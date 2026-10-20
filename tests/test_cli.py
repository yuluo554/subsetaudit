# -*- coding: utf-8 -*-
"""CLI 测试：三档退出码、五子命令可跑、SKIPPED 显式、参数面反射对账、零网络、版本一致。"""
from __future__ import print_function

import io
import json
import os
import subprocess

import pytest

from subsetaudit import cli

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Result(object):
    """一次 CLI 运行的完整观察结果。

    **capsys 只能消费一次**：``readouterr()`` 二次调用返回空串 —— 所以三个流必须在同一处
    一次性接住（本项目 M0 实测踩到：单独再取 stderr 得到空串，看起来像"错误信息没打印"，
    实际是被第一次调用消费掉了）。
    """

    def __init__(self, code, out, err):
        self.code = code
        self.out = out
        self.err = err

    def json(self):
        return json.loads(self.out)


def run(argv, capsys=None):
    """跑 CLI，一次性返回 (退出码, stdout, stderr)。"""
    code = cli.main(argv)
    out = err = ""
    if capsys is not None:
        captured = capsys.readouterr()
        out, err = captured.out, captured.err
    return Result(code, out, err)


# ── 退出码 2（输入非法） ─────────────────────────────────────────────────────
def test_no_subcommand_is_usage_error(capsys):
    assert run([], capsys).code == cli.EXIT_INPUT_ERROR


def test_license_gate_missing_file_is_exit_2(tmp_path, capsys):
    assert run(["license-gate", str(tmp_path / "nope.ttf")], capsys).code == cli.EXIT_INPUT_ERROR


def test_license_gate_non_font_is_exit_2(tmp_path, capsys):
    bad = tmp_path / "x.ttf"
    bad.write_text("nope", encoding="utf-8")
    assert run(["license-gate", str(bad)], capsys).code == cli.EXIT_INPUT_ERROR


def test_every_subcommand_rejects_a_non_font(tmp_path, capsys):
    """退出码 2 是 M0 就承诺的可演示物 —— 五个子命令都要有输入校验。"""
    bad = tmp_path / "x.ttf"
    bad.write_text("nope", encoding="utf-8")
    cases = [
        ["license-gate", str(bad)],
        ["coverage-diff", str(bad), "--text", "ab"],
        ["layout-survival", str(bad), str(bad)],
        ["metadata", str(bad)],
        ["report", "--source", str(bad)],
    ]
    for argv in cases:
        assert run(argv, capsys).code == cli.EXIT_INPUT_ERROR, argv


def test_open_failure_writes_exactly_one_line_to_stderr(tmp_path, capsys):
    r = run(["license-gate", str(tmp_path / "nope.ttf")], capsys)
    assert r.code == cli.EXIT_INPUT_ERROR
    assert r.err.count("\n") == 1, repr(r.err)
    assert "输入非法" in r.err


def test_coverage_diff_requires_text_or_corpus(simple_font):
    with pytest.raises(SystemExit) as exc:
        cli.main(["coverage-diff", simple_font])
    assert exc.value.code == cli.EXIT_INPUT_ERROR


def test_coverage_diff_rejects_both_text_and_corpus(simple_font, corpus_file):
    with pytest.raises(SystemExit) as exc:
        cli.main(["coverage-diff", simple_font, "--text", "ab", "--corpus", corpus_file])
    assert exc.value.code == cli.EXIT_INPUT_ERROR


def test_coverage_diff_unreadable_corpus_is_exit_2(simple_font, tmp_path, capsys):
    argv = ["coverage-diff", simple_font, "--corpus", str(tmp_path / "gone.txt")]
    assert run(argv, capsys).code == cli.EXIT_INPUT_ERROR


# ── 退出码 0 + SKIPPED 显式 ─────────────────────────────────────────────────
def test_license_gate_real_verdict_exits_zero(simple_font, capsys):
    """M2 起 `license-gate` 出真实结论：合成字体 `fsType=0x0000` → Installable 全放行。

    这里**不再**断言 `SKIPPED`：该字体有 OS/2 表，跳过是错的（M0 的断言已随 M2 退役）。
    """
    r = run(["license-gate", simple_font], capsys)
    assert r.code == cli.EXIT_OK, r.out
    body = r.json()
    assert body["findings"] == []
    assert body["skipped"] == []
    assert body["inputs"]["font"] == os.path.basename(simple_font)
    assert body["summary"]["permission_name"] == "Installable"
    assert body["summary"]["conclusions"]["embed_app"]["value"] is True


