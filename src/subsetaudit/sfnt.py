# -*- coding: utf-8 -*-
"""只读表访问层：唯一允许打开字体的地方。

纪律：
  · 不调用任何 ``save()``（生成 fixture 的写盘代码只在 ``tools/gen_fixtures.py``）；
  · 不缓存跨字体状态、不读时钟、不联网；
  · 打不开 / 不是 sfnt → ``canonical.InputError``（CLI 收口为退出码 2）。

编码优先级见 ``data/README.md`` §六.3：``(3,10) → (0,4) → (3,1) → (0,3)``；
布局表读取口径见 §六.5（三元组枚举 5.1 / Extension 解包 5.2 / 连字规则 5.4）。
"""
from __future__ import print_function

import os

from fontTools.ttLib import TTFont, TTLibError

from .canonical import InputError

# 优先级（§六.3）。同一优先级可能有多个子表 → 取并集。
UNICODE_CMAP_PRIORITY = ((3, 10), (0, 4), (3, 1), (0, 3))

#: 布局表标签（§六.5.1：GSUB 与 GPOS **分开成条**）
LAYOUT_TAGS = ("GSUB", "GPOS")

#: Extension lookup 的外层类型号 → 该表里的"真类型"来自 ``ExtensionLookupType``（§六.5.2）。
#: **必须两个都解**：只解 GSUB 的 7 会让 GPOS 整段读不到（§七 #13）。
EXTENSION_LOOKUP_TYPES = {"GSUB": 7, "GPOS": 9}

#: `LangSysTag` 的两个合成取值（§六.5.1）：`dflt` = `Script.DefaultLangSys`，`all` = 全 langsys 共有的聚合条
LANGSYS_DEFAULT = "dflt"
LANGSYS_ALL = "all"


def open_font(path):
    """只读打开字体；任何失败都转成 ``InputError``（不吞、不猜、不降级）。"""
    if not os.path.isfile(path):
        raise InputError(path, "file_not_found")
    try:
        font = TTFont(path, lazy=True)
    except (TTLibError, Exception) as exc:  # noqa: BLE001 - 上游异常类型随版本变
        raise InputError(path, "not_an_sfnt_font (%s)" % (exc.__class__.__name__,))
    return font


def close_font(font):
    try:
        font.close()
    except Exception:  # noqa: BLE001 - 关闭失败不影响判定
        pass


def os2_info(font):
    """OS/2 关键字段；无表 → ``None``（由调用方报 SKIPPED）。"""
    if "OS/2" not in font:
        return None
    os2 = font["OS/2"]
    return {
        "version": int(getattr(os2, "version", 0)),
        "fsType": int(getattr(os2, "fsType", 0)),
        "ulUnicodeRange": [int(v) for v in (getattr(os2, "ulUnicodeRange1", 0),
                                            getattr(os2, "ulUnicodeRange2", 0),
                                            getattr(os2, "ulUnicodeRange3", 0),
                                            getattr(os2, "ulUnicodeRange4", 0))],
        "ulCodePageRange": [int(getattr(os2, "ulCodePageRange1", 0)),
                            int(getattr(os2, "ulCodePageRange2", 0))],
        "usFirstCharIndex": int(getattr(os2, "usFirstCharIndex", 0)),
        "usLastCharIndex": int(getattr(os2, "usLastCharIndex", 0)),
    }


def cmap_subtables(font):
    """全部子表：``[(platform, encoding, format, mapping)]``；无 cmap → ``[]``。"""
    if "cmap" not in font:
        return []
    out = []
    for sub in font["cmap"].tables:
        out.append((int(sub.platformID), int(sub.platEncID), int(sub.format), sub.cmap))
    return out


def select_unicode_cmap(font):
    """按 §六.3 选 Unicode cmap。

    返回 ``(selected, stats)``：
      · ``selected`` = ``{codepoint: glyphName}``（多个同优先子表取并集）；无 Unicode 映射 → ``None``；
      · ``stats`` = ``{"subtables": [...], "chosen": [[platform, encoding, format, count], ...],
                       "reason": "" | "no_unicode_cmap" | "no_cmap_table"}``
    """
    subs = cmap_subtables(font)
    stats = {
        "subtables": [[p, e, f, len(m)] for (p, e, f, m) in subs],
        "chosen": [],
        "reason": "",
    }
    if not subs:
        stats["reason"] = "no_cmap_table"
        return None, stats

    for pair in UNICODE_CMAP_PRIORITY:
        matched = [(f, m) for (p, e, f, m) in subs if (p, e) == pair]
        if not matched:
            continue
        merged = {}
        for fmt, mapping in matched:
            stats["chosen"].append([pair[0], pair[1], fmt, len(mapping)])
            for cp, glyph in mapping.items():
                if isinstance(cp, int):
                    merged[cp] = glyph
        if merged:
            return merged, stats

    stats["reason"] = "no_unicode_cmap"
    return None, stats


