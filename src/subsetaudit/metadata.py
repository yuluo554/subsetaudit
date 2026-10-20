# -*- coding: utf-8 -*-
"""M5 · `metadata` 元数据与位域一致性 —— 真实判定。

    evaluate(subset_path, source_path=None) -> (findings, skips, summary)

**口径单点 = `data/README.md` §六.9**，本模块只实现、不定义：
  · **9.1** name 存活（必查 0/7/11/13/14/16/17），缺 13/14 分「默认剥离」与「原作者没写」
    —— 两者的分界是 `--source`：**无源只能看到"缺"，分不出责任 → 不产 finding**；
  · **9.2** `ulCodePageRange` ↔ `C`：**只判 bit0（Latin-1）**，且按码位范围判，
    不是"是否为 0"；回退置位是 `recalcCodePageRanges` 的已知行为；
  · **9.3** `ulUnicodeRange` **不对称判定**：只判"过度声明"（位置了、cmap 无覆盖），
    **欠声明不判**、**全零不判**（`ulUnicodeRange1 = 0` 在 CJK 子集里是正确重算 —— §七 #3）；
  · **9.4** `maxp.numGlyphs` vs **独立量**（`loca` 条目 / CFF `CharStrings`），不用 `getGlyphOrder` 自证；
  · **9.5** `usFirstCharIndex/usLastCharIndex` ↔ `C` 的 BMP 子集，只判"没覆盖住"方向，`0xFFFF` 是哨兵；
  · **9.6** 四条失败路径（`no_os2_table` / `no_name_table` / `no_cmap_table` / `no_unicode_cmap`），
    各自一条 `SKIPPED`、`summary` 为空、退出码 0；
  · **9.7** `report` 聚合只有一条路径（见 `report.evaluate`）。

编排：``sfnt.open_font`` → name / OS/2 / cmap 各取一次纯数据 → 五组判定 → 计数归并。
**只读**：不写盘、不读时钟、不联网。
"""
from __future__ import print_function

from . import sfnt
from ._skeleton import validate_inputs
from .canonical import finding, skipped

MODULE = "metadata"

#: §六.9 —— 元数据判定的 `spec_ref` 字面量（**逐字**使用，勿改写措辞）
SPEC_REF = "data/README §6.9"

#: §六.9.1：必查的七个 name ID（顺序即 `primary_key` 的排序基准）
REQUIRED_NAME_IDS = (0, 7, 11, 13, 14, 16, 17)

#: §六.9.1：ID → (finding code, spec_ref)，**只此七条**
NAME_CODES = {
    0: ("NAME_COPYRIGHT_STRIPPED", "MS-NAME nameID0"),
    7: ("NAME_TRADEMARK_STRIPPED", "MS-NAME nameID7"),
    11: ("NAME_VENDOR_URL_STRIPPED", "MS-NAME nameID11"),
    13: ("NAME_LICENSE_DESCRIPTION_STRIPPED", "MS-NAME nameID13"),
    14: ("NAME_LICENSE_INFO_URL_STRIPPED", "MS-NAME nameID14"),
    16: ("NAME_TYPOGRAPHIC_FAMILY_STRIPPED", "MS-NAME nameID16"),
    17: ("NAME_TYPOGRAPHIC_SUBFAMILY_STRIPPED", "MS-NAME nameID17"),
}

#: §六.9.1 的三种分类（**无源时恒为 `unclassified`**）
CLASS_DEFAULT_STRIPPED = "default_stripped"
CLASS_AUTHOR_ABSENT = "author_absent"
CLASS_UNCLASSIFIED = "unclassified"
CLASSES = (CLASS_DEFAULT_STRIPPED, CLASS_AUTHOR_ABSENT, CLASS_UNCLASSIFIED)

#: §六.9.2 的唯一码页判定：bit0 = Latin-1，整个字符集落在 `U+0000–U+00FF`
CODE_CODEPAGE_LATIN1 = "CODEPAGE_CLAIMS_LATIN1_WITHOUT_COVERAGE"
CODEPAGE_LATIN1_SPEC_REF = "fontTools O_S_2f_2.recalcCodePageRanges"
LATIN1_HI = 0x00FF

#: §六.9.3：只判过度声明；块范围单点 = fontTools 的 v1.7 表（本仓库**不复制**该表）
CODE_UNICODE_OVER = "UNICODE_RANGE_OVER_DECLARED"
UNICODE_RANGE_SPEC_REF = "MS-OS2 §ulUnicodeRange"