def test_license_gate_without_os2_table_skips_but_still_exit_zero(tmp_path, capsys):
    """无 OS/2 表 → `SKIPPED(reason=no_os2_table)`，退出码 0（§六.1 不适用，不猜）。"""
    from conftest import build_font

    path = str(tmp_path / "noos2.ttf")
    build_font(path, cmap={0x61: "a"}, include_os2=False)
    r = run(["license-gate", path], capsys)
    assert r.code == cli.EXIT_OK, r.out
    body = r.json()
    assert body["findings"] == []
    assert [s["reason"] for s in body["skipped"]] == ["no_os2_table"]
    assert "conclusions" not in body["summary"]


def test_all_five_subcommands_exit_zero(simple_font, corpus_file, capsys):
    cases = [
        ["license-gate", simple_font],
        ["coverage-diff", simple_font, "--text", "ab"],
        ["coverage-diff", simple_font, "--corpus", corpus_file, "--subset", simple_font],
        ["layout-survival", simple_font, simple_font],
        ["metadata", simple_font],
        ["metadata", simple_font, "--source", simple_font],
        ["report", "--source", simple_font, "--subset", simple_font, "--text", "ab"],
    ]
    for argv in cases:
        r = run(argv, capsys)
        assert r.code == cli.EXIT_OK, "%r -> %s %s" % (argv, r.code, r.out)
        body = r.json()
        assert body["inputs"].get("source") is None or not os.path.isabs(body["inputs"]["source"])
    # M5 起**五个子命令全部出真实结论**（`metadata` 与 `report` 不再是骨架）→
    # 这里不再要求"必须输出 SKIPPED"。"不再跳过"由下方 `*_is_no_longer_a_skeleton` 反向断言钉住。
    assert True


def test_report_markdown_format(simple_font, capsys):
    r = run(["report", "--source", simple_font, "--format", "markdown"], capsys)
    assert r.code == cli.EXIT_OK
    assert "# SubsetAudit 报告" in r.out and "法律意见" in r.out


def test_out_file_is_written_lf_and_utf8(simple_font, tmp_path, capsys):
    target = tmp_path / "r.json"
    assert run(["license-gate", simple_font, "--out", str(target)], capsys).code == cli.EXIT_OK
    raw = target.read_bytes()
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    json.loads(raw.decode("utf-8"))


