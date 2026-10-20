# -*- coding: utf-8 -*-
"""测试公共夹具：程序合成的极小字体（**不依赖任何商用字体，也不入库**）。

合成字体只在临时目录里存在（pytest 的 ``tmp_path``），符合 `plan/04` 的数据纪律。
"""
from __future__ import print_function

import os

import pytest

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from subsetaudit import cmapset, sfnt


def _glyph(pen_factory, size=20):
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((size, 0))
    pen.lineTo((size, size))
    pen.closePath()
    return pen.glyph()


def build_font(path, cmap=None, fs_type=0x0000, version=0, name_records=None,
               include_os2=True, code_page_range=(0, 0), unicode_range=None,
               mac_only=False):
    """合成一个最小 TTF 并保存到 ``path``（测试专用，落临时目录）。"""
    cmap = dict(cmap or {0x61: "a"})
    # 字形顺序必须去重（把某个码位映射到 .notdef 时集合里会出现两次 → fontTools 编译期断言失败）
    glyph_order = [".notdef"] + sorted(set(g for g in cmap.values() if g != ".notdef"))
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    glyphs = {".notdef": _glyph(None, 10)}
    for name in glyph_order[1:]:
        glyphs[name] = _glyph(None)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(dict((n, (600, 0)) for n in glyph_order))
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable(name_records or {
        "familyName": "SubsetAuditFixture",
        "styleName": "Regular",
        "copyright": "Synthetic fixture",
        "licenseDescription": "Synthetic OFL-like fixture",
        "licenseInfoURL": "https://example.invalid/license",
    })
    if include_os2:
        fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
        os2 = fb.font["OS/2"]
        os2.fsType = fs_type
        os2.version = version
        os2.ulCodePageRange1, os2.ulCodePageRange2 = code_page_range
        if unicode_range is not None:
            (os2.ulUnicodeRange1, os2.ulUnicodeRange2,
             os2.ulUnicodeRange3, os2.ulUnicodeRange4) = unicode_range
    fb.setupPost()
    if mac_only:
        _make_mac_only(fb.font)
    fb.save(path)
    return path


def _make_mac_only(font):
    """把 cmap 换成**只有** Mac Roman (1,0) / format 0 的子表 —— 用于验证 no_unicode_cmap。

    为什么不用 `fb.font["cmap"].tables = [...]` 过滤：``setupCharacterMap`` 默认只建
    ``(3,1)``，过滤后得到的是**空表**（会被判成 ``no_cmap_table``，那是另一条 SKIPPED 理由）。
    这里显式构造一条 (1,0)/format 0 子表，才能测出"有 cmap 但没有 Unicode 映射"这一态。
    """
    from fontTools.ttLib.tables._c_m_a_p import cmap_format_0

    mac = cmap_format_0(0)
    mac.platformID, mac.platEncID, mac.language = 1, 0, 0
    best = font.getBestCmap()
    mac.cmap = dict((cp, name) for cp, name in best.items() if cp < 0x100)
    font["cmap"].tables = [mac]


@pytest.fixture()
def simple_font(tmp_path):
    """含 ``a b c`` 的最小字体。"""
    path = str(tmp_path / "simple.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b", 0x63: "c"})
    return path


@pytest.fixture()
def notdef_mapped_font(tmp_path):
    """把 U+0061 映射到 .notdef —— 用于验证『glyph0 命中不计覆盖』。"""
    path = str(tmp_path / "notdef.ttf")
    build_font(path, cmap={0x61: ".notdef", 0x62: "b"})
    return path


@pytest.fixture()
def corpus_file(tmp_path):
    path = tmp_path / "corpus.txt"
    path.write_text("汉字abc\n", encoding="utf-8")
    return str(path)


__all__ = ["build_font", "cmapset", "sfnt", "os"]