#: §六.9.4
CODE_MAXP_MISMATCH = "MAXP_NUM_GLYPHS_MISMATCH"
MAXP_SPEC_REF = "MS-maxp §numGlyphs"

#: §六.9.5
CODE_CHAR_INDEX = "CHAR_INDEX_MISMATCH"
CHAR_INDEX_SPEC_REF = "MS-OS2 §usFirstCharIndex"
SENTINEL_FFFF = 0xFFFF
BMP_LIMIT = 0xFFFE  # 0xFFFF 是哨兵值，不参与 BMP 范围

#: §六.9.6：四条失败理由（**不得合并**）；后两条复用 §六.3 的名字
REASON_NO_OS2 = "no_os2_table"
REASON_NO_NAME = "no_name_table"
REASON_NO_CMAP_TABLE = "no_cmap_table"
REASON_NO_UNICODE_CMAP = "no_unicode_cmap"

#: §六.9.4 的附加 SKIPPED（取不到独立字形量时）
REASON_NO_OUTLINE = "no_outline_table"


# ── 位域工具（纯函数，便于变异测试单独打） ──────────────────────────────────
def set_bits(word, base=0):
    """一个 32 位字里置位的位号集合（`base` 把 4 个词拼成 0–127 的位号空间）。"""
    word = int(word or 0)
    return set(base + i for i in range(32) if word & (1 << i))


def os2_bits(os2):
    """把 ``sfnt.os2_info`` 的位域摊成两个位号集合：``(unicode_bits, codepage_bits)``。"""
    unicode_bits = set()
    for index, word in enumerate(os2["ulUnicodeRange"]):
        unicode_bits |= set_bits(word, 32 * index)
    codepage_bits = set_bits(os2["ulCodePageRange"][0], 0) | set_bits(os2["ulCodePageRange"][1], 32)
    return unicode_bits, codepage_bits


def unicode_range_block_ranges(bit):
    """位号 → 该位声明的**码位区间列表**；表里没有该位 → ``None``。

    块范围来自 ``fontTools.ttLib.tables.O_S_2f_2.OS2_UNICODE_RANGES``（OpenType v1.7 数据，
    123 个块）。**本仓库不复制这张表** —— 复制即第二套口径（§六.9.3）。
    """
    from fontTools.ttLib.tables import O_S_2f_2 as os2_module

    table = os2_module.OS2_UNICODE_RANGES
    if bit < 0 or bit >= len(table):
        return None
    return [tuple(rng) for _name, rng in table[bit]]


def unicode_range_block_names(bit):
    from fontTools.ttLib.tables import O_S_2f_2 as os2_module

    table = os2_module.OS2_UNICODE_RANGES
    if bit < 0 or bit >= len(table):
        return []
    return [name for name, _rng in table[bit]]


#: 代理区（`Non-Plane 0 *` 在表里写的就是这一段；它本身不含任何可编码字符）
SURROGATE_LO, SURROGATE_HI = 0xD800, 0xDFFF


def is_behavioral_bit(bit):
    """该位是不是**行为型**位（§六.9.3 的 `Non-Plane 0 *`）。

    识别方式照口径：该位在 `OS2_UNICODE_RANGES` 里的**全部**区间都落在 `U+D800–U+DFFF` 内。
    这样的位（实测只有 bit57）语义是"本字体含 BMP 之外的码位"，不是"代理区里有字符"。
    """
    ranges = unicode_range_block_ranges(bit)
    if not ranges:
        return False
    return all(SURROGATE_LO <= lo and hi <= SURROGATE_HI for lo, hi in ranges)


def _bit_satisfied(bit, codepoints):
    """该位是否被 `C` 满足：普通位按区间比对，行为型位按"存在非 BMP 码位"判（§六.9.3）。"""
    if is_behavioral_bit(bit):
        return any(cp > 0xFFFF for cp in codepoints)
    ranges = unicode_range_block_ranges(bit)
    return bool(ranges) and _hits_any(codepoints, ranges)


def _hits_any(codepoints, ranges):
    for lo, hi in ranges:
        for cp in codepoints:
            if lo <= cp <= hi:
                return True
    return False


# ── 9.1 name 存活 ───────────────────────────────────────────────────────────
def _name_state(subset_ids, source_ids):
    """``(present, missing, classes)`` —— 分类需要**两侧**的 ID 集合（§六.9.1）。"""
    present = [nid for nid in REQUIRED_NAME_IDS if subset_ids.get(nid)]
    missing = [nid for nid in REQUIRED_NAME_IDS if not subset_ids.get(nid)]
    classes = dict((key, []) for key in CLASSES)
    for nid in missing:
        if source_ids is None:
            classes[CLASS_UNCLASSIFIED].append(nid)
        elif source_ids.get(nid):
            classes[CLASS_DEFAULT_STRIPPED].append(nid)
        else:
            classes[CLASS_AUTHOR_ABSENT].append(nid)
    return present, missing, classes


