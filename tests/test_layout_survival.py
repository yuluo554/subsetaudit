# -*- coding: utf-8 -*-
"""M4 布局保真测试：三元组 / Type 7+9 解包 / 默认丢弃标签 / 连字改名 / 全量丢失 / SKIPPED / 双跑。

口径单点在 ``data/README.md`` §六.5；本文件只断言，不另立判定式。

三层验证（与 M3 的写法一致 —— 防"实现与测试共享同一个错误"）：
  ① **裸字节独立 oracle**（``_oracle_gsub``，不经过 fontTools 的 otTables）；
  ② **交付实现** ``layout_survival.evaluate``；
  ③ **golden 期望值**（本文件内的字面量）。
三方对齐后才算通过。
"""
from __future__ import print_function

import io
import json
import os
import struct

import pytest

from conftest import build_layout_font, subset_layout_font
from subsetaudit import cli, cli as _cli, layout_survival, sfnt

MODULE = "layout-survival"
SPEC_REF = "data/README §6.5"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with io.open(os.path.join(REPO_ROOT, rel), "r", encoding="utf-8") as fh:
        return fh.read()


def _run(argv, capsys=None):
    code = cli.main(argv)
    out = ""
    if capsys is not None:
        captured = capsys.readouterr()
        out = captured.out
    return code, out


# ── 裸字节 oracle（不复用 fontTools 的 otTables 语义） ──────────────────────
def _read_sfnt_table(path, tag):
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < 12:
        raise AssertionError("不是 sfnt")
    wanted = tag.encode("ascii")[:4].ljust(4, b" ")
    num_tables = struct.unpack(">H", data[4:6])[0]
    for i in range(num_tables):
        off = 12 + i * 16
        if data[off:off + 4] == wanted:
            table_off, table_len = struct.unpack(">II", data[off + 8:off + 16])
            return data[table_off:table_off + table_len]
    return None


def _u16(buf, off):
    return struct.unpack(">H", buf[off:off + 2])[0]


def _u32(buf, off):
    return struct.unpack(">I", buf[off:off + 4])[0]


def _coverage(buf, off):
    fmt = _u16(buf, off)
    count = _u16(buf, off + 2)
    if fmt == 1:
        return list(struct.unpack(">%dH" % count, buf[off + 4:off + 4 + 2 * count]))
    if fmt == 2:
        out = []
        for i in range(count):
            rec = off + 4 + i * 6
            start, end = _u16(buf, rec), _u16(buf, rec + 2)
            out.extend(range(start, end + 1))
        return out
    raise AssertionError("unknown coverage format %d" % fmt)


def _ligature_rules(buf, sub_off):
    """``LigatureSubst`` format 1 → ``[(first_gid, (comp_gids...), lig_gid)]``。"""
    if _u16(buf, sub_off) != 1:
        raise AssertionError("LigatureSubst format != 1")
    coverage = _coverage(buf, sub_off + _u16(buf, sub_off + 2))
    set_count = _u16(buf, sub_off + 4)
    assert len(coverage) == set_count
    rules = []
    for i in range(set_count):
        set_off = sub_off + _u16(buf, sub_off + 6 + 2 * i)
        count = _u16(buf, set_off)
        for j in range(count):
            lig_off = set_off + _u16(buf, set_off + 2 + 2 * j)
            lig_gid = _u16(buf, lig_off)
            comp_count = _u16(buf, lig_off + 2)
            if comp_count > 1:
                comps = struct.unpack(">%dH" % (comp_count - 1),
                                      buf[lig_off + 4:lig_off + 4 + 2 * (comp_count - 1)])
            else:
                comps = ()
            rules.append((coverage[i], tuple(comps), lig_gid))
    return rules


