# -*- coding: utf-8 -*-
"""测试公共夹具：程序合成的极小字体（**不依赖任何商用字体，也不入库**）。

合成字体只在临时目录里存在（pytest 的 ``tmp_path``），符合 `plan/04` 的数据纪律。
"""
from __future__ import print_function

import os
import sys

# src 布局：让"刚 clone / 未安装"的树也能直接 `py -m pytest`。
# 放在 conftest 顶部（pytest 在收集前加载它），比要求调用方设 PYTHONPATH 更省事；
# 注意这条只影响**测试进程**，不改变包本身的导入形态。
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

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


# ── 布局样本（M4）：测试内合成，**不依赖任何商用字体**（data/README §四.1 #14） ──
LAYOUT_GLYPH_ORDER = (
    ".notdef", "f", "i", "uniFB01", "a", "b", "a.alt", "zero.slash", "one",
)
LAYOUT_CMAP = {0x66: "f", 0x69: "i", 0x61: "a", 0x62: "b", 0x30: "zero.slash", 0x31: "one"}
LAYOUT_FEA = u"""
feature liga { sub f i by uniFB01; } liga;
feature ss01 { sub a by a.alt; } ss01;
feature zero { sub zero.slash by one; } zero;
"""


def build_layout_font(path, wrap_gsub_ext=(), wrap_gpos_ext=False):
    """合成带 GSUB（liga/ss01/zero）的极小 TTF；可选把指定 feature 的 lookup 包成 Extension。

    ``wrap_gsub_ext`` = 需要包成 GSUB **Type 7** 的 feature 标签（如 ``("liga", "ss01")``）；
    ``wrap_gpos_ext`` = 是否把 ``kern`` 的 GPOS lookup 包成 **Type 9**。

    这两个参数是 M4 的对照锚点（`data/README.md` §六.5.2 / §四.1 #13–#14）：
      · 包了 Type 7/9 之后，**朴素遍历看到 0 条**、解包后看到真子表；
      · 不包时两者相等 —— 用来证明"解包这一层是承重的"，而不是恒等变换。
    """
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    from fontTools.ttLib.tables import otTables as OT

    glyph_order = list(LAYOUT_GLYPH_ORDER)
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(dict(LAYOUT_CMAP))
    fb.setupGlyf(dict((name, _glyph(None)) for name in glyph_order))
    fb.setupHorizontalMetrics(dict((name, (600, 0)) for name in glyph_order))
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({
        "familyName": "SubsetAuditLayoutFixture",
        "styleName": "Regular",
        "copyright": "Synthetic fixture",
        "licenseDescription": "Synthetic OFL-like fixture",
        "licenseInfoURL": "https://example.invalid/license",
    })
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    addOpenTypeFeaturesFromString(fb.font, LAYOUT_FEA + u"\nfeature kern { pos f i -10; } kern;\n")
    font = fb.font

    _wrap_extension(font, "GSUB", wrap_gsub_ext, OT.ExtensionSubst)
    if wrap_gpos_ext:
        _wrap_extension(font, "GPOS", ("kern",), OT.ExtensionPos)

    font.save(path)
    font.close()
    return path


def _wrap_extension(font, tag, feature_tags, extension_class):
    """把指定 feature 引用的 lookup 就地包成 Extension（GSUB Type 7 / GPOS Type 9）。"""
    table = font[tag].table
    targets = set()
    for record in table.FeatureList.FeatureRecord:
        if record.FeatureTag in feature_tags:
            targets.update(int(i) for i in (record.Feature.LookupListIndex or []))
    for index in sorted(targets):
        lookup = table.LookupList.Lookup[index]
        if int(lookup.LookupType) in (7, 9):
            continue  # 已经是 Extension，不重复包
        inner = lookup.SubTable[0]
        extension = extension_class()
        extension.Format = 1
        extension.ExtensionLookupType = int(lookup.LookupType)
        extension.ExtSubTable = inner
        lookup.LookupType = 7 if tag == "GSUB" else 9
        lookup.SubTable = [extension]


def subset_layout_font(src, dst, unicodes, layout_features=None):
    """用 ``fontTools.subset`` 产出子集（与 `pyftsubset` 默认行为对齐）。"""
    from fontTools import subset
    from fontTools.ttLib import TTFont

    options = subset.Options()
    if layout_features is not None:
        options.layout_features = list(layout_features)
    font = TTFont(src, recalcTimestamp=False)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=sorted(unicodes))
    subsetter.subset(font)
    font.save(dst)
    font.close()
    return dst


@pytest.fixture()
def layout_font(tmp_path):
    """GSUB 无 Extension：liga/ss01/zero 三条 feature，`naive == raw`。"""
    return build_layout_font(str(tmp_path / "layout-plain.ttf"))


@pytest.fixture()
def layout_font_ext(tmp_path):
    """GSUB 的 liga/ss01 包成 **Type 7**，GPOS 的 kern 包成 **Type 9**。"""
    return build_layout_font(str(tmp_path / "layout-ext.ttf"),
                             wrap_gsub_ext=("liga", "ss01"), wrap_gpos_ext=True)


@pytest.fixture()
def no_layout_font(tmp_path):
    """完全没有 GSUB/GPOS（走 `SKIPPED(reason=no_layout_tables)`）。"""
    path = str(tmp_path / "no-layout.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"})
    return path


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