def _name_findings(classes):
    """只有「默认剥离」产 finding；`author_absent`（原作者没写）与 `unclassified`（无源）都不产。"""
    out = []
    for nid in classes[CLASS_DEFAULT_STRIPPED]:
        code, spec_ref = NAME_CODES[nid]
        out.append(finding(
            MODULE, code, "warn", "nameID%d" % nid,
            "原字体有 nameID %d，产物里没有（默认 name_IDs 白名单把它剥掉了）" % nid,
            evidence={
                "nameID": nid,
                "source_present": True,
                "subset_present": False,
                "classification": CLASS_DEFAULT_STRIPPED,
            },
            spec_ref=spec_ref,
        ))
    return out


# ── 9.2 码页 ↔ cmap ────────────────────────────────────────────────────────
def _codepage_findings(os2, codepoints):
    """**只判 bit0**（§六.9.2）：声称 Latin-1 而 `C ∩ [U+0000, U+00FF] = ∅`。"""
    bits = os2_bits(os2)[1]
    if 0 not in bits:
        return []
    if any(cp <= LATIN1_HI for cp in codepoints):
        return []
    return [finding(
        MODULE, CODE_CODEPAGE_LATIN1, "error", "cp1:latin1",
        "ulCodePageRange1 bit0 声明支持 Latin-1，但 cmap 里没有任何 U+0000–U+00FF 码位"
        "（fontTools 的 recalcCodePageRanges 在无码页可用时回退置 bit0）",
        evidence={
            "ulCodePageRange1": "0x%08X" % os2["ulCodePageRange"][0],
            "claims_latin1": True,
            "latin1_codepoints": 0,
            "codepoints_total": len(codepoints),
        },
        spec_ref=CODEPAGE_LATIN1_SPEC_REF,
    )]


def _codepage_probe_ranges(bit):
    """**只用于 summary 的"命中数"展示**，不参与任何判定（§六.9.2 只判 bit0）。

    这不是第二套判定口径：没有任何 finding 读它。给读者一个量级参照而已。
    """
    if bit == 0:
        return [(0x0000, LATIN1_HI)]
    return _CODEPAGE_PROBE_RANGES.get(bit)


#: 码页位的字集**近似**区间（仅供 summary 展示；判定一律走 9.2 的 bit0 规则）。
_CODEPAGE_PROBE_RANGES = {
    1: [(0x0100, 0x017F)],
    2: [(0x0400, 0x04FF)],
    3: [(0x0370, 0x03FF)],
    4: [(0x011E, 0x0131)],
    5: [(0x0590, 0x05FF)],
    6: [(0x0600, 0x06FF)],
    7: [(0x0156, 0x017F)],
    8: [(0x1EA0, 0x1EF9)],
    16: [(0x0E00, 0x0E7F)],
    17: [(0x3040, 0x30FF), (0x31F0, 0x31FF)],
    18: [(0x4E00, 0x9FFF)],
    19: [(0xAC00, 0xD7A3)],
    20: [(0x4E00, 0x9FFF)],
    21: [(0xAC00, 0xD7A3)],
    29: [(0x0000, 0x00FF)],
    30: [(0x0000, 0x00FF)],
}


def _codepage_summary(os2, codepoints):
    """把**全部**置位列出来（含未判定的位）：读者看得到事实，工具只对可证的位下结论。"""
    rows = []
    for bit in sorted(os2_bits(os2)[1]):
        ranges = _codepage_probe_ranges(bit)
        hits = sum(1 for cp in codepoints if any(lo <= cp <= hi for lo, hi in ranges)) if ranges else 0
        rows.append({
            "bit": bit,
            "judged": bit == 0,
            "hits": hits,
            "ranges_known": ranges is not None,
        })
    return {
        "ulCodePageRange1": "0x%08X" % os2["ulCodePageRange"][0],
        "ulCodePageRange2": "0x%08X" % os2["ulCodePageRange"][1],
        "bits": sorted(os2_bits(os2)[1]),
        "judged_bits": [0],
        "detail": rows,
    }