def name_records(font):
    """``{(nameID, langID): value}``；缺表 → ``{}``。"""
    if "name" not in font:
        return {}
    out = {}
    for rec in font["name"].names:
        try:
            value = rec.toUnicode()
        except (UnicodeDecodeError, AttributeError):
            value = ""
        out[(int(rec.nameID), int(rec.langID))] = value
    return out


def table_tags(font):
    return set(font.keys())


def maxp_num_glyphs(font):
    if "maxp" not in font:
        return None
    return int(getattr(font["maxp"], "numGlyphs", 0))


def glyph_count(font):
    """实际字形数：优先 ``glyf``/``CFF`` 的字形顺序长度。"""
    order = font.getGlyphOrder() if hasattr(font, "getGlyphOrder") else []
    return len(order)


# ── 布局表（§六.5；只读，不构造写入对象） ──────────────────────────────────
def layout_table_presence(font):
    """``{"GSUB": bool, "GPOS": bool}`` —— 缺表与空表是两件事（§六.5.5）。"""
    return dict((tag, tag in font) for tag in LAYOUT_TAGS)


def iter_lookup_subtables(lookup, tag):
    """遍历一个 lookup 的**逻辑子表**，把 Extension 解包（§六.5.2）。

    产出 ``(inner_subtable, unwrapped, true_type)``：
      · 非 Extension lookup → ``(原始 SubTable, False, lookup.LookupType)``；
      · Extension lookup（GSUB Type 7 / GPOS Type 9）→
        ``(ExtSubTable, True, ExtensionLookupType)``。

    **为什么必须解包**：外层 SubTable 是 ``ExtensionSubst`` / ``ExtensionPos``，真子表在
    ``ExtSubTable`` 字段里；不解包则连字规则数为 0、GPOS 整段读不到（§四.1 #13 实测）。
    **为什么真类型取 ``ExtensionLookupType``**：§六.5.2 要求按真实类型统计直方图，外层号
    （7/9）只说明"这是层包装"。
    """
    ext_type = EXTENSION_LOOKUP_TYPES.get(tag)
    for subtable in lookup.SubTable:
        # ``hasattr`` 在 lazy 模式下会触发 decompile —— 这正是我们要的（不 decompile 读不到真子表）
        if ext_type is not None and lookup.LookupType == ext_type and hasattr(subtable, "ExtSubTable"):
            yield subtable.ExtSubTable, True, int(subtable.ExtensionLookupType)
        else:
            yield subtable, False, int(lookup.LookupType)


def layout_tables(font):
    """按 §六.5.1/5.2 把 GSUB/GPOS 摊平成**纯数据**（不返回 fontTools 对象，防调用方写回）。

    返回 ``{tag: None | {
        "lookups": int,                 # Lookup 数
        "subtables_raw": int,           # 解包后的逻辑子表数（结论用）
        "subtables_naive": int,         # 不展开 Extension 时**可见**的子表数（只作对照）
        "subtable_types": {int: int},   # 解包后**子表**直方图（键 = 真实类型号）
        "extension_lookups": int,       # 外层类型为 7/9 的 lookup 数
        "ligature_rules_raw": int,      # 解包后 LigatureSubst 的规则数
        "ligature_rules_naive": int,    # 不展开时可见的规则数（只作对照）
        "ligature_features": [str, ...],# 连字 lookup 归属的 feature 标签（已排序）
        "feature_variations": int,      # FeatureVariationRecord 数；无该表 → 0
        "triples": [(script, langsys, feature), ...],  # 已去重、已排序
        "ligatures": [((glyph, component...), ligGlyph), ...],  # 已排序（§六.5.4）
    }}``
    """
    out = {}
    for tag in LAYOUT_TAGS:
        if tag not in font:
            out[tag] = None
            continue
        table = font[tag].table
        out[tag] = _flatten_layout_table(table, tag)
    return out


