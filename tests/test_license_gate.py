# -*- coding: utf-8 -*-
"""M2 `license-gate` 测试：F1/F2/F3 golden 逐项、bit0 单列、bit9、无 OS/2、口径单点、改坏必红。

口径单点在 ``data/README.md`` §六.1；本文件**不复制判定式**，只做两件事：
  ① 断言实现与 §六.1 的表一致（含 spec_ref 字面量逐字对账）；
  ② 用变异证明这些断言真的会红。
"""
from __future__ import print_function

import io
import json
import os
import re

import pytest

from conftest import build_font
from subsetaudit import canonical, license_gate

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_ROOT = os.path.join(REPO_ROOT, "data", "fixtures")
DATA_README = os.path.join(REPO_ROOT, "data", "README.md")

NAMES = {
    "F1": "fstype-nosubset",
    "F2": "fstype-multibit-v0",
    "F3": "fstype-multibit-v3",
}


def _fixture_font(fid):
    path = os.path.join(FIXTURES_ROOT, NAMES[fid], "out")
    with io.open(os.path.join(FIXTURES_ROOT, NAMES[fid], "expect.json"),
                 "r", encoding="utf-8") as fh:
        body = json.load(fh)
    return os.path.join(path, body["font"]), body


def _evaluate(path):
    findings, skips, summary = license_gate.evaluate(path)
    return findings, skips, summary


def _values(summary):
    return dict((k, v["value"]) for k, v in summary["conclusions"].items())


def _codes(findings):
    return [(f["code"], f["severity"]) for f in findings]


# ── F1/F2/F3 golden 逐项 ───────────────────────────────────────────────────
@pytest.mark.parametrize("fid", ["F1", "F2", "F3"])
def test_golden_summary_matches_expect_json(fid):
    """golden 的每个键都要在 summary 里逐项对上（不是"抽查几个"）。"""
    font, body = _fixture_font(fid)
    _findings, _skips, summary = _evaluate(font)
    exp = body["expect"]

    assert summary["fsType"] == exp["fsType"]
    assert summary["os2_version"] == exp["os2_version"]
    assert summary["permission_bits"] == exp["permission_bits"]
    assert summary["permission_name"] == exp["permission_name"]
    assert summary["permission_resolution"] == exp["permission_resolution"]
    assert _values(summary) == dict(
        (key, exp[key]) for key in license_gate.CONCLUSION_KEYS
    ), "五元结论必须逐条与 golden 一致"


@pytest.mark.parametrize("fid", ["F1", "F2", "F3"])
def test_golden_findings_match_expect_json(fid):
    """finding 的 `(code, severity, spec_ref)` 三元组与 golden 逐条一致（含顺序）。"""
    font, body = _fixture_font(fid)
    findings, _skips, _summary = _evaluate(font)
    expected = [(f["code"], f["severity"], f["spec_ref"]) for f in body["expect"]["expected_findings"]]
    got = [(f["code"], f["severity"], f["spec_ref"]) for f in findings]
    assert got == expected


def test_f2_v0_multibit_is_not_reported_as_violation():
    """**反例守护**：`0x000E` + v0 不得报互斥（本机 560 字体池里 40 个 0x000E 全在 v0/v1）。

    这条是本模块最容易被"写得更严"而误伤的地方：只要实现不看 `OS/2.version`，它必红。
    """
    font, _body = _fixture_font("F2")
    findings, skips, summary = _evaluate(font)
    assert findings == []
    assert skips == []
    assert summary["permission_resolution"] == "least_restrictive"
    assert summary["permission_name"] == "Editable"
    assert _values(summary)["may_subset"] is True


def test_f3_v3_multibit_is_a_violation_and_conclusions_are_unchanged():
    """F3 与 F2 位值相同、只差 `OS/2.version`：违规独立成条，五元结论不得跟着变。"""
    font3, _ = _fixture_font("F3")
    font2, _ = _fixture_font("F2")
    _f2, _s2, sum2 = _evaluate(font2)
    findings3, _s3, sum3 = _evaluate(font3)

    assert _codes(findings3) == [("FSTYPE_MUTUAL_EXCLUSION", "error")]
    assert _values(sum3) == _values(sum2), "违规不得改写解析值（最宽松仍是 Editable）"
    assert sum3["permission_name"] == sum2["permission_name"] == "Editable"