def test_json_output_is_byte_identical_across_runs(simple_font, tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    run(["license-gate", simple_font, "--out", str(a)], capsys)
    run(["license-gate", simple_font, "--out", str(b)], capsys)
    assert a.read_bytes() == b.read_bytes()


# ── 参数面反射对账（README ↔ parser） ───────────────────────────────────────
def test_readme_command_lines_parse_against_parser():
    """README 每条 ``subsetaudit`` 命令行都必须被 parser 接受。

    · ``<...>`` 占位符**替换成具体值**（而不是删掉）—— 删掉会让 `--corpus <f>` 退化成
      "选项后面没有值"，把"文档写的形态"误判成"parser 不接受"（变异靶子瞄错）；
    · ``--version`` / ``--help`` 由 argparse 自己 ``SystemExit(0)``，那是**成功**形态。
    """
    import re

    parser = cli.build_parser()
    readme = io.open(os.path.join(REPO_ROOT, "README.md"), "r", encoding="utf-8").read()
    commands = sorted(set(
        line.strip() for line in readme.split("\n") if line.strip().startswith("subsetaudit ")
    ))
    assert len(commands) >= 3, "README 至少要给出三条可复制命令（场景复现要求）"
    checked, rejected = 0, []
    for command in commands:
        argv = re.sub(r"<[^>]+>", "placeholder", command).split()[1:]
        try:
            parsed = parser.parse_args(argv)
        except SystemExit as exc:
            if exc.code in (0, None):
                checked += 1
                continue
            rejected.append("%s (exit %s)" % (command, exc.code))
            continue
        assert parsed.command, command
        checked += 1
    assert rejected == [], "README 写的命令形态 parser 不认: %s" % rejected
    assert checked >= 3


def test_readme_reflection_check_would_catch_a_rejected_flag():
    """变异自证：把 README 里一个合法选项改坏 → 上面的对账必须红（防假门）。"""
    import re

    parser = cli.build_parser()
    broken = re.sub(r"<[^>]+>", "placeholder",
                    'subsetaudit report --source <source.ttf> --format markdown')
    argv = broken.split()[1:]
    argv[argv.index("markdown")] = "--not-a-real-flag"
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(argv)
    assert exc.value.code == cli.EXIT_INPUT_ERROR


def test_multi_value_argument_in_help_is_accepted_in_all_three_shapes():
    """多值参数（若将来加 `--modules` 之类）必须同时接受单值 / 逗号 / all。

    本判据在 M5 有真实多值参数时自动生效；当前以 `--format` 的两值面作最小锚点，
    保证"文档写的形态"与 parser 一致这条纪律在 M0 就被钉住。
    """
    parser = cli.build_parser()
    for value in ("json", "markdown"):
        assert parser.parse_args(["report", "--format", value]).format == value
    with pytest.raises(SystemExit):
        parser.parse_args(["report", "--format", "yaml"])


# ── 纪律类判据（变异：改坏即红） ────────────────────────────────────────────
def test_no_runtime_network_or_model_imports():
    """零网络零模型纪律：包内不得 import 任何网络/模型库。"""
    banned = ("urllib", "requests", "socket", "http.client", "httpx", "aiohttp", "torch",
              "transformers", "openai")
    pkg = os.path.join(REPO_ROOT, "src", "subsetaudit")
    hits = []
    for name in sorted(os.listdir(pkg)):
        if not name.endswith(".py"):
            continue
        text = io.open(os.path.join(pkg, name), "r", encoding="utf-8").read()
        for lineno, line in enumerate(text.split("\n"), 1):
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for token in banned:
                if token in stripped:
                    hits.append("%s:%d %s" % (name, lineno, stripped))
    assert hits == [], "包内出现网络/模型依赖: %s" % hits


def test_version_consistent_between_package_and_pyproject():
    from subsetaudit import __version__
    pyproject = io.open(os.path.join(REPO_ROOT, "pyproject.toml"), "r", encoding="utf-8").read()
    line = [l for l in pyproject.split("\n") if l.startswith("version = ")][0]
    assert __version__ == line.split("=", 1)[1].strip().strip('"'), line


def test_version_consistent_with_readme():
    """第三处：README 顶部状态行必须写出当前版本（变异：升版本只改一处 → 必红）。"""
    from subsetaudit import __version__
    readme = io.open(os.path.join(REPO_ROOT, "README.md"), "r", encoding="utf-8").read()
    assert ("v%s" % __version__) in readme, "README 状态行必须写出 v%s" % __version__


def test_console_script_entry_point_matches_cli_main():
    pyproject = io.open(os.path.join(REPO_ROOT, "pyproject.toml"), "r", encoding="utf-8").read()
    assert 'subsetaudit = "subsetaudit.cli:main"' in pyproject


def test_skeleton_modules_do_not_fabricate_findings():
    """未实现的模块只准返回 SKIPPED，不得返回任何 finding。

    **M2 起 `license_gate`、M3 起 `coverage_diff`、M4 起 `layout_survival`、M5 起 `metadata`
    都已实现判定** → 断言面已清空。这条判据保留为**空表形态**：将来若再加骨架模块，
    把名字填进 `SKELETON_MODULES` 即可（空表本身也断言"包内确实没有残留骨架出口"）。
    """
    SKELETON_MODULES = ()
    for name in SKELETON_MODULES:
        mod = __import__("subsetaudit.%s" % name, fromlist=[name])
        text = io.open(mod.__file__, "r", encoding="utf-8").read() if hasattr(mod, "__file__") else ""
        assert "skeleton_result(" in text, "%s 未走骨架出口" % name
        assert "finding(" not in text, "%s 在骨架阶段不得构造 finding" % name
    # 反向：包内不得再有任何模块调用骨架出口（否则说明"实现完了却还在跳过"）
    pkg = os.path.join(REPO_ROOT, "src", "subsetaudit")
    callers = []
    for fname in sorted(os.listdir(pkg)):
        if not fname.endswith(".py") or fname == "_skeleton.py":
            continue
        text = io.open(os.path.join(pkg, fname), "r", encoding="utf-8").read()
        if "skeleton_result(" in text:
            callers.append(fname)
    assert callers == [], "这些模块仍在走骨架出口: %s" % callers


def test_metadata_is_no_longer_a_skeleton():
    """M5 已实现：`metadata` 不再走骨架出口（反向判据，防"翻完 ✅ 又退回骨架"）。"""
    from subsetaudit import metadata
    text = io.open(metadata.__file__, "r", encoding="utf-8").read()
    assert "skeleton_result(" not in text
    assert "module_not_implemented_in_m0" not in text


def test_report_is_no_longer_a_skeleton():
    """M5 已实现：`report.evaluate` 不再返回"未实现"的 SKIPPED（它现在是聚合的唯一路径）。"""
    from subsetaudit import report
    text = io.open(report.__file__, "r", encoding="utf-8").read()
    assert "NOT_IMPLEMENTED" not in text
    assert "module_not_implemented_in_m0" not in text
    assert report.evaluate()["summary"]["modules"] == []


def test_license_gate_is_no_longer_a_skeleton():
    """M2 已实现：`license_gate` 不再走骨架出口（反向判据，防"翻完 ✅ 又退回骨架"）。"""
    from subsetaudit import license_gate
    text = io.open(license_gate.__file__, "r", encoding="utf-8").read()
    assert "skeleton_result(" not in text
    assert "module_not_implemented_in_m0" not in text


def test_coverage_diff_is_no_longer_a_skeleton():
    """M3 已实现：`coverage_diff` 不再走骨架出口（反向判据，防"翻完 ✅ 又退回骨架"）。"""
    from subsetaudit import coverage_diff
    text = io.open(coverage_diff.__file__, "r", encoding="utf-8").read()
    assert "skeleton_result(" not in text
    assert "module_not_implemented_in_m0" not in text


def test_layout_survival_is_no_longer_a_skeleton():
    """M4 已实现：`layout_survival` 不再走骨架出口（反向判据，防"翻完 ✅ 又退回骨架"）。"""
    from subsetaudit import layout_survival
    text = io.open(layout_survival.__file__, "r", encoding="utf-8").read()
    assert "skeleton_result(" not in text
    assert "module_not_implemented_in_m0" not in text


def test_no_font_binaries_tracked_by_git():
    """商用字体红线：git 索引里不得有任何字体二进制。

    **必须确认 git 解析到的仓库根就是本项目根**：源码包（`git archive`）解出来的树没有 `.git`，
    如果它恰好被解到"另一个仓库的子目录"里，`git ls-files` 会**静默向上**解析到父仓库
    → 断言扫的是别人的索引（本项目 M0 实测：在仓库内解包时 `git rev-parse --show-toplevel`
    返回的是**外层**仓库）。这种"绿"证明不了任何事。
    """
    toplevel = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=REPO_ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)
    if toplevel.returncode != 0:
        pytest.skip("not a git work tree: %s" % toplevel.stderr.strip())
    resolved = os.path.normcase(os.path.realpath(toplevel.stdout.strip()))
    expected = os.path.normcase(os.path.realpath(REPO_ROOT))
    if resolved != expected:
        pytest.skip("这是一个无 .git 的解包树，且 git 向上解析到了别处（%s）——"
                    "此时 ls-files 扫的不是本树，不能当作通过" % resolved)

    proc = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    assert proc.returncode == 0, proc.stderr
    offenders = [f for f in proc.stdout.split("\n")
                 if f.lower().endswith((".ttf", ".otf", ".ttc", ".otc", ".woff", ".woff2"))]
    assert offenders == [], "字体二进制不得入库: %s" % offenders