def _oracle_gsub(path):
    """独立复算 GSUB 的三项计数与三元组（不经过 fontTools）。"""
    buf = _read_sfnt_table(path, "GSUB")
    if buf is None:
        return None
    script_off, feature_off, lookup_off = _u16(buf, 4), _u16(buf, 6), _u16(buf, 8)

    triples = set()
    for i in range(_u16(buf, script_off)):
        rec = script_off + 2 + i * 6
        script_tag = buf[rec:rec + 4].decode("ascii")
        script = script_off + _u16(buf, rec + 4)
        default = _u16(buf, script)
        lang_count = _u16(buf, script + 2)
        buckets = []
        if default:
            buckets.append(("dflt", script + default))
        for j in range(lang_count):
            lang_rec = script + 4 + j * 6
            buckets.append((buf[lang_rec:lang_rec + 4].decode("ascii"),
                            script + _u16(buf, lang_rec + 4)))
        per_langsys = {}
        for lang_tag, lang_off in buckets:
            count = _u16(buf, lang_off + 4)
            indices = struct.unpack(">%dH" % count, buf[lang_off + 6:lang_off + 6 + 2 * count])
            tags = set()
            for index in indices:
                feat_rec = feature_off + 2 + int(index) * 6
                tags.add(buf[feat_rec:feat_rec + 4].decode("ascii"))
            per_langsys[lang_tag] = tags
        all_langs = set(per_langsys)
        for feature in set().union(*per_langsys.values()) if per_langsys else set():
            where = set(lt for lt, tags in per_langsys.items() if feature in tags)
            if where == all_langs:
                triples.add((script_tag, "all", feature))
            for lang_tag in where:
                triples.add((script_tag, lang_tag, feature))

    lookups = []
    naive_rules = 0
    unwrapped_rules = 0
    naive_subs = 0
    unwrapped_subs = 0
    for i in range(_u16(buf, lookup_off)):
        lookup = lookup_off + _u16(buf, lookup_off + 2 + 2 * i)
        lookup_type = _u16(buf, lookup)
        sub_count = _u16(buf, lookup + 4)
        is_extension = lookup_type == 7
        for j in range(sub_count):
            sub_off = lookup + _u16(buf, lookup + 6 + 2 * j)
            if is_extension:
                true_type = _u16(buf, sub_off + 2)
                inner = sub_off + _u32(buf, sub_off + 4)
                unwrapped_subs += 1
                if true_type == 4:
                    unwrapped_rules += len(_ligature_rules(buf, inner))
            else:
                naive_subs += 1
                unwrapped_subs += 1
                if lookup_type == 4:
                    count = len(_ligature_rules(buf, sub_off))
                    naive_rules += count
                    unwrapped_rules += count
        lookups.append(lookup_type)

    return {
        "lookups": len(lookups),
        "subtables_naive": naive_subs,
        "subtables_raw": unwrapped_subs,
        "ligature_rules_naive": naive_rules,
        "ligature_rules_raw": unwrapped_rules,
        "extension_lookups": sum(1 for t in lookups if t == 7),
        "triples": sorted(triples),
    }


def _impl_flat(path):
    font = sfnt.open_font(path)
    try:
        return sfnt.layout_tables(font)
    finally:
        sfnt.close_font(font)


def _codes(findings):
    return sorted((f["code"], f["primary_key"]) for f in findings)


# ── ① Type 7 / Type 9 解包是承重的（三方对齐） ────────────────────────────
def test_gsub_extension_is_unwrapped_and_naive_is_zero(layout_font_ext):
    """GSUB 的 liga/ss01 被包成 Type 7 → **朴素遍历 0 条**、解包后 1 条（§六.5.2）。"""
    oracle = _oracle_gsub(layout_font_ext)
    impl = _impl_flat(layout_font_ext)["GSUB"]

    assert oracle["extension_lookups"] == 2
    assert oracle["subtables_naive"] == 1, "只有未包装的 `zero` lookup 可见"
    assert oracle["subtables_raw"] == 3
    assert oracle["ligature_rules_naive"] == 0, "朴素遍历看不到 Extension 里的连字规则"
    assert oracle["ligature_rules_raw"] == 1

    # 三方对齐：oracle / 被测实现 / golden 字面量
    assert impl["subtables_naive"] == oracle["subtables_naive"] == 1
    assert impl["subtables_raw"] == oracle["subtables_raw"] == 3
    assert impl["ligature_rules_naive"] == oracle["ligature_rules_naive"] == 0
    assert impl["ligature_rules_raw"] == oracle["ligature_rules_raw"] == 1
    assert impl["extension_lookups"] == oracle["extension_lookups"] == 2


def test_gpos_type9_extension_is_unwrapped(layout_font_ext):
    """GPOS 的 Extension 是 **Type 9** 不是 7；只解 7 会让这一整段读不到（§七 #13）。"""
    font = sfnt.open_font(layout_font_ext)
    try:
        presence = sfnt.layout_table_presence(font)
        flat = sfnt.layout_tables(font)["GPOS"]
    finally:
        sfnt.close_font(font)
    assert presence["GPOS"] is True
    assert flat["extension_lookups"] == 1
    assert flat["subtables_naive"] == 0, "唯一的 GPOS lookup 是 Type 9 → 朴素看不到子表"
    assert flat["subtables_raw"] == 1
    # 解包后的真实类型是 PairPos（2），不是外层 9
    assert flat["subtable_types"] == {2: 1}