# ── bit0 保留位单列（0x0001 / 0x0003 两类样本） ────────────────────────────
def test_bit0_only_sample_is_singled_out(tmp_path):
    """`0x0001`：bit0 置位 → `FSTYPE_BIT0_RESERVED`；权限位全 0 → 解析为 Installable。"""
    path = str(tmp_path / "bit0.ttf")
    build_font(path, cmap={0x61: "a"}, fs_type=0x0001, version=0)
    findings, skips, summary = _evaluate(path)

    assert skips == []
    assert _codes(findings) == [("FSTYPE_BIT0_RESERVED", "error")]
    assert findings[0]["primary_key"] == "bit0"
    assert summary["permission_bits"] == "0x0001"
    assert summary["permission_name"] == "Installable"
    assert _values(summary)["may_modify"] is True


def test_bit0_plus_bit1_sample_reports_both_independently(tmp_path):
    """`0x0003`：bit0 与 bit1 并存 → 保留位一条 + Restricted 一条，各自独立。

    本机字体池里正好有 1 个 `0x0003`（OS/2 v0）→ 这是真实形态，不是编出来的。
    """
    path = str(tmp_path / "bit0bit1.ttf")
    build_font(path, cmap={0x61: "a"}, fs_type=0x0003, version=0)
    findings, _skips, summary = _evaluate(path)

    assert _codes(findings) == [("FSTYPE_BIT0_RESERVED", "error"),
                                ("FSTYPE_RESTRICTED_LICENSE", "warn")]
    assert summary["permission_bits"] == "0x0003"
    assert summary["permission_name"] == "Restricted"
    assert _values(summary)["embed_pdf"] is False
    assert _values(summary)["may_modify"] is False


def test_bit0_is_reported_on_every_os2_version(tmp_path):
    """bit0 在任何版本都是 permanently reserved（v0 也不例外）→ 不得因版本降级。"""
    for version in (0, 1, 2, 4):
        path = str(tmp_path / ("bit0-v%d.ttf" % version))
        build_font(path, cmap={0x61: "a"}, fs_type=0x0001, version=version)
        findings, _skips, _summary = _evaluate(path)
        assert _codes(findings) == [("FSTYPE_BIT0_RESERVED", "error")], version


# ── bit8 / bit9 / 保留位 ───────────────────────────────────────────────────
def test_bit8_blocks_subset_and_web_but_not_pdf_embedding():
    """bit8 只禁"嵌入前子集"，不禁嵌入本身 —— `embed_pdf` 必须仍为 true。"""
    font, _ = _fixture_font("F1")
    _f, _s, summary = _evaluate(font)
    values = _values(summary)
    assert values["may_subset"] is False
    assert values["embed_web"] is False
    assert values["embed_pdf"] is True
    assert values["may_modify"] is True


def test_bit9_bitmap_only_blocks_all_outline_embedding(tmp_path):
    """`0x0208`（Editable + bit9）：轮廓不可嵌入 → 三条嵌入结论全 false，`may_subset` 仍 true。"""
    path = str(tmp_path / "bit9.ttf")
    build_font(path, cmap={0x61: "a"}, fs_type=0x0208, version=4)
    findings, _skips, summary = _evaluate(path)

    assert _codes(findings) == [("FSTYPE_BITMAP_ONLY", "warn")]
    assert findings[0]["primary_key"] == "bit9"
    values = _values(summary)
    assert values["embed_pdf"] is False
    assert values["embed_app"] is False
    assert values["embed_web"] is False
    assert values["may_subset"] is True


def test_reserved_bits_severity_follows_os2_version(tmp_path):
    """§六.1.6：bits4–15 在 v0/v1 规范要求"应用忽略" → warn；v2+ → error。"""
    for version, severity in ((0, "warn"), (1, "warn"), (2, "error"), (4, "error")):
        path = str(tmp_path / ("resv-v%d.ttf" % version))
        build_font(path, cmap={0x61: "a"}, fs_type=0x0010, version=version)  # bit4
        findings, _skips, _summary = _evaluate(path)
        assert _codes(findings) == [("FSTYPE_RESERVED_BITS", severity)], version


def test_restricted_license_blocks_every_embedding(tmp_path):
    """`0x0002`：Restricted → 三条嵌入 false、`may_modify` false，`may_subset` 仍 true。"""
    path = str(tmp_path / "restricted.ttf")
    build_font(path, cmap={0x61: "a"}, fs_type=0x0002, version=1)
    findings, _skips, summary = _evaluate(path)

    assert _codes(findings) == [("FSTYPE_RESTRICTED_LICENSE", "warn")]
    values = _values(summary)
    assert values == {"embed_pdf": False, "embed_app": False, "embed_web": False,
                      "may_subset": True, "may_modify": False}


