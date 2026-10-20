# -*- coding: utf-8 -*-
"""M4 · `layout-survival` 布局保真 —— 真实判定。

    evaluate(source_path, subset_path) -> (findings, skips, summary)

**口径单点 = `data/README.md` §六.5**，本模块只实现、不定义：
  · **5.1** 三元组枚举 `(TableTag, ScriptTag, LangSysTag, FeatureTag)` —— GSUB/GPOS **分开成条**，
    `LangSysTag ∈ {dflt, <原样>, all}`，`all` 是**附加**聚合条，四元组精确去重；
  · **5.2** 子表计数 `subtables_raw / subtables_naive` 与 `ligature_rules_raw / _naive`
    —— **LookupType 7（GSUB）与 9（GPOS）都必须解包**，`naive` 只作对照；
  · **5.3** 判定式 `LAYOUT_FEATURE_LOST`（四元组差集，恒 error）；
  · **5.4** 连字规则判定 `LAYOUT_LIGATURE_LOST` / `LAYOUT_LIGATURE_RENAMED`（按**输入码位序列**比对，
    **不按字形名** —— 子集后 `uniFB01 → glyph00003` 是改名的实测事实）；
  · **5.5** 失败路径：两侧都无布局表 → `SKIPPED(reason=no_layout_tables)`、`summary` 为空；
    只有一侧有 → 照常判定 + `SKIPPED(reason=layout_tables_missing_on_one_side)`；
  · **5.6** 跨表去重的落地约束（GID 空间不同，只比码位视图）。

编排：``sfnt.open_font`` → ``sfnt.layout_tables``（摊平成纯数据）→ 三元组差集 → 连字规则差分
→ 计数归并。**只读**：不写盘、不读时钟、不联网。
"""
from __future__ import print_function

from . import sfnt
from ._skeleton import validate_inputs
from .canonical import finding, skipped

MODULE = "layout-survival"

#: §六.5 —— 布局判定的 `spec_ref` 字面量（**逐字**使用，勿改写措辞）
SPEC_REF = "data/README §6.5"

#: §六.5.3 / 5.4 的 finding 代码
CODE_FEATURE_LOST = "LAYOUT_FEATURE_LOST"
CODE_LIGATURE_LOST = "LAYOUT_LIGATURE_LOST"
CODE_LIGATURE_RENAMED = "LAYOUT_LIGATURE_RENAMED"

#: §六.5.5 的两条 SKIPPED 理由（**不得合并**）
REASON_NO_TABLES = "no_layout_tables"
REASON_ONE_SIDE = "layout_tables_missing_on_one_side"

#: §六.5.4：CLI 无 `--text` 时的显式说明（**不假装过滤过**）
LIGATURE_SCOPE_ALL = "all"


def _triple_key(table_tag, triple):
    """``primary_key`` 形态：``GSUB/hani/ZHS /liga``（§六.5.1 排序键的字面拼法）。"""
    script, langsys, feature = triple
    return "%s/%s/%s/%s" % (table_tag, script, langsys, feature)


def _codepoint_view(font, glyph_names):
    """把字形名映射成**码位视图**（§六.5.6：GID 空间不同，只比码位）。

    返回 ``tuple(codepoints)``；任一字形在 cmap 里没有反查 → ``None``（该规则不参与码位比对）。
    反查用**全部** Unicode 子表的并集（不是 §六.3 的优先级选择）：这里问的是"这个字形叫什么字符"，
    不是"用户能敲出哪些字符"—— 后者是 coverage-diff 的口径，两者语义不同。
    """
    if font is None:
        return None
    reverse = {}
    for _p, _e, _f, mapping in sfnt.cmap_subtables(font):
        for codepoint, glyph in mapping.items():
            if isinstance(codepoint, int) and glyph not in reverse:
                reverse[glyph] = int(codepoint)
    out = []
    for name in glyph_names:
        codepoint = reverse.get(name)
        if codepoint is None:
            return None
        out.append(codepoint)
    return tuple(out)


def _name_state(font, glyph_name):
    """§六.5.4：``placeholder`` ⇔ 名字恰好是 fontTools 的 GID 占位名 ``glyph%05d``。

    实测机制：``pyftsubset`` 默认 ``glyph_names=False`` → 产物 post 降到 3.0，名称丢失；
    fontTools 读入时按 GID **合成** ``glyph00003`` 这类占位名。名字本身不可比，但
    "有没有稳定名字"是可判的事实 —— 这正是 `uniFB01 → glyph00003` 那条实测的落点。
    """
    if font is None or glyph_name is None:
        return None
    try:
        gid = font.getGlyphID(glyph_name)
    except (KeyError, AttributeError):
        return None
    return "placeholder" if glyph_name == "glyph%05d" % gid else "named"