# ── 9.3 ulUnicodeRange（只判过度声明） ─────────────────────────────────────
def _unicode_range_findings(os2, codepoints):
    bits = os2_bits(os2)[0]
    unknown = []
    out = []
    for bit in sorted(bits):
        ranges = unicode_range_block_ranges(bit)
        if ranges is None:
            unknown.append(bit)
            continue
        if _bit_satisfied(bit, codepoints):
            continue
        out.append(finding(
            MODULE, CODE_UNICODE_OVER, "warn", "ur:bit%d" % bit,
            "ulUnicodeRange 第 %d 位置位，但 cmap 在该位声明的 %s 里没有任何码位" % (
                bit, "非 BMP 码位" if is_behavioral_bit(bit) else "Unicode 块"),
            evidence={
                "bit": bit,
                "declared": True,
                "covered_codepoints": 0,
                "behavioral": is_behavioral_bit(bit),
                "blocks": unicode_range_block_names(bit),
            },
            spec_ref=UNICODE_RANGE_SPEC_REF,
        ))
    return out, unknown


def _unicode_range_summary(os2, codepoints):
    """`declared` / `over_declared` / `under_declared` 三个量都报（**只判过度**）。"""
    bits = os2_bits(os2)[0]
    over = []
    for bit in sorted(bits):
        if unicode_range_block_ranges(bit) is None:
            continue
        if not _bit_satisfied(bit, codepoints):
            over.append(bit)

    covered = set()
    from fontTools.ttLib.tables import O_S_2f_2 as os2_module

    for bit in range(len(os2_module.OS2_UNICODE_RANGES)):
        if _bit_satisfied(bit, codepoints):
            covered.add(bit)
    return {
        "declared": sorted(bits),
        "over_declared": over,
        # §六.9.3：欠声明**不判**（位是可选自我声明；实测欠声明率 91–254/559）
        "under_declared": sorted(covered - bits),
        "declared_empty": not bits,
    }


# ── 9.4 maxp / 9.5 首末码位 ────────────────────────────────────────────────
def _maxp_findings(font, declared):
    """§六.9.4：`maxp.numGlyphs` vs **独立量**（`loca` / CFF `CharStrings`）。"""
    measured = sfnt.measured_glyph_count(font)
    if measured is None:
        return [], None
    if declared is None or int(declared) == measured:
        return [], measured
    return [finding(
        MODULE, CODE_MAXP_MISMATCH, "error", "maxp",
        "maxp.numGlyphs = %d，但轮廓表的独立字形计数 = %d" % (declared, measured),
        evidence={
            "numGlyphs": int(declared),
            "measured": int(measured),
            "glyph_order": len(font.getGlyphOrder()) if hasattr(font, "getGlyphOrder") else None,
        },
        spec_ref=MAXP_SPEC_REF,
    )], measured


def _char_index_findings(os2, codepoints):
    """§六.9.5：只判"**没覆盖住**"方向；`0xFFFF` 是哨兵（该方向不判）。"""
    bmp = [cp for cp in codepoints if cp <= BMP_LIMIT]
    if not bmp:
        return [], False
    lo, hi = min(bmp), max(bmp)
    first = int(os2["usFirstCharIndex"])
    last = int(os2["usLastCharIndex"])
    out = []
    if first != SENTINEL_FFFF and lo < first:
        out.append(finding(
            MODULE, CODE_CHAR_INDEX, "warn", "usFirstCharIndex",
            "usFirstCharIndex = 0x%04X，但 cmap 里存在更低的 BMP 码位 U+%04X" % (first, lo),
            evidence={"field": "usFirstCharIndex", "declared": "0x%04X" % first,
                      "measured_min": "U+%04X" % lo},
            spec_ref=CHAR_INDEX_SPEC_REF,
        ))
    if last != SENTINEL_FFFF and hi > last:
        out.append(finding(
            MODULE, CODE_CHAR_INDEX, "warn", "usLastCharIndex",
            "usLastCharIndex = 0x%04X，但 cmap 里存在更高的 BMP 码位 U+%04X" % (last, hi),
            evidence={"field": "usLastCharIndex", "declared": "0x%04X" % last,
                      "measured_max": "U+%04X" % hi},
            spec_ref=CHAR_INDEX_SPEC_REF,
        ))
    if first != SENTINEL_FFFF and last != SENTINEL_FFFF and first > last:
        out.append(finding(
            MODULE, CODE_CHAR_INDEX, "warn", "usFirstCharIndex",
            "usFirstCharIndex = 0x%04X 大于 usLastCharIndex = 0x%04X（区间为空）" % (first, last),
            evidence={"field": "usFirstCharIndex", "declared": "0x%04X" % first,
                      "usLastCharIndex": "0x%04X" % last},
            spec_ref=CHAR_INDEX_SPEC_REF,
        ))
    return out, True


