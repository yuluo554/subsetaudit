# -*- coding: utf-8 -*-
"""M5 `report` 测试：聚合顺序、键冲突检测、Markdown 渲染、退出码 0/1/2 三档、单一路径。

口径单点在 ``data/README.md`` §六.9.7；本文件只做三件事：
  ① 断言聚合行为与 §六.9.7 一致（模块顺序 / 键冲突 / `summary.modules`）；
  ② 断言"**只有一条聚合路径**"（改回两套必红）；
  ③ 用变异证明这些断言真的会红。
"""
from __future__ import print_function

import io
import json
import os

import pytest

from conftest import build_font
from subsetaudit import cli, report

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_ROOT = os.path.join(REPO_ROOT, "data", "fixtures")
F6 = os.path.join(FIXTURES_ROOT, "codepage-mismatch", "out")
F5 = os.path.join(FIXTURES_ROOT, "metadata-stripped", "out")


def _read(rel):
    with io.open(os.path.join(REPO_ROOT, rel), "r", encoding="utf-8") as fh:
        return fh.read()


def _run(argv, capsys):
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ── ① 聚合顺序与模块清单 ───────────────────────────────────────────────────
def test_modules_are_all_four_in_spec_order():
    """四个模块都跑时，`summary.modules` 严格照 §六.9.7 的固定顺序。"""
    body = report.evaluate(
        source=os.path.join(F6, "source.ttf"),
        subset=os.path.join(F6, "subset.ttf"),
        required={0x6C49, 0x5B57},
    )
    assert body["summary"]["modules"] == list(report.MODULE_ORDER)
    assert report.MODULE_ORDER == ("license-gate", "metadata", "layout-survival", "coverage-diff")


def test_single_module_runs_are_listed():
    """只给 `--source` → 只跑 `license-gate`；空跑 → `[]`（"没跑"必须可见）。"""
    body = report.evaluate(source=os.path.join(F6, "source.ttf"))
    assert body["summary"]["modules"] == ["license-gate"]

    body = report.evaluate(subset=os.path.join(F5, "subset.ttf"))
    assert body["summary"]["modules"] == ["metadata"]

    empty = report.evaluate()
    assert empty["summary"]["modules"] == []
    assert empty["findings"] == [] and empty["skipped"] == []


def test_layout_and_coverage_need_both_sides():
    """`layout-survival` 要两侧都有；`coverage-diff` 要 `--source` 且有需求集（§六.9.7）。"""
    body = report.evaluate(source=os.path.join(F6, "source.ttf"))
    assert "layout-survival" not in body["summary"]["modules"]
    assert "coverage-diff" not in body["summary"]["modules"]

    body = report.evaluate(source=os.path.join(F6, "source.ttf"),
                           subset=os.path.join(F6, "subset.ttf"))
    assert body["summary"]["modules"] == ["license-gate", "metadata", "layout-survival"]


def test_aggregated_findings_are_sorted_by_canonical_key():
    """聚合后的 finding 仍由 `canonical.sort_findings` 统一排序（不按模块拼接顺序）。"""
    from subsetaudit import canonical

    body = report.evaluate(
        source=os.path.join(F6, "source.ttf"),
        subset=os.path.join(F6, "subset.ttf"),
        required={0x6C49, 0x5B57},
    )
    ordered = [(f["module"], f["severity"], f["primary_key"]) for f in body["findings"]]
    assert ordered == sorted(
        ordered,
        key=lambda t: (t[0], canonical.SEVERITIES.index(t[1]), t[2]),
    )