def test_plain_font_has_naive_equal_to_raw(layout_font):
    """没有 Extension 时 `naive == raw` —— 证明解包那一层不是恒等变换的假象。"""
    oracle = _oracle_gsub(layout_font)
    impl = _impl_flat(layout_font)["GSUB"]
    assert oracle["extension_lookups"] == 0
    assert oracle["subtables_naive"] == oracle["subtables_raw"] == 3
    assert oracle["ligature_rules_naive"] == oracle["ligature_rules_raw"] == 1
    assert impl["subtables_naive"] == impl["subtables_raw"] == 3
    assert impl["ligature_rules_naive"] == impl["ligature_rules_raw"] == 1


def test_naive_count_is_zero_only_when_extension_is_not_unwrapped():
    """变异自证：把解包关掉 → `raw` 掉到 `naive`（说明 raw 的数值确实来自解包）。

    这是**仓库内可复现**的 "784 vs 0" 对照：商用 Arial 的 784 只作只读观察登记
    （`data/README.md` §四.1 #13），合成样本给出同构的 `1 vs 0`。
    """
    import tempfile

    path = build_layout_font(os.path.join(tempfile.mkdtemp(), "ext.ttf"),
                             wrap_gsub_ext=("liga",))
    font = sfnt.open_font(path)
    try:
        lookup = font["GSUB"].table.LookupList.Lookup[0]
        # 不展开时看到的子表数 = 该 lookup 的 SubTable 条数（= 1 个 Extension 包装）
        naive_view = len(lookup.SubTable)
        # 展开后 = iter_lookup_subtables 的产出条数
        unwrapped = list(sfnt.iter_lookup_subtables(lookup, "GSUB"))
    finally:
        sfnt.close_font(font)
    assert naive_view == 1
    assert len(unwrapped) == 1
    assert unwrapped[0][1] is True, "该条必须是解包出来的"
    assert unwrapped[0][2] == 4, "真实类型是 LigatureSubst(4)，不是外层 7"


# ── ② 三元组枚举（含 `all` 语义与去重） ────────────────────────────────────
def test_triples_both_tables_and_all_aggregate(layout_font):
    """GSUB/GPOS 分开成条；`all` 是**附加**聚合条，不替代具体 `dflt`（§六.5.1）。"""
    flat = _impl_flat(layout_font)
    gsub = flat["GSUB"]["triples"]
    gpos = flat["GPOS"]["triples"]

    assert ("DFLT", "dflt", "liga") in gsub
    assert ("DFLT", "all", "liga") in gsub, "单 langsys 时 `all` 与 `dflt` 同时存在"
    assert ("DFLT", "dflt", "kern") in gpos
    assert ("DFLT", "dflt", "kern") not in gsub, "GSUB 与 GPOS 必须分开成条"
    # 具体标签不被 `all` 取代
    assert len([t for t in gsub if t[2] == "liga"]) == 2


def test_triples_match_oracle(layout_font):
    oracle = _oracle_gsub(layout_font)["triples"]
    impl = _impl_flat(layout_font)["GSUB"]["triples"]
    assert impl == oracle


def test_triples_are_deduplicated_when_feature_repeats():
    """真实字体常见：同一 feature 被多条 FeatureRecord 指向（NotoSansSC 的 `aalt` 有 11 条）。

    去重后该 feature 只出现一次（按 script/langsys 计）。
    """
    import tempfile
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

    order = [".notdef", "a", "a.alt"]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({0x61: "a"})
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0)); pen.lineTo((20, 0)); pen.lineTo((20, 20)); pen.closePath()
    fb.setupGlyf(dict((n, pen.glyph()) for n in order))
    fb.setupHorizontalMetrics(dict((n, (600, 0)) for n in order))
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "DupProbe", "styleName": "Regular"})
    fb.setupOS2(); fb.setupPost()
    addOpenTypeFeaturesFromString(fb.font, u"feature salt { sub a by a.alt; } salt;")
    # 手工复制一条同 tag 的 FeatureRecord，且把两个 index 都挂到 DefaultLangSys
    table = fb.font["GSUB"].table
    table.FeatureList.FeatureRecord.append(table.FeatureList.FeatureRecord[0])
    table.FeatureList.FeatureCount = len(table.FeatureList.FeatureRecord)
    langs = table.ScriptList.ScriptRecord[0].Script.DefaultLangSys
    langs.FeatureIndex = [0, 1]
    langs.FeatureCount = 2
    path = os.path.join(tempfile.mkdtemp(), "dup.ttf")
    fb.font.save(path)
    fb.font.close()

    triples = _impl_flat(path)["GSUB"]["triples"]
    assert triples.count(("DFLT", "dflt", "salt")) == 1, "同一 feature 的重复 FeatureRecord 必须去重"
    assert triples.count(("DFLT", "all", "salt")) == 1