def _ligature_index(flat, font):
    """``{inputs_codepoints: {"glyph": 目标字形名, "state": named|placeholder}}``（§六.5.4）。

    输入字形里只要有任一个不在 cmap 反查里，就跳过该规则（无法建立跨字体的同一性，
    **不猜**）。同一输入序列出现多次时保留首次（`LigatureSet.Ligature` 按优先级排序，
    首次 = 最高优先级，与规范一致）。**目标字形不参与键**（它通常没有 cmap 映射）。
    """
    index = {}
    if flat is None:
        return index
    for inputs, lig_glyph in flat["ligatures"]:
        inputs_cps = _codepoint_view(font, inputs)
        if inputs_cps is None or inputs_cps in index:
            continue
        index[inputs_cps] = {
            "glyph": lig_glyph,
            "state": _name_state(font, lig_glyph),
        }
    return index


def _is_renamed(source_target, subset_target):
    """§六.5.4 的改名判定：两侧都 placeholder **不算**改名（名字两侧都没了，不是"改名"）。"""
    src_state = source_target["state"]
    sub_state = subset_target["state"]
    if src_state == "named" and sub_state == "placeholder":
        return True
    if src_state == "named" and sub_state == "named":
        return source_target["glyph"] != subset_target["glyph"]
    return False


def _u_list(codepoints):
    return ["U+%04X" % cp for cp in codepoints]


def _feature_lost_findings(source_flat, subset_flat):
    """§六.5.3：四元组差集，每个丢失的三元组一条。"""
    out = []
    for table_tag in sfnt.LAYOUT_TAGS:
        src = source_flat[table_tag]
        if src is None:
            continue
        out_set = set(subset_flat[table_tag]["triples"]) if subset_flat[table_tag] else set()
        for triple in src["triples"]:
            if triple in out_set:
                continue
            out.append(finding(
                MODULE, CODE_FEATURE_LOST, "error",
                _triple_key(table_tag, triple),
                "%s 的 %s/%s 布局三元组在产物里消失（原字体存在）" % (
                    table_tag, triple[0], triple[1]),
                evidence={
                    "table": table_tag,
                    "script": triple[0],
                    "langsys": triple[1],
                    "feature": triple[2],
                    "source_present": True,
                    "subset_present": False,
                },
                spec_ref=SPEC_REF,
            ))
    return out


def _ligature_findings(source_font, subset_font, source_flat, subset_flat):
    """§六.5.4：连字规则差分（LOST 优先于 RENAMED，互斥）。"""
    findings = []
    renamed = 0
    lost = 0
    for table_tag in sfnt.LAYOUT_TAGS:
        src = source_flat[table_tag]
        if src is None or not src["ligatures"]:
            continue
        sub = subset_flat[table_tag]
        src_index = _ligature_index(src, source_font)
        sub_index = _ligature_index(sub, subset_font)
        if not src_index:
            continue
        feature = _ligature_feature(src)
        for inputs_cps in sorted(src_index):
            target_src = src_index[inputs_cps]
            key = "%s/%s/%s" % (table_tag, feature, "+".join(_u_list(inputs_cps)))
            if inputs_cps not in sub_index:
                lost += 1
                findings.append(finding(
                    MODULE, CODE_LIGATURE_LOST, "error", key,
                    "%s 连字规则 %s 在产物里消失" % (table_tag, "+".join(_u_list(inputs_cps))),
                    evidence={
                        "table": table_tag,
                        "feature": feature,
                        "inputs": _u_list(inputs_cps),
                        "ligature_source_glyph": target_src["glyph"],
                        "ligature_source_state": target_src["state"],
                        "ligature_subset_glyph": None,
                    },
                    spec_ref=SPEC_REF,
                ))
                continue
            target_out = sub_index[inputs_cps]
            if _is_renamed(target_src, target_out):
                renamed += 1
                findings.append(finding(
                    MODULE, CODE_LIGATURE_RENAMED, "warn", key,
                    "%s 连字规则 %s 仍生效，但目标字形改名（%s → %s）" % (
                        table_tag, "+".join(_u_list(inputs_cps)),
                        target_src["glyph"], target_out["glyph"]),
                    evidence={
                        "table": table_tag,
                        "feature": feature,
                        "inputs": _u_list(inputs_cps),
                        "ligature_source_glyph": target_src["glyph"],
                        "ligature_source_state": target_src["state"],
                        "ligature_subset_glyph": target_out["glyph"],
                        "ligature_subset_state": target_out["state"],
                    },
                    spec_ref=SPEC_REF,
                ))
    return findings, lost, renamed


def _ligature_feature(flat):
    """连字规则归属的 feature 标签（确定性：若含 `liga` 取 `liga`，否则取字母序最小）。

    `sfnt.layout_tables` 给出的是"含连字 lookup 的 feature 标签集合"（已排序）。
    """
    labels = flat.get("ligature_features") or []
    if "liga" in labels:
        return "liga"
    if not labels:
        return "-"
    return labels[0]


