# -*- coding: utf-8 -*-
"""字符集运算：三分类、glyph0 剔除、分区计数、组合字符闭包、回退链建议。

口径单点在 ``data/README.md`` §六.2 / §六.3 / §六.4 —— 本文件只实现，不另立口径。
"""
from __future__ import print_function

import unicodedata

# .notdef 在 fontTools 的 cmap 里通常映射到 ".notdef" 或不出现；把两种都当缺。
NOTDEF_NAMES = frozenset([".notdef", "glyph00000", ""])

BMP_MAX = 0xFFFF
EXTA_LO, EXTA_HI = 0x3400, 0x4DBF
EXTB_LO, EXTB_HI = 0x20000, 0x2FA1F


def codepoints(selected):
    """从 ``{cp: glyphName}`` 取**真实覆盖**码位：映射到 .notdef 的视为缺（§六.2）。"""
    if not selected:
        return set()
    out = set()
    for cp, glyph in selected.items():
        name = (glyph or "").strip()
        if name in NOTDEF_NAMES:
            continue
        out.add(int(cp))
    return out


def classify(required, source, subset):
    """三分类（§六.2）：``MISSING_IN_SOURCE`` / ``LOST_IN_SUBSET`` / ``OK``，均码位升序。"""
    required = set(required)
    source = set(source)
    subset = set(subset) if subset is not None else None

    missing = required - source
    if subset is None:
        lost = set()
        ok = required & source
    else:
        lost = (required & source) - subset
        ok = required & source & subset
    return {
        "OK": sorted(ok),
        "MISSING_IN_SOURCE": sorted(missing),
        "LOST_IN_SUBSET": sorted(lost),
    }


def block_of(cp):
    if cp <= BMP_MAX:
        return "BMP"
    if EXTA_LO <= cp <= EXTA_HI:
        return "ExtA"
    if EXTB_LO <= cp <= EXTB_HI:
        return "ExtB+"
    return "other"


def block_counts(cps):
    """分块计数（§六.4）：BMP / ExtA / ExtB+ / other。"""
    counts = {"BMP": 0, "ExtA": 0, "ExtB+": 0, "other": 0}
    for cp in sorted(set(cps)):
        counts[block_of(cp)] += 1
    return counts


def closure(cps):
    """组合字符闭包：对每个码位取 NFD 分解与 NFC 合成，返回 ``(closed, added)``。

    ``added`` 只含闭包**新引入**的码位（码位升序），用于报告"闭包内缺失"。
    """
    base = set(int(c) for c in cps)
    closed = set(base)
    for cp in sorted(base):
        ch = chr(cp)
        for form in ("NFD", "NFC"):
            try:
                mapped = unicodedata.normalize(form, ch)
            except (ValueError, TypeError):
                continue
            for out_ch in mapped:
                closed.add(ord(out_ch))
    return closed, sorted(closed - base)


def from_text(text):
    """文本 → 码位集合（去掉换行/制表等控制字符，避免把 CRLF 当需求）。"""
    drop = {0x0A, 0x0D, 0x09}
    return set(ord(ch) for ch in text if ord(ch) not in drop)


def from_corpus_file(path):
    # 只读、按 UTF-8（BOM 容忍）；错误由调用方转 InputError。
    with open(path, "r", encoding="utf-8-sig") as fh:
        return from_text(fh.read())


def fallback_hint(lost, subset_cps):
    """回退链建议（§六.2 的延伸）：对被丢码位给出"子集可提供的最近似集合"。

    规则（确定性、无启发式）：按 ``block_of`` 归组，报告子集在该块里的可提供数量；
    若子集在该块内 0 个，则给出子集覆盖最多的块名。仅作**建议**，不改变三分类判定。
    """
    lost = sorted(set(lost))
    subset_cps = set(subset_cps or ())
    if not lost:
        return []
    hints = []
    blocks = sorted(set(block_of(cp) for cp in lost))
    for block in blocks:
        avail = sum(1 for cp in subset_cps if block_of(cp) == block)
        hints.append({"block": block, "lost": sum(1 for cp in lost if block_of(cp) == block),
                      "subset_available_in_block": avail})
    return hints


def format_codepoints(cps, limit=32):
    """稳定的人类可读形态：``U+5B57, U+6C49``；超限则截断并标注总数。"""
    cps = list(cps)
    shown = ", ".join("U+%04X" % cp for cp in cps[:limit])
    if len(cps) > limit:
        shown += " …（共 %d 个）" % len(cps)
    return shown