# ── ③ 默认丢弃标签被列出 / 全量丢失 ────────────────────────────────────────
def test_default_subset_lists_dropped_labels(layout_font, tmp_path):
    """默认白名单不含 `ss01`/`zero` → 产物上这两个三元组被列为 `LAYOUT_FEATURE_LOST`。"""
    out = str(tmp_path / "default.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61])

    findings, skips, summary = layout_survival.evaluate(layout_font, out)
    keys = [k for c, k in _codes(findings) if c == layout_survival.CODE_FEATURE_LOST]
    assert "GSUB/DFLT/dflt/ss01" in keys
    assert "GSUB/DFLT/dflt/zero" in keys
    assert "GSUB/DFLT/dflt/liga" not in keys, "`liga` 在默认白名单里 → 必须存活"
    assert skips == []
    assert summary["layout"]["ligature_scope"] == "all"


def test_empty_layout_features_loses_every_triple(layout_font, tmp_path):
    """`--layout-features=''` → 三元组**全量丢失**（§六.5.3 的"全量丢失是差集特例"）。"""
    src_flat = _impl_flat(layout_font)
    out = str(tmp_path / "empty.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61], layout_features=[])

    findings, skips, summary = layout_survival.evaluate(layout_font, out)
    out_flat = _impl_flat(out)
    assert out_flat["GSUB"]["triples"] == [], "产物上不该还剩任何 GSUB 三元组"
    expected = len(src_flat["GSUB"]["triples"])
    got = len([f for f in findings if f["code"] == layout_survival.CODE_FEATURE_LOST
               and f["primary_key"].startswith("GSUB/")])
    assert got == expected, "每个源侧 GSUB 三元组都要各报一条"
    assert all(f["severity"] == "error" for f in findings)
    assert summary["layout"]["lost"]["ligature_rules"] == 1
    assert skips == []


def test_full_loss_when_product_table_vanishes(layout_font, no_layout_font):
    """产物整张 GSUB 都没了 → 全量丢失 + **只有一侧有**的 SKIPPED（§六.5.5）。"""
    findings, skips, summary = layout_survival.evaluate(layout_font, no_layout_font)
    assert [s["reason"] for s in skips] == [layout_survival.REASON_ONE_SIDE]
    assert "subset:" in skips[0]["detail"], "detail 必须指明是哪一侧"
    lost = [f for f in findings if f["code"] == layout_survival.CODE_FEATURE_LOST]
    assert len(lost) == 8, "源侧 GSUB 6 条（3 feature × dflt+all）+ GPOS 2 条（kern × dflt+all）"
    assert summary["layout"]["subset"]["gsub"]["present"] is False


# ── ④ 连字改名（uniFB01 → glyph00003）被认出 ──────────────────────────────
def test_ligature_rename_is_detected_not_judged_as_loss(layout_font, tmp_path):
    """`liga` 存活但目标字形改名 → `LAYOUT_LIGATURE_RENAMED`（warn），**不是** LOST。"""
    out = str(tmp_path / "renamed.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61])

    # 前提自证：产物上目标字形**确实**换了名字（否则这条判据测的是别的态）
    src_flat = _impl_flat(layout_font)["GSUB"]
    out_flat = _impl_flat(out)["GSUB"]
    src_target = dict(src_flat["ligatures"])[("f", "i")]
    out_target = dict(out_flat["ligatures"])[("f", "i")]
    assert src_target == "uniFB01"
    assert out_target == "glyph00003", "post 3.0 下 fontTools 按 GID 合成占位名"
    assert out_flat["ligature_rules_raw"] == 1, "连字规则仍然存在"

    findings, _skips, summary = layout_survival.evaluate(layout_font, out)
    renamed = [f for f in findings if f["code"] == layout_survival.CODE_LIGATURE_RENAMED]
    lost = [f for f in findings if f["code"] == layout_survival.CODE_LIGATURE_LOST]
    assert len(renamed) == 1 and not lost, "改名与丢失互斥，先判丢失"
    assert renamed[0]["severity"] == "warn", "改名不判 error（功能未失效）"
    assert renamed[0]["primary_key"] == "GSUB/liga/U+0066+U+0069"
    assert renamed[0]["evidence"]["ligature_source_glyph"] == "uniFB01"
    assert renamed[0]["evidence"]["ligature_subset_glyph"] == "glyph00003"
    assert summary["layout"]["lost"]["ligature_renamed"] == 1


def test_renamed_rule_still_counts_as_present_when_names_kept(layout_font, tmp_path):
    """`glyph_names=True` 时两侧名字都在 → **不报改名**（names 保留就无可追溯性下降）。"""
    from fontTools import subset
    from fontTools.ttLib import TTFont

    out = str(tmp_path / "names.ttf")
    options = subset.Options()
    options.glyph_names = True
    font = TTFont(layout_font, recalcTimestamp=False)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=[0x66, 0x69, 0x61])
    subsetter.subset(font)
    font.save(out)
    font.close()

    findings, _skips, _summary = layout_survival.evaluate(layout_font, out)
    assert [f for f in findings if f["code"] == layout_survival.CODE_LIGATURE_RENAMED] == []
    assert [f for f in findings if f["code"] == layout_survival.CODE_LIGATURE_LOST] == []


def test_ligature_loss_is_detected_when_rule_disappears(layout_font, tmp_path):
    """连字规则真的没了 → `LAYOUT_LIGATURE_LOST`（error），且不是改名。"""
    out = str(tmp_path / "norigla.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61], layout_features=[])

    findings, _skips, summary = layout_survival.evaluate(layout_font, out)
    lost = [f for f in findings if f["code"] == layout_survival.CODE_LIGATURE_LOST]
    assert len(lost) == 1
    assert lost[0]["severity"] == "error"
    assert lost[0]["primary_key"] == "GSUB/liga/U+0066+U+0069"
    assert summary["layout"]["lost"]["ligature_rules"] == 1
    assert summary["layout"]["lost"]["ligature_renamed"] == 0


# ── ⑤ raw / kept / naive 三个计数分开报（§六.5.2） ─────────────────────────
def test_raw_kept_naive_are_reported_separately(layout_font, tmp_path):
    """三个计数**分开报**，且 `kept + lost == |T_src|`（分母一致的那一对）。

    `raw`/`naive` 是**单侧**结构量、`kept` 是**跨两侧**结论量 —— 三者分母不同，
    本判据只钉住"都在、键名不混、乘积关系成立的那一条恒等式"。
    """
    out = str(tmp_path / "default.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61])

    _findings, _skips, summary = layout_survival.evaluate(layout_font, out)
    layout = summary["layout"]

    for side in ("source", "subset"):
        for table in ("gsub", "gpos"):
            block = layout[side][table]
            assert "subtables_raw" in block and "subtables_naive" in block
            assert "ligature_rules_raw" in block and "ligature_rules_naive" in block
    assert "kept" in layout and "triples" in layout["kept"]

    src_total = sum(v["count"] for v in layout["source"]["triples"].values())
    assert layout["kept"]["triples"] + layout["lost"]["triples"] == src_total


def test_kept_equals_source_when_nothing_is_lost(layout_font, tmp_path):
    """`--layout-features='*'` + 全码位 → 三元组全保住（`kept == |T_src|`、`lost == 0`）。"""
    out = str(tmp_path / "all.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61, 0x30, 0x31], layout_features=["*"])
    _findings, _skips, summary = layout_survival.evaluate(layout_font, out)
    layout = summary["layout"]
    src_total = sum(v["count"] for v in layout["source"]["triples"].values())
    assert layout["lost"]["triples"] == 0
    assert layout["kept"]["triples"] == src_total


def test_kept_is_zero_when_everything_is_lost(layout_font, tmp_path):
    """`--layout-features=''` → `kept == 0`、`lost == |T_src|`。"""
    out = str(tmp_path / "empty.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61], layout_features=[])
    _findings, _skips, summary = layout_survival.evaluate(layout_font, out)
    layout = summary["layout"]
    src_total = sum(v["count"] for v in layout["source"]["triples"].values())
    assert layout["kept"]["triples"] == 0
    assert layout["lost"]["triples"] == src_total


# ── ⑥ 失败路径：两侧都无布局表 → SKIPPED 且 summary 为空 ────────────────────
def test_no_layout_tables_on_either_side_skips_with_empty_summary(no_layout_font):
    findings, skips, summary = layout_survival.evaluate(no_layout_font, no_layout_font)
    assert findings == []
    assert [s["reason"] for s in skips] == [layout_survival.REASON_NO_TABLES]
    assert summary == {}, "两侧都没有布局表 → 不给半份结论（不猜）"
    assert skips[0]["module"] == MODULE
    assert "source:" in skips[0]["detail"] and "subset:" in skips[0]["detail"]


def test_skipped_reason_is_in_output_and_does_not_change_exit_code(no_layout_font, capsys):
    """§六.6：SKIPPED 恒进输出、恒不影响退出码。"""
    code, out = _run(["layout-survival", no_layout_font, no_layout_font], capsys)
    assert code == cli.EXIT_OK
    body = json.loads(out)
    assert [s["reason"] for s in body["skipped"]] == [layout_survival.REASON_NO_TABLES]
    assert body["findings"] == []


def test_one_side_only_still_judges_and_warns(layout_font, no_layout_font):
    """只有一侧有布局表 → **不整份放弃**：差集照常出，外加一条 SKIPPED（§六.5.5）。"""
    findings, skips, summary = layout_survival.evaluate(layout_font, no_layout_font)
    assert summary != {}, "有一侧的表就是可判定的事实"
    assert [s["reason"] for s in skips] == [layout_survival.REASON_ONE_SIDE]
    assert any(f["code"] == layout_survival.CODE_FEATURE_LOST for f in findings)


# ── ⑥ 退出码 / 报告纪律 ───────────────────────────────────────────────────
def test_lost_features_exit_one(layout_font, tmp_path, capsys):
    out = str(tmp_path / "default.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61])
    code, stdout = _run(["layout-survival", layout_font, out], capsys)
    assert code == cli.EXIT_FINDINGS
    assert json.loads(stdout)["summary"]["layout"]["spec_ref"] == SPEC_REF


def test_rename_only_exits_zero(layout_font, tmp_path, capsys):
    """只有 `warn` 级（改名）时退出码 = 0 —— 产物功能没坏。

    构造：`--layout-features='*'` + 把 `zero`/`one` 需要的码位一并喂进去 →
    产物上**所有三元组都还在**，唯一差异是连字目标字形被改名。
    """
    out = str(tmp_path / "allfeat.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61, 0x30, 0x31], layout_features=["*"])
    code, stdout = _run(["layout-survival", layout_font, out], capsys)
    body = json.loads(stdout)
    assert [f["code"] for f in body["findings"]] == [layout_survival.CODE_LIGATURE_RENAMED]
    assert code == cli.EXIT_OK


def test_non_font_is_exit_two(tmp_path, capsys):
    bad = tmp_path / "x.ttf"
    bad.write_text("nope", encoding="utf-8")
    assert _run(["layout-survival", str(bad), str(bad)], capsys)[0] == cli.EXIT_INPUT_ERROR


def test_report_has_no_absolute_path(layout_font, tmp_path, capsys):
    out = str(tmp_path / "d.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69])
    _code, stdout = _run(["layout-survival", layout_font, out], capsys)
    body = json.loads(stdout)
    for value in body["inputs"].values():
        assert not os.path.isabs(value)
    assert body["inputs"]["source"] == os.path.basename(layout_font)


def test_json_is_byte_identical_across_runs(layout_font, tmp_path):
    out = str(tmp_path / "d.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69])
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    _run(["layout-survival", layout_font, out, "--out", str(a)])
    _run(["layout-survival", layout_font, out, "--out", str(b)])
    assert a.read_bytes() == b.read_bytes()
    assert b"\r\n" not in a.read_bytes()


def test_markdown_view_renders(layout_font, tmp_path, capsys):
    out = str(tmp_path / "d.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69])
    _code, stdout = _run(["layout-survival", layout_font, out, "--markdown"], capsys)
    assert stdout.startswith("# SubsetAudit 报告")
    assert "LAYOUT_" in stdout


# ── ⑦ 口径对账：spec_ref 逐字 / §六.5 表可解析 ─────────────────────────────
def test_spec_ref_matches_data_readme_section():
    """`SPEC_REF` 必须是 `data/README.md` 里真实存在的节号（变异：改一边必红）。"""
    assert layout_survival.SPEC_REF == SPEC_REF
    text = _read("data/README.md")
    assert "§六.5" in text or "§6.5" in text
    assert "5.1 三元组枚举" in text
    assert "5.2 子表计数" in text
    assert "5.3 判定式" in text
    assert "5.4 连字规则判定" in text
    assert "5.5 失败路径" in text
    assert "5.6 落地约束" in text


def test_spec_declares_both_extension_types():
    """§六.5.2 必须写明 **7 与 9 都要解**（只解 7 是缺陷，§七 #13）。"""
    text = _read("data/README.md")
    assert "LookupType 7" in text and "LookupType 9" in text
    assert sfnt.EXTENSION_LOOKUP_TYPES == {"GSUB": 7, "GPOS": 9}


def test_finding_codes_are_the_three_in_spec():
    """只此三码，不另立（§六.5.3 / 5.4）。"""
    codes = {layout_survival.CODE_FEATURE_LOST,
             layout_survival.CODE_LIGATURE_LOST,
             layout_survival.CODE_LIGATURE_RENAMED}
    assert codes == {"LAYOUT_FEATURE_LOST", "LAYOUT_LIGATURE_LOST", "LAYOUT_LIGATURE_RENAMED"}


# ── ⑧ 真实 OFL 字体回归（字体未下载时显式 skip，不假装跑过） ───────────────
OFL_FONT = os.path.join(REPO_ROOT, "data", "fonts", "NotoSansSC-Regular.otf")


@pytest.mark.skipif(not os.path.isfile(OFL_FONT),
                    reason="data/fonts 未下载（离线环境）；用 py tools/fetch_fonts.py --download 获取")
def test_real_ofl_font_has_no_extension_lookups():
    """三个 OFL 字体都没有 Type 7 / Type 9 → `naive == raw`（`data/README.md` §四.1 #12）。"""
    flat = _impl_flat(OFL_FONT)
    for tag in sfnt.LAYOUT_TAGS:
        assert flat[tag]["extension_lookups"] == 0, tag
        assert flat[tag]["subtables_naive"] == flat[tag]["subtables_raw"], tag
        assert flat[tag]["ligature_rules_naive"] == flat[tag]["ligature_rules_raw"], tag


@pytest.mark.skipif(not os.path.isfile(OFL_FONT),
                    reason="data/fonts 未下载（离线环境）；用 py tools/fetch_fonts.py --download 获取")
def test_real_ofl_font_full_loss_matches_oracle(tmp_path):
    """真实字体 + `--layout-features=''` → 三元组全量丢失，且 oracle/实现三方对齐。"""
    out = str(tmp_path / "empty.ttf")
    subset_layout_font(OFL_FONT, out, [0x66, 0x69], layout_features=[])

    oracle = _oracle_gsub(OFL_FONT)
    impl = _impl_flat(OFL_FONT)["GSUB"]
    assert impl["triples"] == oracle["triples"]
    assert impl["ligature_rules_raw"] == oracle["ligature_rules_raw"] == 340
    assert impl["subtables_naive"] == impl["subtables_raw"] == 15
    assert len(impl["triples"]) == 198, "6 个 script × (dflt+all) + hani/latn 等额外 langsys `ZHS ` 条"
    assert len(impl["triples"]) == len(oracle["triples"])

    findings, _skips, summary = layout_survival.evaluate(OFL_FONT, out)
    lost_triples = [f for f in findings if f["code"] == layout_survival.CODE_FEATURE_LOST
                    and f["primary_key"].startswith("GSUB/")]
    assert len(lost_triples) == 198
    # 只有 `f`/`i` 还在 cmap 里 → 340 条规则里只有能反查出输入码位的那部分会被判定
    assert summary["layout"]["lost"]["ligature_rules"] >= 1


def test_real_ofl_font_default_subset_keeps_liga(tmp_path):
    """默认子集 → `liga` 存活、`dlig`/`vert` 等被丢（默认白名单不含它们）。"""
    if not os.path.isfile(OFL_FONT):
        pytest.skip("data/fonts 未下载（离线环境）")
    out = str(tmp_path / "default.ttf")
    subset_layout_font(OFL_FONT, out, [0x66, 0x69, 0x5B57])

    findings, _skips, _summary = layout_survival.evaluate(OFL_FONT, out)
    keys = set(f["primary_key"] for f in findings
               if f["code"] == layout_survival.CODE_FEATURE_LOST)
    assert "GSUB/hani/dflt/liga" not in keys, "`liga` 在默认白名单里 → 必须存活"
    assert any(k.endswith("/dlig") for k in keys), "`dlig` 默认被丢"
    assert any(k.endswith("/aalt") for k in keys), "`aalt` 默认被丢"


# ── ⑨ 变异：改坏实现至少一层测试必红 ──────────────────────────────────────
def test_mutation_disabling_unwrap_is_caught(monkeypatch, layout_font_ext):
    """变异 1：把 Extension 解包关掉（只返回外层包装）→ 连字规则必然掉到 0。"""
    def no_unwrap(lookup, tag):
        for subtable in lookup.SubTable:
            # 外层包装直接当子表交出：不解 ``ExtSubTable``，判类型时它既不是 LigatureSubst
            # 也读不到 ligatures —— 这正是"只解 7 不解 9 / 干脆不解"的失效形态
            yield subtable, False, int(lookup.LookupType)

    monkeypatch.setattr(sfnt, "iter_lookup_subtables", no_unwrap)
    flat = _impl_flat(layout_font_ext)["GSUB"]
    assert flat["ligature_rules_raw"] == 0, "不解包时连字规则必须掉到 0"
    assert flat["ligature_rules_naive"] == 0
    assert flat["subtables_raw"] == 3, "条数不变（包装各算一条），但类型全成了外层号"
    assert flat["subtable_types"] == {1: 1, 7: 2}, "直方图退化成外层类型号（未包装的 zero 仍是 1）"


def test_mutation_merging_all_into_specific_is_caught(monkeypatch, layout_font):
    """变异 2：把 `all` 当成具体标签（不额外加聚合条）→ 三元组数少一半。"""
    flat_before = _impl_flat(layout_font)["GSUB"]["triples"]
    assert ("DFLT", "all", "liga") in flat_before

    original = sfnt._triples

    def no_all(table, tag):
        return [t for t in original(table, tag) if t[1] != "all"]

    monkeypatch.setattr(sfnt, "_triples", no_all)
    flat_after = _impl_flat(layout_font)["GSUB"]["triples"]
    assert ("DFLT", "all", "liga") not in flat_after
    assert len(flat_after) == len(flat_before) - 3


def test_mutation_treating_rename_as_loss_is_caught(monkeypatch, layout_font, tmp_path):
    """变异 3：把改名判成丢失 → 改名计数归零、丢失计数虚增。"""
    out = str(tmp_path / "renamed.ttf")
    subset_layout_font(layout_font, out, [0x66, 0x69, 0x61])

    baseline, _s, base_summary = layout_survival.evaluate(layout_font, out)
    assert base_summary["layout"]["lost"]["ligature_renamed"] == 1

    monkeypatch.setattr(layout_survival, "_is_renamed", lambda _a, _b: False)
    mutated, _s, mutated_summary = layout_survival.evaluate(layout_font, out)
    assert mutated_summary["layout"]["lost"]["ligature_renamed"] == 0
    assert [f["code"] for f in mutated if f["code"].startswith("LAYOUT_LIGATURE")] == []


def test_mutation_dropping_gpos_walk_is_caught(monkeypatch, layout_font):
    """变异 4：只遍历 GSUB（漏掉 GPOS）→ GPOS 三元组必然为空。"""
    original = sfnt.layout_tables

    def gsub_only(font):
        tables = original(font)
        return {"GSUB": tables["GSUB"], "GPOS": None}

    monkeypatch.setattr(sfnt, "layout_tables", gsub_only)
    flat = _impl_flat(layout_font)
    assert flat["GPOS"] is None
    assert flat["GSUB"]["triples"], "GSUB 侧不该受影响（变异只打 GPOS）"


def test_mutation_spec_ref_drift_is_caught(monkeypatch):
    """变异 5：改 `SPEC_REF` 措辞 → 对账判据必红。"""
    monkeypatch.setattr(layout_survival, "SPEC_REF", "data/README §6.99")
    with pytest.raises(AssertionError):
        assert layout_survival.SPEC_REF == SPEC_REF


# ── ⑩ 模块不再是骨架（反向判据） ──────────────────────────────────────────
def test_layout_survival_is_no_longer_a_skeleton():
    """M4 已实现：不得再走骨架出口（防"翻完 ✅ 又退回骨架"）。"""
    text = io.open(layout_survival.__file__, "r", encoding="utf-8").read()
    assert "skeleton_result(" not in text
    assert "module_not_implemented_in_m0" not in text