def _counts(flat):
    """§六.5.2 的四个计数 + 直方图，按固定键序。"""
    if flat is None:
        return {
            "present": False,
            "lookups": 0,
            "subtables_raw": 0,
            "subtables_naive": 0,
            "extension_lookups": 0,
            "subtable_types": {},
            "ligature_rules_raw": 0,
            "ligature_rules_naive": 0,
            "feature_variations": 0,
        }
    return {
        "present": True,
        "lookups": flat["lookups"],
        "subtables_raw": flat["subtables_raw"],
        "subtables_naive": flat["subtables_naive"],
        "extension_lookups": flat["extension_lookups"],
        # JSON 键必须是字符串：真实类型号作为十进制字符串，排序稳定
        "subtable_types": dict(
            (str(k), v) for k, v in sorted(flat["subtable_types"].items())
        ),
        "ligature_rules_raw": flat["ligature_rules_raw"],
        "ligature_rules_naive": flat["ligature_rules_naive"],
        "feature_variations": flat["feature_variations"],
    }


def _open(path):
    return sfnt.open_font(path)


def evaluate(source_path, subset_path):
    """布局保真：返回 ``(findings, skips, summary)``（形状与 M0 骨架一致，接口不改）。"""
    validate_inputs([source_path, subset_path])  # 不可读 / 非 sfnt → InputError → 退出码 2

    source_font = _open(source_path)
    try:
        subset_font = _open(subset_path)
        try:
            source_flat = sfnt.layout_tables(source_font)
            subset_flat = sfnt.layout_tables(subset_font)
            return _compare(source_flat, subset_flat, source_font, subset_font)
        finally:
            sfnt.close_font(subset_font)
    finally:
        sfnt.close_font(source_font)


def _compare(source_flat, subset_flat, source_font, subset_font):
    src_has = any(source_flat[tag] is not None for tag in sfnt.LAYOUT_TAGS)
    sub_has = any(subset_flat[tag] is not None for tag in sfnt.LAYOUT_TAGS)

    # §六.5.5：两侧都没有 → 显式跳过且 summary 为空（不猜）
    if not src_has and not sub_has:
        return (
            [],
            [skipped(MODULE, REASON_NO_TABLES,
                     "source: 无 GSUB/GPOS；subset: 无 GSUB/GPOS")],
            {},
        )

    skips = []
    if not src_has or not sub_has:
        side = "source" if not src_has else "subset"
        skips.append(skipped(
            MODULE, REASON_ONE_SIDE,
            "%s: 该侧没有 GSUB/GPOS（另一侧有）→ 全量丢失去重报，不放弃整份判定" % side,
        ))

    findings = _feature_lost_findings(source_flat, subset_flat)
    lig_findings, lig_lost, lig_renamed = _ligature_findings(
        source_font, subset_font, source_flat, subset_flat
    )
    findings.extend(lig_findings)
    lost_triples, kept_triples = _triple_delta(source_flat, subset_flat)

    summary = {
        "layout": {
            "spec_ref": SPEC_REF,
            "ligature_scope": LIGATURE_SCOPE_ALL,
            "source": {
                "gsub": _counts(source_flat["GSUB"]),
                "gpos": _counts(source_flat["GPOS"]),
                "triples": _triple_summary(source_flat),
            },
            "subset": {
                "gsub": _counts(subset_flat["GSUB"]),
                "gpos": _counts(subset_flat["GPOS"]),
                "triples": _triple_summary(subset_flat),
            },
            # §六.5.2：`raw` / `kept` / `naive` **分开报**；三者分母不同（前两个数四元组、
            # `naive` 数子表），不得相除当"保留率"。
            "kept": {"triples": kept_triples},
            "lost": {
                "triples": lost_triples,
                "ligature_rules": lig_lost,
                "ligature_renamed": lig_renamed,
            },
        }
    }
    return (findings, skips, summary)


def _triple_summary(flat):
    """三元组按表分开计数（GSUB/GPOS 分开成条，§六.5.1）。"""
    out = {}
    for tag in sfnt.LAYOUT_TAGS:
        value = flat[tag]
        out[tag] = {"present": value is not None,
                    "count": len(value["triples"]) if value is not None else 0}
    return out


def _triple_delta(source_flat, subset_flat):
    """§六.5.2 的 `kept` / `lost`（**跨两侧**的四元组量，与单侧 `raw`/`naive` 分母不同）。

    返回 ``(lost_count, kept_count)``；`lost + kept == |T_src|`（按表分别求交并后求和）。
    """
    lost = 0
    kept = 0
    for tag in sfnt.LAYOUT_TAGS:
        src = source_flat[tag]
        if src is None:
            continue
        src_set = set(src["triples"])
        out_set = set(subset_flat[tag]["triples"]) if subset_flat[tag] is not None else set()
        lost += len(src_set - out_set)
        kept += len(src_set & out_set)
    return lost, kept
