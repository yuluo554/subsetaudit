# -*- coding: utf-8 -*-
"""只读表访问层：唯一允许打开字体的地方。

纪律：
  · 不调用任何 ``save()``（生成 fixture 的写盘代码只在 ``tools/gen_fixtures.py``）；
  · 不缓存跨字体状态、不读时钟、不联网；
  · 打不开 / 不是 sfnt → ``canonical.InputError``（CLI 收口为退出码 2）。

编码优先级见 ``data/README.md`` §六.3：``(3,10) → (0,4) → (3,1) → (0,3)``。
"""
from __future__ import print_function

import os

from fontTools.ttLib import TTFont, TTLibError

from .canonical import InputError

# 优先级（§六.3）。同一优先级可能有多个子表 → 取并集。
UNICODE_CMAP_PRIORITY = ((3, 10), (0, 4), (3, 1), (0, 3))


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