def _flatten_layout_table(table, tag):
    lookups = list(table.LookupList.Lookup) if table.LookupList is not None else []
    ext_type = EXTENSION_LOOKUP_TYPES.get(tag)
    lookup_features = _lookup_to_features(table)

    type_hist = {}
    subtables_raw = 0
    subtables_naive = 0
    extension_lookups = 0
    lig_rules_raw = 0
    lig_rules_naive = 0
    ligatures = []
    ligature_features = set()

    for index, lookup in enumerate(lookups):
        is_extension = ext_type is not None and int(lookup.LookupType) == ext_type
        if is_extension:
            extension_lookups += 1
        else:
            # §六.5.2：naive 只数**可见**的子表；Extension 包装本身不计（否则虚增）
            subtables_naive += len(lookup.SubTable)
        for inner, unwrapped, true_type in iter_lookup_subtables(lookup, tag):
            subtables_raw += 1
            type_hist[true_type] = type_hist.get(true_type, 0) + 1
            if _is_ligature_subst(inner):
                rules = _ligature_rules(inner)
                lig_rules_raw += len(rules)
                if not unwrapped:
                    lig_rules_naive += len(rules)
                ligatures.extend(rules)
                ligature_features.update(lookup_features.get(index, ()))

    return {
        "lookups": len(lookups),
        "subtables_raw": subtables_raw,
        "subtables_naive": subtables_naive,
        "subtable_types": dict(sorted(type_hist.items())),
        "extension_lookups": extension_lookups,
        "ligature_rules_raw": lig_rules_raw,
        "ligature_rules_naive": lig_rules_naive,
        "ligature_features": sorted(ligature_features),
        "feature_variations": _feature_variation_count(table),
        "triples": _triples(table, tag),
        "ligatures": sorted(ligatures),
    }


def _lookup_to_features(table):
    """``{lookup_index: set(FeatureTag)}`` —— 供连字规则的 finding 归属到 feature（§六.5.4）。"""
    if table.FeatureList is None:
        return {}
    out = {}
    for record in table.FeatureList.FeatureRecord:
        feature = record.Feature
        for index in getattr(feature, "LookupListIndex", None) or []:
            out.setdefault(int(index), set()).add(record.FeatureTag)
    return out


def _is_ligature_subst(subtable):
    return subtable.__class__.__name__ == "LigatureSubst"


def _ligature_rules(subtable):
    """``LigatureSubst`` → ``[((first, comp, ...), lig), ...]``（§六.5.4：按字形名/序，不按数值 GID）。"""
    rules = []
    try:
        ligatures = subtable.ligatures
    except AttributeError:  # pragma: no cover - 非 format 1 的 LigatureSubst 不存在
        return rules
    for first in ligatures:
        for lig in ligatures[first]:
            rules.append(((first,) + tuple(lig.Component), lig.LigGlyph))
    return rules


def _feature_variation_count(table):
    """``FeatureVariationRecord`` 数（§六.5.1：只计数，不产 finding）。"""
    variations = getattr(table, "FeatureVariations", None)
    if variations is None:
        return 0
    records = getattr(variations, "FeatureVariationRecord", None) or []
    return len(records)


def _triples(table, tag):
    """§六.5.1 的三元组枚举：``[(script, langsys, feature)]``，已去重、已排序。"""
    if table.ScriptList is None or table.FeatureList is None:
        return []
    feature_records = table.FeatureList.FeatureRecord
    found = set()

    for script_record in table.ScriptList.ScriptRecord:
        script_tag = script_record.ScriptTag
        per_langsys = {}
        default = script_record.Script.DefaultLangSys
        if default is not None:
            per_langsys[LANGSYS_DEFAULT] = set(default.FeatureIndex)
        for lang_record in script_record.Script.LangSysRecord:
            bucket = per_langsys.setdefault(lang_record.LangSysTag, set())
            bucket.update(lang_record.LangSys.FeatureIndex)
        if not per_langsys:
            continue

        all_tags = set(per_langsys.keys())
        feature_to_langsys = {}
        for langsys_tag, indices in per_langsys.items():
            for index in indices:
                feature_tag = feature_records[int(index)].FeatureTag
                feature_to_langsys.setdefault(feature_tag, set()).add(langsys_tag)

        for feature_tag, where in feature_to_langsys.items():
            # §六.5.1：`all` 是**附加**聚合条，不替代具体标签
            if where == all_tags:
                found.add((script_tag, LANGSYS_ALL, feature_tag))
            for langsys_tag in where:
                found.add((script_tag, langsys_tag, feature_tag))

    return sorted(found)