# ── 无 OS/2 表 → SKIPPED，不猜 ─────────────────────────────────────────────
def test_missing_os2_table_skips_without_guessing(tmp_path):
    path = str(tmp_path / "noos2.ttf")
    build_font(path, cmap={0x61: "a"}, include_os2=False)
    findings, skips, summary = _evaluate(path)

    assert findings == []
    assert [s["reason"] for s in skips] == ["no_os2_table"]
    assert summary == {}, "无 OS/2 表时不得输出任何五元结论（那是猜测）"


def test_unreadable_font_is_input_error_not_finding(tmp_path):
    with pytest.raises(canonical.InputError):
        _evaluate(str(tmp_path / "nope.ttf"))
    bad = tmp_path / "bad.ttf"
    bad.write_text("not a font", encoding="utf-8")
    with pytest.raises(canonical.InputError):
        _evaluate(str(bad))


# ── 五元结论每条带 spec_ref + 免责声明 ─────────────────────────────────────
def test_every_conclusion_carries_a_spec_ref():
    font, _ = _fixture_font("F2")
    _f, _s, summary = _evaluate(font)
    assert list(summary["conclusions"]) == list(license_gate.CONCLUSION_KEYS)
    for key, item in summary["conclusions"].items():
        assert item["spec_ref"].startswith("MS-OS2 "), key


@pytest.mark.parametrize("fid", ["F1", "F2", "F3"])
def test_every_finding_carries_a_spec_ref(fid):
    font, _ = _fixture_font(fid)
    findings, _s, _summary = _evaluate(font)
    for f in findings:
        assert f["spec_ref"], f["code"]
        assert f["evidence"], "每条 finding 必须有可复算证据: %s" % f["code"]


def test_report_carries_the_technical_verdict_disclaimer():
    font, _ = _fixture_font("F1")
    findings, skips, summary = _evaluate(font)
    body = canonical.build_report(findings, skips, {"font": "f.ttf"}, summary,
                                  tool_version="x")
    assert "法律意见" in body["disclaimer"]
    assert "法律意见" in canonical.render_markdown(body)
    assert "`embed_pdf`" in canonical.render_markdown(body), "Markdown 必须渲染五元结论"


def test_evaluate_is_deterministic():
    font, _ = _fixture_font("F3")
    a = canonical.dumps(canonical.build_report(*license_gate.evaluate(font), {"font": "f.ttf"},
                                               tool_version="x"))
    b = canonical.dumps(canonical.build_report(*license_gate.evaluate(font), {"font": "f.ttf"},
                                               tool_version="x"))
    assert a == b


# ── 口径单点：实现里的 spec_ref / primary_key 必须逐字等于 §六.1 的表 ───────
def _table_spec_refs(section_marker, keys):
    """从 `data/README.md` 的表里抽出 ``{key: spec_ref}``（spec_ref = 该行最后一个 MS-OS2 反引号片段）。"""
    text = io.open(DATA_README, "r", encoding="utf-8").read()
    start = text.index(section_marker)
    end = text.find("\n   **1.4", start) if section_marker.startswith("1.3") else text.find("\n   **1.5", start)
    block = text[start:end if end > 0 else len(text)]
    found = {}
    for line in block.split("\n"):
        # 表在有序列表里，行首有 3 个空格缩进 → 先 strip 再认行首
        if not line.strip().startswith("| `"):
            continue
        key = line.strip().split("`")[1]
        if key not in keys:
            continue
        refs = [m for m in re.findall(r"`([^`]+)`", line) if m.startswith("MS-OS2 ")]
        if refs:
            found[key] = refs[-1]
    return found


def test_spec_refs_match_the_single_source_table():
    """**口径单点**：§六.1.3 的 spec_ref 字面量与代码常量逐字一致（改一边必红）。"""
    got = _table_spec_refs("**1.3 五元结论", set(license_gate.SPEC_REFS))
    assert got, "§六.1.3 表没解析到 spec_ref（表被改了？）"
    assert got == license_gate.SPEC_REFS


def test_finding_spec_refs_match_the_single_source_table():
    """**口径单点**：§六.1.4 的违规码 spec_ref 字面量与代码常量逐字一致。"""
    got = _table_spec_refs("**1.4 违规码", set(license_gate.CODE_SPEC_REFS))
    assert got, "§六.1.4 表没解析到 spec_ref（表被改了？）"
    assert got == license_gate.CODE_SPEC_REFS


def test_conclusion_keys_are_exactly_the_five_in_the_plan():
    """五元结论的键集合固定（`plan/01` §三 M1 与 `plan/03` §2 写的是同一组）。"""
    assert set(license_gate.CONCLUSION_KEYS) == {
        "embed_pdf", "embed_app", "embed_web", "may_subset", "may_modify"}
    assert set(license_gate.SPEC_REFS) == set(license_gate.CONCLUSION_KEYS)