def _char_index_summary(os2, codepoints, judged):
    bmp = [cp for cp in codepoints if cp <= BMP_LIMIT]
    return {
        "usFirstCharIndex": "0x%04X" % int(os2["usFirstCharIndex"]),
        "usLastCharIndex": "0x%04X" % int(os2["usLastCharIndex"]),
        "measured_min": ("U+%04X" % min(bmp)) if bmp else None,
        "measured_max": ("U+%04X" % max(bmp)) if bmp else None,
        "judged": bool(judged),
    }


# ── 主流程 ──────────────────────────────────────────────────────────────────
def _skip(reason, detail):
    """任一条失败路径 → 一条 SKIPPED + 空 summary（§六.9.6：不猜、不给半份结论）。"""
    return ([], [skipped(MODULE, reason, "subset: " + detail + "（metadata §6.9）")], {})


def evaluate(subset_path, source_path=None):
    """元数据与位域一致性：返回 ``(findings, skips, summary)``（接口与 M0 骨架一致）。"""
    validate_inputs([subset_path, source_path])  # 不可读 / 非 sfnt → InputError → 退出码 2

    subset_font = sfnt.open_font(subset_path)
    try:
        os2 = sfnt.os2_info(subset_font)
        if os2 is None:
            return _skip(REASON_NO_OS2, "该字体没有 OS/2 表，位域一致性无从判定")
        if "name" not in subset_font:
            return _skip(REASON_NO_NAME, "该字体没有 name 表，name 存活无从判定")
        if "cmap" not in subset_font:
            return _skip(REASON_NO_CMAP_TABLE, "该字体没有 cmap 表，位域 ↔ 覆盖无从比对")
        codepoints = sfnt.cmap_codepoints(subset_font)
        if not codepoints:
            return _skip(REASON_NO_UNICODE_CMAP, "该字体没有 Unicode cmap 覆盖，位域 ↔ 覆盖无从比对")

        subset_ids = sfnt.name_ids(subset_font)
        subset_langs = sfnt.name_language_ids(subset_font)

        source_ids = None
        source_langs = []
        if source_path is not None:
            source_font = sfnt.open_font(source_path)
            try:
                if "name" in source_font:
                    source_ids = sfnt.name_ids(source_font)
                    source_langs = sfnt.name_language_ids(source_font)
            finally:
                sfnt.close_font(source_font)

        return _judge(subset_font, os2, codepoints, subset_ids, subset_langs,
                      source_ids, source_langs)
    finally:
        sfnt.close_font(subset_font)


def _judge(font, os2, codepoints, subset_ids, subset_langs, source_ids, source_langs):
    findings = []
    skips = []

    present, missing, classes = _name_state(subset_ids, source_ids)
    findings.extend(_name_findings(classes))

    findings.extend(_codepage_findings(os2, codepoints))
    ur_findings, ur_unknown = _unicode_range_findings(os2, codepoints)
    findings.extend(ur_findings)

    declared_glyphs = sfnt.maxp_num_glyphs(font)
    maxp_findings, measured_glyphs = _maxp_findings(font, declared_glyphs)
    findings.extend(maxp_findings)
    if measured_glyphs is None:
        skips.append(skipped(MODULE, REASON_NO_OUTLINE,
                             "subset: 既无 glyf/loca 也无 CFF，maxp 无独立量可比（其余判定照常）"))

    char_findings, char_judged = _char_index_findings(os2, codepoints)
    findings.extend(char_findings)

    summary = {
        "metadata": {
            "spec_ref": SPEC_REF,
            "name": {
                "present": present,
                "missing": missing,
                "required_ids": list(REQUIRED_NAME_IDS),
                "classification": dict((key, sorted(value)) for key, value in classes.items()),
                "classification_source": ("source" if source_ids is not None else "none"),
                "source_present": source_ids is not None,
                "languages": {"subset": subset_langs, "source": source_langs},
                "language_count": {"subset": len(subset_langs), "source": len(source_langs)},
            },
            "codepage": _codepage_summary(os2, codepoints),
            "unicode_range": _unicode_range_summary(os2, codepoints),
            "unicode_range_unknown_bits": ur_unknown,
            "maxp": {
                "numGlyphs": declared_glyphs,
                "measured": measured_glyphs,
                "match": (None if measured_glyphs is None
                          else declared_glyphs == measured_glyphs),
            },
            "char_index": _char_index_summary(os2, codepoints, char_judged),
            "codepoints_total": len(codepoints),
        }
    }
    return (findings, skips, summary)