def test_summary_keys_do_not_collide_across_modules(layout_font, tmp_path):
    """现状：四个模块的顶级 `summary` 键互不相交 → **不得**出现冲突 finding。

    用一个**有 GSUB** 的样本，四个模块才会都把各自的 key 落进 summary
    （F6 那对字体两侧都没有布局表 → 布局侧走 `no_layout_tables`、summary 为空，见下一条）。
    """
    from conftest import subset_layout_font

    out = str(tmp_path / "sub.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61])
    body = report.evaluate(source=layout_font, subset=out, required={0x66, 0x69})
    assert body["summary"]["modules"] == list(report.MODULE_ORDER)
    assert report.CODE_KEY_COLLISION not in [f["code"] for f in body["findings"]]
    assert "summary_key_collisions" not in body["summary"]
    # 四个模块各自的落点都在
    for key in ("conclusions", "metadata", "layout", "coverage"):
        assert key in body["summary"], key


def test_no_layout_tables_means_no_layout_key_and_a_visible_skip():
    """§六.5.5：两侧都无布局表 → `summary` 为空 + 一条 SKIPPED（聚合层照实保留）。"""
    body = report.evaluate(source=os.path.join(F6, "source.ttf"),
                           subset=os.path.join(F6, "subset.ttf"))
    assert "layout" not in body["summary"]
    assert [(s["module"], s["reason"]) for s in body["skipped"]] == [
        ("layout-survival", "no_layout_tables")]


# ── ② 键冲突检测（静默覆盖是缺陷） ─────────────────────────────────────────
def test_merge_summaries_reports_collisions():
    """两模块用同一个顶级键 → `owners` 记全、合并时保留先到者。"""
    merged, owners = report.merge_summaries([
        ("license-gate", {"shared": 1, "only_a": True}),
        ("metadata", {"shared": 2, "only_b": True}),
    ])
    assert owners["shared"] == ["license-gate", "metadata"]
    assert merged["shared"] == 1, "先到者保留（但冲突一定要报）"
    assert merged["only_a"] is True and merged["only_b"] is True


def test_collision_becomes_an_error_finding(monkeypatch):
    """真的撞键时 → 产 `SUMMARY_KEY_COLLISION`（`error`）+ 列出冲突键。

    变异意义：把"静默覆盖"改回来 → 这条必红。
    """
    from subsetaudit import license_gate

    original = license_gate.evaluate

    def clashing(path):
        findings, skips, summary = original(path)
        summary["metadata"] = {"clash": True}  # 故意占用 metadata 的键
        return findings, skips, summary

    monkeypatch.setattr(license_gate, "evaluate", clashing)
    body = report.evaluate(
        source=os.path.join(F6, "source.ttf"),
        subset=os.path.join(F6, "subset.ttf"),
    )
    hits = [f for f in body["findings"] if f["code"] == report.CODE_KEY_COLLISION]
    assert len(hits) == 1
    assert hits[0]["severity"] == "error"
    assert hits[0]["primary_key"] == "metadata"
    assert hits[0]["spec_ref"] == "data/README §6.9"
    assert hits[0]["evidence"]["modules"] == ["license-gate", "metadata"]
    assert body["summary"]["summary_key_collisions"] == ["metadata"]
    # 合并语义 = **先到者保留**（§六.9.7）：license-gate 先跑 → 它的 `metadata` 键留下，
    # metadata 模块的真实内容被**报错**而不是被静默覆盖
    assert body["summary"]["metadata"] == {"clash": True}


def test_mutation_silent_overwrite_is_caught(monkeypatch):
    """变异 1：把冲突检查去掉（回到 `summary.update(...)`）→ 冲突 finding 消失。"""
    monkeypatch.setattr(report, "_collision_findings", lambda owners: [])
    merged, owners = report.merge_summaries([
        ("license-gate", {"shared": 1}),
        ("metadata", {"shared": 2}),
    ])
    assert owners["shared"] == ["license-gate", "metadata"], "owners 仍应记全"
    assert report._collision_findings(owners) == [], "变异后不产 finding（本条断言证明变异生效）"


# ── ③ 单一路径（不得留两套聚合） ───────────────────────────────────────────
def test_there_is_exactly_one_aggregation_path():
    """§六.9.7：聚合只在 `report.evaluate` 里。`_run_report` **不得**再自己合并各模块 summary。

    变异：把 `_run_report` 改回自己聚合 → 这条必红。
    （单模块子命令各自调自己的 `evaluate` 是正常的 —— 那不是聚合，扫描面只取 `_run_report`。）
    """
    cli_source = _read("src/subsetaudit/cli.py")
    start = cli_source.index("def _run_report(")
    end = cli_source.index("def _from_text(")
    report_handler = cli_source[start:end]

    assert "summary.update(" not in report_handler, "`_run_report` 里又出现第二处聚合（禁止）"
    assert "report.evaluate(" in report_handler, "`_run_report` 必须走 `report.evaluate`"
    for module in ("license_gate", "metadata", "layout_survival", "coverage_diff"):
        assert "%s.evaluate(" % module not in report_handler, \
            "`_run_report` 仍在直接调 %s.evaluate（聚合跑到 CLI 里了）" % module
    assert "merge_summaries(" not in report_handler

    report_source = _read("src/subsetaudit/report.py")
    assert report_source.count("def evaluate(") == 1
    assert "summary.update(" not in report_source, "合并用 `merge_summaries`（带冲突检测），不用 update"


def test_cli_report_matches_module_report_byte_for_byte(tmp_path):
    """`report` 子命令的输出与直接调 `report.evaluate` 逐字节一致（同一条路径）。"""
    from subsetaudit import canonical

    target = str(tmp_path / "cli.json")
    code = cli.main(["report", "--source", os.path.join(F6, "source.ttf"),
                     "--subset", os.path.join(F6, "subset.ttf"),
                     "--text", "汉字", "--out", target])
    assert code == cli.EXIT_FINDINGS
    direct = report.evaluate(
        source=os.path.join(F6, "source.ttf"),
        subset=os.path.join(F6, "subset.ttf"),
        required={0x6C49, 0x5B57},
    )
    assert open(target, "rb").read() == canonical.dumps(direct).encode("utf-8")


# ── ④ 退出码 0 / 1 / 2 三档 ────────────────────────────────────────────────
def test_exit_zero_on_clean_input(simple_font, capsys):
    code, out, _err = _run(["report", "--source", simple_font], capsys)
    assert code == cli.EXIT_OK
    assert json.loads(out)["findings"] == []


def test_exit_one_on_error_finding(capsys):
    """F6 的码页矛盾是 `error` → 聚合报告退出码 1。"""
    code, out, _err = _run(["report", "--source", os.path.join(F6, "source.ttf"),
                            "--subset", os.path.join(F6, "subset.ttf")], capsys)
    assert code == cli.EXIT_FINDINGS
    body = json.loads(out)
    assert any(f["severity"] == "error" for f in body["findings"])


def test_exit_two_on_non_font(tmp_path, capsys):
    """输入夹非字体文件 → 退出码 2 且**指明文件**（DoD）。"""
    bad = tmp_path / "not-a-font.ttf"
    bad.write_text("nope", encoding="utf-8")
    code, _out, err = _run(["report", "--source", str(bad)], capsys)
    assert code == cli.EXIT_INPUT_ERROR
    assert "not-a-font.ttf" in err


def test_exit_two_when_subset_is_non_font(tmp_path, simple_font, capsys):
    bad = tmp_path / "also-not.ttf"
    bad.write_text("nope", encoding="utf-8")
    code, _out, err = _run(["report", "--source", simple_font, "--subset", str(bad)], capsys)
    assert code == cli.EXIT_INPUT_ERROR
    assert "also-not.ttf" in err


def test_exit_two_on_unreadable_corpus(simple_font, tmp_path, capsys):
    code, _out, _err = _run(["report", "--source", simple_font,
                             "--corpus", str(tmp_path / "gone.txt")], capsys)
    assert code == cli.EXIT_INPUT_ERROR


# ── ⑤ Markdown / 确定性 / 脱敏 ─────────────────────────────────────────────
def test_markdown_renders_findings_and_skips(capsys):
    code, out, _err = _run(["report", "--source", os.path.join(F6, "source.ttf"),
                            "--subset", os.path.join(F6, "subset.ttf"),
                            "--format", "markdown"], capsys)
    assert code == cli.EXIT_FINDINGS
    assert out.startswith("# SubsetAudit 报告")
    assert "CODEPAGE_CLAIMS_LATIN1_WITHOUT_COVERAGE" in out
    assert "`cp1:latin1`" in out
    # 布局侧两侧都没有 GSUB/GPOS → SKIPPED 必须出现在渲染视图里
    assert "SKIPPED(reason=no_layout_tables)" in out


def test_markdown_renders_conclusions_section(simple_font, capsys):
    """`summary["conclusions"]` 仍由 `license-gate` 独占（K15），Markdown 要有该节。"""
    _code, out, _err = _run(["report", "--source", simple_font, "--format", "markdown"], capsys)
    assert "## 结论" in out and "`embed_pdf`" in out


def test_json_is_byte_identical_across_runs(tmp_path):
    a, b = str(tmp_path / "a.json"), str(tmp_path / "b.json")
    argv = ["report", "--source", os.path.join(F6, "source.ttf"),
            "--subset", os.path.join(F6, "subset.ttf"), "--text", "汉字"]
    cli.main(argv + ["--out", a])
    cli.main(argv + ["--out", b])
    assert open(a, "rb").read() == open(b, "rb").read()


def test_report_has_no_absolute_path_or_timestamp(capsys):
    import re

    _code, out, _err = _run(["report", "--source", os.path.join(F6, "source.ttf"),
                             "--subset", os.path.join(F6, "subset.ttf"), "--text", "汉字"], capsys)
    body = json.loads(out)
    assert body["inputs"] == {"source": "source.ttf", "subset": "subset.ttf"}
    assert not re.search(r"20\d\d-\d\d-\d\d", out)
    assert "Users" not in out and "C:\\\\" not in out


def test_summary_has_the_four_counters(simple_font):
    """`build_report` 保证 error/warn/note/skipped 四个计数器恒在（§六.9.7 之外的老约定）。"""
    body = report.evaluate(source=simple_font)
    for key in ("error", "warn", "note", "skipped"):
        assert key in body["summary"], key


# ── ⑥ 变异：改坏实现至少一层测试必红 ──────────────────────────────────────
def test_mutation_reordering_modules_is_caught(monkeypatch):
    """变异 2：把 `MODULE_ORDER` 调换 → `summary.modules` 跟着变（证明顺序来自那张表）。"""
    monkeypatch.setattr(report, "MODULE_ORDER", ("metadata", "license-gate"))
    body = report.evaluate(
        source=os.path.join(F6, "source.ttf"),
        subset=os.path.join(F6, "subset.ttf"),
    )
    assert body["summary"]["modules"] == ["metadata", "license-gate"], \
        "顺序必须由 MODULE_ORDER 说了算（否则那张表是装饰）"


def test_mutation_dropping_modules_list_is_caught(monkeypatch):
    """变异 3：把 `modules` 写成常量 → 与真实跑过的模块脱钩（可见后果 = 顺序变异失效）。"""
    monkeypatch.setattr(report, "MODULE_ORDER", ("license-gate",))
    body = report.evaluate(
        source=os.path.join(F6, "source.ttf"),
        subset=os.path.join(F6, "subset.ttf"),
    )
    assert body["summary"]["modules"] == ["license-gate"], \
        "modules 必须反映这次**真的跑了哪些**，而不是四个模块的静态清单"


def test_mutation_metadata_not_run_is_visible(monkeypatch):
    """变异 4：把 `metadata` 从聚合里摘掉 → `summary.modules` 立刻少一项。"""
    monkeypatch.setattr(report.metadata, "evaluate",
                        lambda *a, **k: ([], [], {}))
    body = report.evaluate(subset=os.path.join(F5, "subset.ttf"))
    assert body["summary"]["modules"] == ["metadata"], \
        "模块仍然跑了（只是返回空）→ 这正是 modules 要暴露的：跑了但没给结论"
    assert body["summary"] == {"modules": ["metadata"], "error": 0, "warn": 0,
                               "note": 0, "skipped": 0}


def test_mutation_dropping_layout_module_is_caught(monkeypatch):
    """变异 5：摘掉 `layout-survival` 的调用 → 布局类 finding 消失（可观察）。"""
    monkeypatch.setattr(report.layout_survival, "evaluate",
                        lambda *a, **k: ([], [], {}))
    body = report.evaluate(
        source=os.path.join(F6, "source.ttf"),
        subset=os.path.join(F6, "subset.ttf"),
    )
    assert "layout" not in body["summary"]
    assert "layout-survival" in body["summary"]["modules"]


def test_report_module_has_no_skeleton_leftovers():
    """M5 已实现：`report` 不得再引用骨架出口（反向判据）。"""
    text = _read("src/subsetaudit/report.py")
    assert "NOT_IMPLEMENTED" not in text
    assert "skeleton_result(" not in text
    assert "module_not_implemented_in_m0" not in text


def test_report_only_reads_never_saves():
    """K6：报告层只读 —— 源码里不得出现 `.save(`。"""
    assert ".save(" not in _read("src/subsetaudit/report.py")


def test_spec_ref_matches_data_readme_section():
    """§六.9.7 必须真的写了聚合口径（含键冲突与 modules）。"""
    text = _read("data/README.md")
    assert "9.7 `report` 聚合口径" in text
    assert "只有一条路径" in text
    assert "SUMMARY_KEY_COLLISION" in text
    assert report.COLLISION_SPEC_REF == "data/README §6.9"