def test_permission_names_cover_exactly_the_four_legal_values():
    """§3.1：合法值只有 0/2/4/8 —— 多一个或少一个都说明口径漂了。"""
    assert sorted(license_gate.PERMISSION_NAMES) == [0, 2, 4, 8]


# ── 变异验证：改坏实现 → 至少一层断言必红（不碰仓库文件，进程内改） ─────────
def _assert_red(mutate, undo, check):
    """应用变异 → 断言 ``check()`` 失败 → 还原。返回被抓住的异常类型。"""
    mutate()
    try:
        with pytest.raises(AssertionError):
            check()
    finally:
        undo()


def test_mutation_ignoring_os2_version_is_caught(tmp_path):
    """变异①：不看 `OS/2.version` 就报互斥 → F2（v0）的守护断言必红。"""
    original = license_gate._violations

    def broken(fs_type, version, perm, bits):
        # 无视版本：只要 bits1–3 多位并存就报互斥
        rows = original(fs_type, version, perm, bits)
        if bin(int(bits) & 0x000E).count("1") >= 2 and not any(
                r[0] == "FSTYPE_MUTUAL_EXCLUSION" for r in rows):
            rows.append(("FSTYPE_MUTUAL_EXCLUSION", "error", "broken", {}))
        return rows

    def check():
        font, _ = _fixture_font("F2")
        findings, _s, _sum = _evaluate(font)
        assert findings == []

    _assert_red(lambda: setattr(license_gate, "_violations", broken),
                lambda: setattr(license_gate, "_violations", original),
                check)


def test_mutation_dropping_least_restrictive_is_caught():
    """变异②：v0 多位并存不再取最宽松（直接返回原始位串）→ F2 的权限名断言必红。"""
    original = license_gate.resolve_permission

    def broken(bits, version):
        return int(bits) & 0x000F, "direct"

    def check():
        font, _ = _fixture_font("F2")
        _f, _s, summary = _evaluate(font)
        assert summary["permission_name"] == "Editable"
        assert summary["permission_resolution"] == "least_restrictive"

    _assert_red(lambda: setattr(license_gate, "resolve_permission", broken),
                lambda: setattr(license_gate, "resolve_permission", original),
                check)


def test_mutation_ignoring_bit8_is_caught():
    """变异③：`may_subset` 不看 bit8 → F1 的 `may_subset=false` 必红。"""
    original = license_gate.conclusions_for

    def broken(fs_type, perm):
        values = original(fs_type, perm)
        values["may_subset"] = True
        return values

    def check():
        font, _ = _fixture_font("F1")
        _f, _s, summary = _evaluate(font)
        assert _values(summary)["may_subset"] is False

    _assert_red(lambda: setattr(license_gate, "conclusions_for", broken),
                lambda: setattr(license_gate, "conclusions_for", original),
                check)


def test_mutation_ignoring_bit9_is_caught(tmp_path):
    """变异④：`embed_pdf` 不看 bit9 → bit9 样本的"轮廓不可嵌入"必红。"""
    original = license_gate.conclusions_for

    def broken(fs_type, perm):
        values = original(fs_type, perm)
        values["embed_pdf"] = perm != 2
        return values

    def check():
        path = str(tmp_path / "bit9m.ttf")
        build_font(path, cmap={0x61: "a"}, fs_type=0x0208, version=4)
        _f, _s, summary = _evaluate(path)
        assert _values(summary)["embed_pdf"] is False

    _assert_red(lambda: setattr(license_gate, "conclusions_for", broken),
                lambda: setattr(license_gate, "conclusions_for", original),
                check)


def test_mutation_dropping_bit0_reserved_is_caught(tmp_path):
    """变异⑤：删掉 bit0 那条码 → `0x0001` 样本必须一条 finding 都没有 → 断言红。"""
    original = license_gate._violations

    def broken(fs_type, version, perm, bits):
        return [r for r in original(fs_type, version, perm, bits)
                if r[0] != "FSTYPE_BIT0_RESERVED"]

    def check():
        path = str(tmp_path / "bit0m.ttf")
        build_font(path, cmap={0x61: "a"}, fs_type=0x0001, version=0)
        findings, _s, _sum = _evaluate(path)
        assert _codes(findings) == [("FSTYPE_BIT0_RESERVED", "error")]

    _assert_red(lambda: setattr(license_gate, "_violations", broken),
                lambda: setattr(license_gate, "_violations", original),
                check)
