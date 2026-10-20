# -*- coding: utf-8 -*-
"""共享层测试：规范层（排序 / 序列化 / 确定性）与只读表访问层。"""
from __future__ import print_function

import io
import json
import os

import pytest

from subsetaudit import canonical, cmapset, sfnt
from conftest import build_font


def test_finding_requires_known_module_and_severity():
    with pytest.raises(ValueError):
        canonical.finding("nope", "C", "error", "k", "m")
    with pytest.raises(ValueError):
        canonical.finding("metadata", "C", "fatal", "k", "m")


def test_sort_key_is_module_then_severity_then_primary_key():
    items = [
        canonical.finding("metadata", "M2", "note", "b", "m"),
        canonical.finding("license-gate", "L2", "error", "z", "m"),
        canonical.finding("metadata", "M1", "error", "a", "m"),
        canonical.finding("license-gate", "L1", "error", "a", "m"),
    ]
    got = [(f["module"], f["severity"], f["primary_key"]) for f in canonical.sort_findings(items)]
    assert got == [
        ("license-gate", "error", "a"),
        ("license-gate", "error", "z"),
        ("metadata", "error", "a"),
        ("metadata", "note", "b"),
    ]


def test_has_error_only_counts_error_severity():
    assert not canonical.has_error([canonical.finding("metadata", "C", "warn", "k", "m")])
    assert not canonical.has_error([canonical.finding("metadata", "C", "note", "k", "m")])
    assert canonical.has_error([canonical.finding("metadata", "C", "error", "k", "m")])


def test_report_is_byte_identical_across_runs():
    findings = [canonical.finding("license-gate", "FSTYPE_NO_SUBSET", "error", "bit8", "m",
                                  evidence={"fsType": "0x0108"}, spec_ref="MS-OS2 bit8")]
    skips = [canonical.skipped("metadata", "no_name_table", "")]
    first = canonical.dumps(canonical.build_report(findings, skips, {"font": "a.ttf"},
                                                   tool_version="x", fonttools_version="y"))
    second = canonical.dumps(canonical.build_report(list(reversed(findings)), list(skips),
                                                    {"font": "a.ttf"}, tool_version="x",
                                                    fonttools_version="y"))
    assert first == second
    assert first.endswith("\n") and not first.endswith("\n\n")


def test_report_carries_no_timestamp_path_host_or_username():
    """变异：往报告里塞任一禁用项（时间戳/绝对路径/主机名/用户名）→ 本测试必红。

    本机用户名**动态取**（不写死字面量）——写死会让这一行本身成为脱敏门的一处命中，
    等于测试自己制造了它要防的那个缺陷（门比项目更严 = 门错）。
    """
    import getpass
    import platform

    body = canonical.build_report([], [], {"font": "a.ttf"}, tool_version="x",
                                 fonttools_version="y")
    text = canonical.dumps(body)
    banned = ["2026-", "C:\\", "/home/", "127.0.0.1", platform.node()]
    username = ""
    try:
        username = getpass.getuser()
    except Exception:  # noqa: BLE001 - 无登录环境的容器里可能取不到
        username = ""
    for token in banned + ([username] if username else []):
        if not token:
            continue
        assert token not in text, "报告里出现禁用项 %r" % token
    assert body["disclaimer"] and "法律意见" in body["disclaimer"]


def test_input_ref_keeps_only_basename():
    assert canonical.input_ref("C:/windows/fonts/arial.ttf") == "arial.ttf"
    assert canonical.input_ref("/tmp/x/y.ttf") == "y.ttf"


def test_markdown_render_mentions_skips_and_disclaimer():
    body = canonical.build_report([], [canonical.skipped("metadata", "no_os2_table", "d")],
                                  {}, tool_version="x", fonttools_version="y")
    md = canonical.render_markdown(body)
    assert "no_os2_table" in md
    assert "法律意见" in md


def test_digest_is_stable_and_markdown_does_not_affect_it():
    body = canonical.build_report([], [], {}, tool_version="x", fonttools_version="y")
    assert canonical.digest(body) == canonical.digest(body)
    before = canonical.digest(body)
    canonical.render_markdown(body)
    assert canonical.digest(body) == before


# ── sfnt / cmapset ─────────────────────────────────────────────────────────
def test_open_font_missing_path_is_input_error(tmp_path):
    with pytest.raises(canonical.InputError) as exc:
        sfnt.open_font(str(tmp_path / "nope.ttf"))
    assert exc.value.reason == "file_not_found"


def test_open_font_non_font_is_input_error(tmp_path):
    bad = tmp_path / "not-a-font.ttf"
    bad.write_text("this is not a font", encoding="utf-8")
    with pytest.raises(canonical.InputError) as exc:
        sfnt.open_font(str(bad))
    assert "not_an_sfnt_font" in exc.value.reason


def test_unicode_cmap_selected_with_priority_stamp(simple_font):
    font = sfnt.open_font(simple_font)
    try:
        selected, stats = sfnt.select_unicode_cmap(font)
    finally:
        sfnt.close_font(font)
    assert selected and 0x61 in selected
    assert stats["chosen"], "chosen 子表必须被打印（这是『扫到了几个』的自证）"


def test_glyph0_mapping_does_not_count_as_coverage(notdef_mapped_font):
    font = sfnt.open_font(notdef_mapped_font)
    try:
        selected, _ = sfnt.select_unicode_cmap(font)
    finally:
        sfnt.close_font(font)
    cps = cmapset.codepoints(selected)
    assert 0x61 not in cps, "映射到 .notdef 的码位必须视为缺"
    assert 0x62 in cps


def test_classify_three_way_partition():
    result = cmapset.classify(required={0x61, 0x62, 0x5B57}, source={0x61, 0x62},
                              subset={0x61})
    assert result["OK"] == [0x61]
    assert result["LOST_IN_SUBSET"] == [0x62]
    assert result["MISSING_IN_SOURCE"] == [0x5B57]


def test_classify_without_subset_has_no_lost():
    result = cmapset.classify({0x61, 0x62}, {0x61}, None)
    assert result["LOST_IN_SUBSET"] == []
    assert result["OK"] == [0x61]


def test_block_counts_partitions_by_range():
    """§六.4 的互斥分区：ExtA 必须先于 BMP 判（`U+3400` 属于 ExtA，不属于 BMP）。

    这里原先写成 `counts == {...BMP:3, ExtA:1...} or counts["BMP"] == 3` —— 两个分支都要求
    `BMP == 3`，等于把实现里"ExtA 永远不可达"的缺陷**当成期望值**钉住了（M3 实现时发现并更正）。
    """
    counts = cmapset.block_counts([0x61, 0x5B57, 0x20000, 0x3400])
    assert counts == {"BMP": 2, "ExtA": 1, "ExtB+": 1, "other": 0}
    assert sum(counts.values()) == 4, "四块之和必须等于码位总数（互斥分区）"


def test_block_of_exta_wins_over_bmp():
    """单点判据：ExtA 边界值的归属（M3 的回归锚点）。"""
    assert cmapset.block_of(0x3400) == "ExtA"   # ExtA 下界
    assert cmapset.block_of(0x4DBF) == "ExtA"   # ExtA 上界
    assert cmapset.block_of(0x4DC0) == "BMP"    # 紧邻 ExtA 之上仍是 BMP
    assert cmapset.block_of(0x20000) == "ExtB+"  # ExtB+ 下界
    assert cmapset.block_of(0x2FA1F) == "ExtB+"  # ExtB+ 上界
    assert cmapset.block_of(0x2FA20) == "other"  # ExtB+ 之上
    assert cmapset.block_of(0x10FFFF) == "other"


def test_closure_adds_decomposition_and_reports_only_new_codepoints():
    closed, added = cmapset.closure({0x00E9})  # é = U+0065 U+0301 (NFD)
    assert 0x0065 in closed and 0x0301 in closed
    assert added == sorted(set(added)) and 0x00E9 not in added


def test_from_text_drops_line_breaks():
    assert cmapset.from_text("a\nb\r\nc") == {0x61, 0x62, 0x63}


def test_os2_info_reads_fstype_and_version(simple_font):
    font = sfnt.open_font(simple_font)
    try:
        info = sfnt.os2_info(font)
    finally:
        sfnt.close_font(font)
    assert info["fsType"] == 0x0000 and info["version"] == 0
    assert len(info["ulUnicodeRange"]) == 4 and len(info["ulCodePageRange"]) == 2


def test_no_unicode_cmap_reports_reason(tmp_path):
    """只含 (1,0)/format 0 的字体必须给出 no_unicode_cmap，而不是『覆盖为空』。

    与 ``no_cmap_table``（根本没有 cmap 表）是**两条不同**的 SKIPPED 理由，不得合并。
    """
    path = str(tmp_path / "mac.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"}, mac_only=True)

    font = sfnt.open_font(path)
    try:
        selected, stats = sfnt.select_unicode_cmap(font)
        subtables = sfnt.cmap_subtables(font)
    finally:
        sfnt.close_font(font)
    assert selected is None
    assert stats["reason"] == "no_unicode_cmap"
    assert subtables, "这条判据的前提是『有 cmap 表、但没有 Unicode 映射』——空表测的是另一条"


def test_read_only_layer_never_saves():
    """只读纪律：sfnt.py 里不得出现 save( —— 变异：加一行即红。"""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "src", "subsetaudit", "sfnt.py")
    with io.open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    assert ".save(" not in text
    assert "TTFont(" in text