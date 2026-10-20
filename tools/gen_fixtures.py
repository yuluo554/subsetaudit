#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""F1–F6 合成破损 fixture 生成器（M1 数据先行）。

设计口径只引 ``plan/04`` §2（fixture 表）与 ``data/README.md`` §六（数值口径），本文件不另立。

三条硬纪律（``plan/04`` §2「生成纪律」）：
  · **禁时钟**：``head.created/modified`` 固定为常量 ``FIXED_EPOCH``，两次生成逐字节一致；
  · **禁随机 / 禁 set 迭代序**：一切顺序来自 ``sorted()`` 或显式字面量；
  · **产物不入仓**：写进 ``data/fixtures/<name>/out/``（``.gitignore`` 已阻断），
    ``expect.json`` / ``README.md`` / 脚本入仓。

每个 fixture 生成后立刻跑一遍**独立 oracle**（``oracle_*``：纯位运算 + 独立 cmap 位解析，
不调 fontTools 的高层 API 复算同一件事），不符即以退出码 1 失败并点名。

用法::

    py tools/gen_fixtures.py                # 全量生成 F1–F6（写 manifest.json）
    py tools/gen_fixtures.py --only F1,F3   # 部分生成（**不写 manifest.json**）
    py tools/gen_fixtures.py --check        # 重生成到临时目录 → 与产物逐字节比对
    py tools/gen_fixtures.py --out DIR      # 换输出根目录（--check 内部用它做临时目录）

退出码：0 全部成功 / 1 生成或自证失败 / 2 用法错误。
"""
from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "fixtures")

# 固定时间戳：fontTools 的 ``head.created/modified`` 默认取当前时钟 → 必须钉死。
# 值 = 2000-01-01T00:00:00Z 的 sfnt 纪元秒（sfnt 纪元 = 1904-01-01，故加 96 年偏移）。
FIXED_EPOCH = 3155673600

# fixture 名表 = ``data/README.md`` §六.7（代码不得另立第二套名字）。
FIXTURES = [
    ("F1", "fstype-nosubset"),
    ("F2", "fstype-multibit-v0"),
    ("F3", "fstype-multibit-v3"),
    ("F4", "silent-drop"),
    ("F5", "metadata-stripped"),
    ("F6", "codepage-mismatch"),
]
FIXTURE_NAMES = dict(FIXTURES)


# ── 基础：确定性合成 ────────────────────────────────────────────────────────
def _glyph(size):
    """固定的方框字形（无 hinting、无曲线）—— 只要合法且确定。"""
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((size, 0))
    pen.lineTo((size, size))
    pen.closePath()
    return pen.glyph()


def build_font(path, cmap, fs_type=0x0000, os2_version=4, name_records=None,
               code_page_range=(0, 0), unicode_range=None, upem=1000,
               extra_names=()):
    """合成一个极小 TTF 并保存。

    ``cmap`` 必须是 ``{codepoint: glyphName}``，且键序 / 值集合由调用方给定字面量
    （本函数再 ``sorted`` 一次，杜绝调用侧顺序泄漏）。

    ``extra_names`` = ``[(nameID, langID, value)]``，用于构造**多语言** name 表
    （F5 需要"源字体多语言、产物单一语言"这一对照）。记录按给定元组**原样**写入，
    不再排序 —— 顺序由调用方字面量决定，确定性不依赖 set。
    """
    from fontTools.fontBuilder import FontBuilder

    cmap = dict(cmap)
    glyph_order = [".notdef"] + sorted(set(g for g in cmap.values() if g != ".notdef"))
    fb = FontBuilder(upem, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    glyphs = {".notdef": _glyph(10)}
    for name in glyph_order[1:]:
        glyphs[name] = _glyph(20)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(dict((n, (600, 0)) for n in glyph_order))
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable(name_records or DEFAULT_NAMES)
    if extra_names:
        table = fb.font["name"]
        for name_id, lang_id, value in extra_names:
            table.setName(value, name_id, 3, 1, lang_id)
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    os2 = fb.font["OS/2"]
    os2.fsType = int(fs_type)
    os2.version = int(os2_version)
    os2.ulCodePageRange1, os2.ulCodePageRange2 = [int(v) for v in code_page_range]
    if unicode_range is not None:
        (os2.ulUnicodeRange1, os2.ulUnicodeRange2,
         os2.ulUnicodeRange3, os2.ulUnicodeRange4) = [int(v) for v in unicode_range]
    fb.setupPost()

    head = fb.font["head"]
    head.created = FIXED_EPOCH
    head.modified = FIXED_EPOCH
    fb.save(path)
    return path


# 默认 name 表：含 13/14（许可元数据），用于"源字体"侧。
DEFAULT_NAMES = {
    "familyName": "SubsetAuditFixture",
    "styleName": "Regular",
    "uniqueFontIdentifier": "SubsetAuditFixture-Regular-1.0",
    "fullName": "SubsetAuditFixture Regular",
    "psName": "SubsetAuditFixture-Regular",
    "version": "Version 1.000",
    "copyright": "Synthetic fixture; not a real font.",
    "licenseDescription": "Synthetic OFL-1.1-like fixture used for audit tests.",
    "licenseInfoURL": "https://example.invalid/ofl-1-1",
}


# ── 独立 oracle（不复用 fontTools 高层语义） ─────────────────────────────────
def _read_sfnt_table(path, tag):
    """**独立**读 sfnt 目录，返回指定表的原始字节；不经过 fontTools。"""
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < 12:
        raise AssertionError("不是 sfnt：文件太短 %r" % (path,))
    tag = tag.encode("ascii")[:4].ljust(4, b" ")
    num_tables = struct.unpack(">H", data[4:6])[0]
    for i in range(num_tables):
        off = 12 + i * 16
        if off + 16 > len(data):
            raise AssertionError("sfnt 目录越界：%r" % (path,))
        entry_tag = data[off:off + 4]
        if entry_tag != tag:
            continue
        _checksum, offset, length = struct.unpack(">III", data[off + 4:off + 16])
        return data[offset:offset + length]
    raise AssertionError("表 %s 不存在：%r" % (tag.decode("ascii").strip(), path))


def oracle_os2(path):
    """独立解析 OS/2：version / fsType / ulUnicodeRange[4] / ulCodePageRange[2]。

    OS/2 布局（MS 规范）：version@0 (u16)、xAvgCharWidth@2、usWeightClass@4、
    usWidthClass@6、fsType@8 (u16)、…、ulUnicodeRange1@42..45、ulCodePageRange1@78。
    **只取本工具需要的字段**，偏移照规范写死（v0 起字段位置不变）。
    """
    raw = _read_sfnt_table(path, "OS/2")
    if len(raw) < 68:
        raise AssertionError("OS/2 太短: %d B" % len(raw))
    version = struct.unpack(">H", raw[0:2])[0]
    fs_type = struct.unpack(">H", raw[8:10])[0]
    unicode_range = list(struct.unpack(">IIII", raw[42:58]))
    if len(raw) >= 86:
        code_page = list(struct.unpack(">II", raw[78:86]))
    else:
        code_page = [0, 0]
    return {
        "version": version,
        "fsType": fs_type,
        "ulUnicodeRange": unicode_range,
        "ulCodePageRange": code_page,
    }


def oracle_cmap(path):
    """独立解析 cmap：返回 ``(format, {(platform, encoding): {codepoint: gid}})``。

    只支持本生成器会产出的子表形态（format 4 / 12 / 0），够用即可；
    解析失败 → AssertionError（**不许**在 oracle 里静默降级）。
    """
    raw = _read_sfnt_table(path, "cmap")
    version, num_subtables = struct.unpack(">HH", raw[0:4])
    if version != 0:
        raise AssertionError("cmap version=%d（只认 0）" % version)
    out = {}
    for i in range(num_subtables):
        off = 4 + i * 8
        pid, eid, sub_off = struct.unpack(">HHI", raw[off:off + 8])
        fmt = struct.unpack(">H", raw[sub_off:sub_off + 2])[0]
        mapping = _parse_cmap_subtable(raw, sub_off, fmt)
        out[(pid, eid)] = mapping
    return out


def _parse_cmap_subtable(raw, off, fmt):
    mapping = {}
    if fmt == 0:
        for cp in range(256):
            gid = raw[off + 6 + cp]
            if gid:
                mapping[cp] = gid
        return mapping
    if fmt == 4:
        seg_x2 = struct.unpack(">H", raw[off + 6:off + 8])[0]
        seg = seg_x2 // 2
        ends = struct.unpack(">%dH" % seg, raw[off + 14:off + 14 + seg_x2])
        base = off + 14 + seg_x2 + 2  # 跳过 reservedPad
        starts = struct.unpack(">%dH" % seg, raw[base:base + seg_x2])
        deltas = struct.unpack(">%dh" % seg, raw[base + seg_x2:base + 2 * seg_x2])
        ro_base = base + 2 * seg_x2
        range_offsets = struct.unpack(">%dH" % seg, raw[ro_base:ro_base + seg_x2])
        for k in range(seg):
            start, end = starts[k], ends[k]
            if start == 0xFFFF and end == 0xFFFF:
                continue
            for cp in range(start, end + 1):
                if range_offsets[k] == 0:
                    gid = (cp + deltas[k]) & 0xFFFF
                else:
                    gid_off = ro_base + 2 * k + range_offsets[k] + 2 * (cp - start)
                    if gid_off + 2 > len(raw):
                        continue
                    gid = struct.unpack(">H", raw[gid_off:gid_off + 2])[0]
                    if gid:
                        gid = (gid + deltas[k]) & 0xFFFF
                if gid:
                    mapping[cp] = gid
        return mapping
    if fmt == 12:
        n_groups = struct.unpack(">I", raw[off + 12:off + 16])[0]
        for i in range(n_groups):
            g_off = off + 16 + i * 12
            start, end, start_gid = struct.unpack(">III", raw[g_off:g_off + 12])
            for cp in range(start, end + 1):
                mapping[cp] = start_gid + (cp - start)
        return mapping
    raise AssertionError("oracle 不支持的 cmap 子表格式: %d" % fmt)


def oracle_sfnt_cmap_mask(path):
    """独立取 "Unicode cmap 覆盖" 的位掩码 ``{codepoint}``（只看 pid==3/0 的子表并集）。"""
    subs = oracle_cmap(path)
    covered = set()
    for (pid, _eid), mapping in sorted(subs.items()):
        if pid in (0, 3):
            for cp, gid in mapping.items():
                if gid:  # gid 0 = .notdef → 不计覆盖（§六.2）
                    covered.add(cp)
    return covered


# ── 各 fixture 的构造与真值 ────────────────────────────────────────────────
def fixture_f1(out_dir):
    """F1 ``0x0108`` = bit3 Editable + bit8 No-subsetting → ``may_subset=false``。"""
    path = os.path.join(out_dir, "fstype-nosubset.ttf")
    build_font(path, {0x61: "a", 0x62: "b", 0x63: "c"},
               fs_type=0x0108, os2_version=4,
               code_page_range=(0x1, 0x0), unicode_range=(0x1, 0x0, 0x0, 0x0))
    return path, {
        "id": "F1",
        "name": "fstype-nosubset",
        "font": "fstype-nosubset.ttf",
        "input": {
            "synthetic": True,
            "cmap": {"0x0061": "a", "0x0062": "b", "0x0063": "c"},
            "fsType": "0x0108",
            "os2_version": 4,
        },
        "expect": {
            "os2_version": 4,
            "fsType": "0x0108",
            "permission_bits": "0x0008",
            "permission_name": "Editable",
            "permission_resolution": "direct",
            "may_subset": False,
            "embed_pdf": True,
            "embed_app": False,
            "embed_web": False,
            "may_modify": True,
            "bit8_no_subsetting": True,
            "bit9_bitmap_only": False,
            "reserved_bits_set": False,
            "mutual_exclusion_violation": False,
            "expected_findings": [
                {"code": "FSTYPE_NO_SUBSET", "severity": "error", "spec_ref": "MS-OS2 §fsType bit8"}
            ],
        },
    }


def fixture_f2(out_dir):
    """F2 ``0x000E`` + OS/2 **v0** → 取最宽松（Editable），**不得**报互斥违规（反例守护）。"""
    path = os.path.join(out_dir, "fstype-multibit-v0.ttf")
    build_font(path, {0x61: "a", 0x62: "b", 0x63: "c"},
               fs_type=0x000E, os2_version=0,
               code_page_range=(0x1, 0x0), unicode_range=(0x1, 0x0, 0x0, 0x0))
    return path, {
        "id": "F2",
        "name": "fstype-multibit-v0",
        "font": "fstype-multibit-v0.ttf",
        "input": {
            "synthetic": True,
            "cmap": {"0x0061": "a", "0x0062": "b", "0x0063": "c"},
            "fsType": "0x000E",
            "os2_version": 0,
        },
        "expect": {
            "os2_version": 0,
            "fsType": "0x000E",
            "permission_bits": "0x000E",
            "permission_name": "Editable",
            "permission_resolution": "least_restrictive",
            "may_subset": True,
            "embed_pdf": True,
            "embed_app": False,
            "embed_web": True,
            "may_modify": True,
            "bit8_no_subsetting": False,
            "bit9_bitmap_only": False,
            "reserved_bits_set": False,
            "mutual_exclusion_violation": False,
            "expected_findings": [],
            "counterexample_guard": "v0 的 bits0–3 多位并存必须解析为最宽松权限，不得误报互斥",
        },
    }


def fixture_f3(out_dir):
    """F3 ``0x000E`` + OS/2 **v3** → 互斥违规 ``error``；最宽松仍是 Editable（8）。"""
    path = os.path.join(out_dir, "fstype-multibit-v3.ttf")
    build_font(path, {0x61: "a", 0x62: "b", 0x63: "c"},
               fs_type=0x000E, os2_version=3,
               code_page_range=(0x1, 0x0), unicode_range=(0x1, 0x0, 0x0, 0x0))
    return path, {
        "id": "F3",
        "name": "fstype-multibit-v3",
        "font": "fstype-multibit-v3.ttf",
        "input": {
            "synthetic": True,
            "cmap": {"0x0061": "a", "0x0062": "b", "0x0063": "c"},
            "fsType": "0x000E",
            "os2_version": 3,
        },
        "expect": {
            "os2_version": 3,
            "fsType": "0x000E",
            "permission_bits": "0x000E",
            "permission_name": "Editable",
            "permission_resolution": "least_restrictive",
            "may_subset": True,
            "embed_pdf": True,
            "embed_app": False,
            "embed_web": True,
            "may_modify": True,
            "bit8_no_subsetting": False,
            "bit9_bitmap_only": False,
            "reserved_bits_set": False,
            "mutual_exclusion_violation": True,
            "expected_findings": [
                {"code": "FSTYPE_MUTUAL_EXCLUSION", "severity": "error",
                 "spec_ref": "MS-OS2 §fsType (v3+ mutually exclusive)"}
            ],
        },
    }


# F4/F5/F6 的"源字体"：同时含 CJK 与 Latin，外加 13/14 与多语言 name 记录。
F45_SOURCE_CMAP = {
    0x0061: "a", 0x0062: "b", 0x0063: "c",
    0x5B57: "uni5B57", 0x6C49: "uni6C49",
}
F45_SOURCE_NAMES = dict(DEFAULT_NAMES)
F45_SOURCE_NAMES.update({
    "licenseDescription": "Synthetic OFL-1.1-like fixture (license description).",
    "licenseInfoURL": "https://example.invalid/ofl-1-1",
})

# F5 专属：源字体带**第二语言**（日语 1041）的 name 记录 —— plan/04 §2 F5 要求
# 「源字体含 13/14 与多语言」。字面量元组，顺序固定（不走 set）。
F5_EXTRA_NAMES = (
    (1, 0x0411, u"SyntheticFixture-ja"),
    (2, 0x0411, u"Regular-ja"),
    (0, 0x0411, u"Synthetic fixture copyright (ja)"),
)


def _write_source(path, fs_type=0x0000, os2_version=4, code_page_range=(0x1, 0x0),
                  extra_names=()):
    build_font(path, F45_SOURCE_CMAP, fs_type=fs_type, os2_version=os2_version,
               name_records=F45_SOURCE_NAMES, code_page_range=code_page_range,
               unicode_range=(0x1, 0x8000000, 0x0, 0x0), extra_names=extra_names)
    return path


def _subset(src, dst, unicodes, options=None):
    """用 fontTools.subset 产出子集；``options`` 为 None 时用库默认（= 工具的默认行为）。

    确定性两个关键点（``plan/04`` §2 禁时钟）：
      · ``recalcTimestamp=False`` —— 否则 ``TTFont.save`` 会把 ``head.modified`` 改成当前时钟；
      · 落盘前把 ``head.created/modified`` 再钉一次（子集过程本身也会改写它们）。
    """
    from fontTools import subset
    from fontTools.ttLib import TTFont

    opts = options if options is not None else subset.Options()
    font = TTFont(src, recalcTimestamp=False)
    subsetter = subset.Subsetter(options=opts)
    subsetter.populate(unicodes=sorted(unicodes))
    subsetter.subset(font)
    head = font["head"]
    head.created = FIXED_EPOCH
    head.modified = FIXED_EPOCH
    font.save(dst)
    font.close()
    return dst


def fixture_f4(out_dir):
    """F4 静默丢字：源有 ``汉字abc``，只对 ``abc`` 子集 → 汉字进 ``LOST_IN_SUBSET``。

    真值由"合成本身"决定：源 cmap 含 {a,b,c,汉,字}，产物 cmap 只含 {a,b,c}；
    需求集 = {a,b,c,汉,字} → 丢失 = {汉, 字}，**不得**判 ``MISSING_IN_SOURCE``。
    """
    src = os.path.join(out_dir, "source.ttf")
    sub = os.path.join(out_dir, "subset.ttf")
    _write_source(src)
    _subset(src, sub, [0x61, 0x62, 0x63])
    return sub, {
        "id": "F4",
        "name": "silent-drop",
        "font": "subset.ttf",
        "input": {
            "synthetic": True,
            "source": "source.ttf",
            "subset": "subset.ttf",
            "source_cmap": {"0x0061": "a", "0x0062": "b", "0x0063": "c",
                            "0x5B57": "uni5B57", "0x6C49": "uni6C49"},
            "subset_unicodes": ["U+0061", "U+0062", "U+0063"],
            "required_text": u"汉字abc",
            "subset_options": {"ignore_missing_unicodes": True, "name_IDs": [0, 1, 2, 3, 4, 5, 6],
                               "name_languages": [1033]},
        },
        "expect": {
            "OK": ["U+0061", "U+0062", "U+0063"],
            "LOST_IN_SUBSET": ["U+5B57", "U+6C49"],
            "MISSING_IN_SOURCE": [],
            "expected_findings": [
                {"code": "LOST_IN_SUBSET", "severity": "error",
                 "primary_key": "U+5B57", "spec_ref": "data/README §6.2"},
                {"code": "LOST_IN_SUBSET", "severity": "error",
                 "primary_key": "U+6C49", "spec_ref": "data/README §6.2"},
            ],
            "counterexample_guard": "丢失的码位源字体确有覆盖 → 不得归入 MISSING_IN_SOURCE",
        },
    }


def fixture_f5(out_dir):
    """F5 元数据剥离：默认 ``name_IDs=[0..6]`` / ``name_languages=[1033]`` 的产物。

    源字体有 13/14 与多语言 name；产物只剩 0–6 与单一语言 → 缺 13/14 判"默认剥离"
    （有源可差分），语言记录数 = 1。
    """
    src = os.path.join(out_dir, "source.ttf")
    sub = os.path.join(out_dir, "subset.ttf")
    _write_source(src, extra_names=F5_EXTRA_NAMES)
    _subset(src, sub, [0x61, 0x62, 0x63])
    return sub, {
        "id": "F5",
        "name": "metadata-stripped",
        "font": "subset.ttf",
        "input": {
            "synthetic": True,
            "source": "source.ttf",
            "subset": "subset.ttf",
            "source_name_ids": [0, 1, 2, 3, 4, 5, 6, 13, 14],
            "source_name_languages": [0, 1033, 1041],
            "subset_options": {"name_IDs": [0, 1, 2, 3, 4, 5, 6], "name_languages": [1033]},
        },
        "expect": {
            "subset_name_ids": [0, 1, 2, 3, 4, 5, 6],
            "subset_name_languages": [1033],
            "missing_name_ids": [13, 14],
            "missing_classification": "default_stripped",
            "name_language_count": 1,
            "expected_findings": [
                {"code": "NAME_LICENSE_DESCRIPTION_STRIPPED", "severity": "warn",
                 "primary_key": "nameID13", "spec_ref": "MS-NAME nameID13"},
                {"code": "NAME_LICENSE_INFO_URL_STRIPPED", "severity": "warn",
                 "primary_key": "nameID14", "spec_ref": "MS-NAME nameID14"},
            ],
            "counterexample_guard": "只有拿到 --source 且原文确有 13/14 时，才可判『默认剥离』；"
                                    "原文也没有则判『原作者没写』",
        },
    }


def fixture_f6(out_dir):
    """F6 码页矛盾：仅 CJK 子集 → ``ulCodePageRange1`` 回退置 ``0x1``（Latin-1），
    而 cmap 无任何 Latin-1 字符。**不得**把 ``ulUnicodeRange1=0`` 报成矛盾。
    """
    src = os.path.join(out_dir, "source.ttf")
    sub = os.path.join(out_dir, "subset.ttf")
    _write_source(src, code_page_range=(0x4001F, 0x0))
    _subset(src, sub, [0x5B57, 0x6C49])
    return sub, {
        "id": "F6",
        "name": "codepage-mismatch",
        "font": "subset.ttf",
        "input": {
            "synthetic": True,
            "source": "source.ttf",
            "subset": "subset.ttf",
            "source_code_page_range": ["0x0004001F", "0x00000000"],
            "source_unicode_range": ["0x00000001", "0x08000000", "0x00000000", "0x00000000"],
            "subset_unicodes": ["U+5B57", "U+6C49"],
        },
        "expect": {
            "ulCodePageRange1": "0x00000001",
            "ulCodePageRange2": "0x00000000",
            "ulUnicodeRange1": "0x00000000",
            "ulUnicodeRange2_bit59_set": True,
            "cmap_has_latin1": False,
            "codepage_claims_latin1": True,
            "expected_findings": [
                {"code": "CODEPAGE_CLAIMS_LATIN1_WITHOUT_COVERAGE", "severity": "error",
                 "primary_key": "cp1:latin1", "spec_ref": "fontTools O_S_2f_2.recalcCodePageRanges"}
            ],
            "counterexample_guard": "ulUnicodeRange1=0 是正确重算（bit59 在 ulUnicodeRange2），"
                                    "不得报矛盾；真实矛盾点只在 ulCodePageRange1 的 Latin-1 回退",
            "expected_absent_findings": [
                {"code": "UNICODE_RANGE_CONTRADICTION", "primary_key": "ur1:zero"}
            ],
        },
    }


BUILDERS = {
    "F1": fixture_f1,
    "F2": fixture_f2,
    "F3": fixture_f3,
    "F4": fixture_f4,
    "F5": fixture_f5,
    "F6": fixture_f6,
}


# ── 生成期自证（独立 oracle 复算） ──────────────────────────────────────────
def _hex32(values):
    return ["0x%08X" % v for v in values]


# §六.1 的宽松序：8 最宽松、2 最严（0 = Installable 是"无限制"，单独成档）
PERMISSION_NAMES = {0: "Installable", 2: "Restricted", 4: "Preview & Print", 8: "Editable"}


def most_permissive(bits):
    """v0–v2 多位并存 → 取最宽松权限位（``data/README.md`` §六.1 的宽松序）。"""
    for candidate in (8, 4, 2):
        if bits & candidate:
            return candidate
    return 0


def _oracle_conclusions(fs_type, perm):
    """五元结论的**独立复算**（口径 = ``data/README.md`` §六.1.3）。

    刻意不复用 ``subsetaudit.license_gate.conclusions_for`` —— 生成期自证的价值就在于
    "用另一条代码路径把同一件事再算一遍"，复用被测实现等于没证。
    """
    bit8 = (fs_type & 0x0100) != 0
    bit9 = (fs_type & 0x0200) != 0
    return {
        "embed_pdf": (perm != 2) and not bit9,
        "embed_app": (perm == 0) and not bit9,
        "embed_web": (perm != 2) and not bit8 and not bit9,
        "may_subset": not bit8,
        "may_modify": perm in (0, 8),
    }


def self_check(fid, path, expect):
    """用独立 oracle 复算，任何不符 → AssertionError（携带 fixture 名）。

    口径来源：``data/README.md`` §六.1（fsType 位运算）与 §六.2（glyph0 不计覆盖）。
    """
    problems = []
    os2 = oracle_os2(path)
    fs_type = os2["fsType"]
    bits = fs_type & 0x000F
    bit_count = bin(bits).count("1")
    resolution = most_permissive(bits)

    if fid in ("F1", "F2", "F3"):
        exp = expect["expect"]
        if os2["version"] != exp["os2_version"]:
            problems.append("os2_version %d != %d" % (os2["version"], exp["os2_version"]))
        if fs_type != int(exp["fsType"], 16):
            problems.append("fsType 0x%04X != %s" % (fs_type, exp["fsType"]))
        if bits != int(exp["permission_bits"], 16):
            problems.append("permission_bits 0x%04X != %s" % (bits, exp["permission_bits"]))
        if "may_subset" in exp:
            may_subset = (fs_type & 0x0100) == 0
            if may_subset != exp["may_subset"]:
                problems.append("may_subset %s != %s" % (may_subset, exp["may_subset"]))
        if "mutual_exclusion_violation" in exp:
            violation = bit_count >= 2 and os2["version"] >= 3
            if violation != exp["mutual_exclusion_violation"]:
                problems.append("mutual_exclusion %s != %s"
                                % (violation, exp["mutual_exclusion_violation"]))
        if "reserved_bits_set" in exp:
            # §六.1：0xFCF1 = bit0 + bits4–7 + bits10–15
            reserved = (fs_type & 0xFCF1) != 0
            if reserved != exp["reserved_bits_set"]:
                problems.append("reserved_bits %s != %s" % (reserved, exp["reserved_bits_set"]))
        if "permission_resolution" in exp:
            # §六.1.2：bits1–3 单位置位或全 0 → `direct`；≥2 位并存 → `least_restrictive`
            expected_resolution = "least_restrictive" if bit_count >= 2 else "direct"
            if exp["permission_resolution"] != expected_resolution:
                problems.append("permission_resolution %s != 期望 %s"
                                % (exp["permission_resolution"], expected_resolution))
            # 解析出的**权限名**必须与期望一致；单权限位时解析值 = 原位值
            got_name = PERMISSION_NAMES.get(resolution, "unknown")
            if got_name != exp.get("permission_name"):
                problems.append("最宽松解析 %s(%s) != 期望 %s"
                                % (resolution, got_name, exp.get("permission_name")))
            if bit_count == 1 and resolution != bits:
                problems.append("单权限位时解析值应与原位值一致")
        if "bit8_no_subsetting" in exp:
            if ((fs_type & 0x0100) != 0) != exp["bit8_no_subsetting"]:
                problems.append("bit8 位与期望不符")
        if "bit9_bitmap_only" in exp:
            if ((fs_type & 0x0200) != 0) != exp["bit9_bitmap_only"]:
                problems.append("bit9 位与期望不符")
        # 五元结论的**独立复算**（口径 = data/README.md §六.1.3，与实现分开写一遍）
        for key, got in _oracle_conclusions(fs_type, resolution).items():
            if key in exp and got != exp[key]:
                problems.append("%s 复算 %s != 期望 %s" % (key, got, exp[key]))
        return problems

    if fid == "F4":
        covered = oracle_sfnt_cmap_mask(path)
        source = expect["input"]["source"]
        src_covered = oracle_sfnt_cmap_mask(os.path.join(os.path.dirname(path), source))
        required = set(int(k, 16) for k in expect["input"]["source_cmap"])
        # 源侧独立复算：需求集必须真的被源覆盖，否则 "MISSING_IN_SOURCE=[]" 就是假的
        not_in_source = sorted(required - src_covered)
        if not_in_source:
            problems.append("源字体并未覆盖需求集（构造失效）：%s" % _hex32(not_in_source))
        lost = sorted(required - covered)
        expect_lost = sorted(int(x[2:], 16) for x in expect["expect"]["LOST_IN_SUBSET"])
        if lost != expect_lost:
            problems.append("LOST_IN_SUBSET 复算 %s != 期望 %s"
                            % (_hex32(lost), _hex32(expect_lost)))
        ok = sorted(required & covered)
        expect_ok = sorted(int(x[2:], 16) for x in expect["expect"]["OK"])
        if ok != expect_ok:
            problems.append("OK 复算 %s != 期望 %s" % (_hex32(ok), _hex32(expect_ok)))
        return problems

    if fid == "F5":
        names = sorted(_oracle_name_ids(path))
        exp = expect["expect"]
        names, langs = _oracle_name_records(path)
        names = sorted(names)
        if names != sorted(exp["subset_name_ids"]):
            problems.append("nameID 集合 %s != 期望 %s" % (names, sorted(exp["subset_name_ids"])))
        # 语言对照：源多语言 → 产物被剥到单一语言（plan/04 §2 F5）
        if sorted(langs) != sorted(exp["subset_name_languages"]):
            problems.append("产物语言集合 %s != 期望 %s"
                            % (sorted(langs), sorted(exp["subset_name_languages"])))
        if len(langs) != exp["name_language_count"]:
            problems.append("语言记录数 %d != 期望 %d" % (len(langs), exp["name_language_count"]))
        # 源侧独立复算：只有源**确实**有 13/14 且多语言，"默认剥离"这个分类才成立
        source = expect["input"]["source"]
        src_names, src_langs = _oracle_name_records(os.path.join(os.path.dirname(path), source))
        src_names = sorted(src_names)
        exp_src = sorted(expect["input"]["source_name_ids"])
        if src_names != exp_src:
            problems.append("源 nameID 集合 %s != 期望 %s" % (src_names, exp_src))
        exp_src_langs = sorted(expect["input"]["source_name_languages"])
        if sorted(src_langs) != exp_src_langs:
            problems.append("源语言集合 %s != 期望 %s" % (sorted(src_langs), exp_src_langs))
        if len(src_langs) <= len(langs):
            problems.append("源语言数 %d 未多于产物 %d（'多语言被剥'这条期望不成立）"
                            % (len(src_langs), len(langs)))
        missing = sorted(set(src_names) - set(names))
        if missing != sorted(exp["missing_name_ids"]):
            problems.append("缺失 nameID %s != 期望 %s" % (missing, exp["missing_name_ids"]))
        return problems

    if fid == "F6":
        exp = expect["expect"]
        cp1 = os2["ulCodePageRange"][0]
        ur1, ur2 = os2["ulUnicodeRange"][0], os2["ulUnicodeRange"][1]
        if "0x%08X" % cp1 != exp["ulCodePageRange1"]:
            problems.append("ulCodePageRange1 0x%08X != %s" % (cp1, exp["ulCodePageRange1"]))
        if "0x%08X" % ur1 != exp["ulUnicodeRange1"]:
            problems.append("ulUnicodeRange1 0x%08X != %s" % (ur1, exp["ulUnicodeRange1"]))
        if bool(ur2 & (1 << 27)) != exp["ulUnicodeRange2_bit59_set"]:
            problems.append("ulUnicodeRange2 bit59 = %s != %s"
                            % (bool(ur2 & (1 << 27)), exp["ulUnicodeRange2_bit59_set"]))
        covered = oracle_sfnt_cmap_mask(path)
        has_latin1 = any(cp <= 0xFF for cp in covered)
        if has_latin1 != exp["cmap_has_latin1"]:
            problems.append("cmap_has_latin1 %s != %s" % (has_latin1, exp["cmap_has_latin1"]))
        claims_latin1 = (cp1 & 0x1) != 0
        if claims_latin1 != exp["codepage_claims_latin1"]:
            problems.append("codepage_claims_latin1 %s != %s"
                            % (claims_latin1, exp["codepage_claims_latin1"]))
        if claims_latin1 == has_latin1:
            problems.append("F6 构造失效：码页声明与 cmap 未形成矛盾")
        # 源侧独立复算：源必须真的声明了 CJK 之外的码页，否则"回退"这个说法无对照
        src_path = os.path.join(os.path.dirname(path), expect["input"]["source"])
        src_cp = oracle_os2(src_path)["ulCodePageRange"]
        got_src = _hex32(src_cp)
        if got_src != expect["input"]["source_code_page_range"]:
            problems.append("源 ulCodePageRange %s != 期望 %s"
                            % (got_src, expect["input"]["source_code_page_range"]))
        return problems

    problems.append("未知 fixture id: %s" % fid)
    return problems


def _oracle_name_records(path):
    """独立解析 name 表，返回 ``(nameID 集合, 语言 ID 集合)``（不走 fontTools 的 name 对象）。"""
    raw = _read_sfnt_table(path, "name")
    _fmt, count, _string_offset = struct.unpack(">HHH", raw[0:6])
    ids, langs = set(), set()
    for i in range(count):
        rec = 6 + i * 12
        if rec + 12 > len(raw):
            raise AssertionError("name 记录越界")
        _pid, _eid, lid, name_id, _length, _offset = struct.unpack(">HHHHHH", raw[rec:rec + 12])
        ids.add(name_id)
        langs.add(lid)
    return ids, langs


def _oracle_name_ids(path):
    return _oracle_name_records(path)[0]


# ── 写盘：expect.json / README.md / manifest.json ──────────────────────────
FIXTURE_README = u"""# {name}（{id}）

> 本目录由 `tools/gen_fixtures.py` 生成维护。**二进制产物不入仓**：
> `out/` 已被 `.gitignore` 阻断，入仓的只有本说明与 `expect.json`。

## 构造

{construction}

## 真值来源

{truth}

## 期望（`expect.json` 摘要）

```
{summary}
```

## 重生成

```bash
py tools/gen_fixtures.py --only {id}
py tools/gen_fixtures.py --check          # 位级一致
```

> 口径单点：`data/README.md` §六（本文件不复制判定式，只描述构造与期望形状）。
"""

CONSTRUCTION = {
    "F1": u"程序合成极小 TTF（`fontBuilder`，3 字形），`OS/2.fsType = 0x0108`：\n"
          u"bit3（Editable）+ bit8（No subsetting）。`OS/2.version = 4`。",
    "F2": u"程序合成极小 TTF，`OS/2.fsType = 0x000E`（bits 1/2/3 同时置位），"
          u"`OS/2.version = 0`。\n这是**反例守护**样本：v0–v2 规范要求「取最宽松」，"
          u"任何实现只要报互斥违规就是误报。",
    "F3": u"程序合成极小 TTF，`OS/2.fsType = 0x000E`（bits 1/2/3 同时置位），"
          u"`OS/2.version = 3`。\nv3+ 规范要求互斥，故必须报互斥违规。\n"
          u"F2 与 F3 的差别**只有两处**：`OS/2.version`（0 vs 3），以及由版本决定的 OS/2 表长"
          u"（v0 = 78 B / v3+ = 96 B —— `ulCodePageRange` 自 v0 起才有）；"
          u"cmap 与其余表完全一致。这是本工具版本分流能力的唯一判别样本。",
    "F4": u"`source.ttf` 含 `a b c 汉 字` 五个码位；用 `fontTools.subset`（默认 `ignore_missing_unicodes=True`）"
          u"对 `abc` 子集得到 `subset.ttf`。\n产物 cmap 只有 `a b c` —— 汉字**静默消失**（无报错、退出码 0）。",
    "F5": u"`source.ttf` 含 nameID 13/14 与许可文本；用默认 `name_IDs=[0,1,2,3,4,5,6]` / "
          u"`name_languages=[1033]` 子集。\n产物只剩 nameID 0–6、单一语言 → 13/14 被**默认剥离**。",
    "F6": u"`source.ttf` 的 `ulCodePageRange1 = 0x4001F`（含 CJK 与 Latin-1）；只对 `汉字` 子集。\n"
          u"fontTools 的 `recalcCodePageRanges` 在无可用码页时**回退置 bit0 (Latin 1)** → "
          u"产物 `ulCodePageRange1 = 0x1`，而 cmap 只有 CJK = 真实矛盾。",
}

TRUTH = {
    "F1": u"直接由 `fsType` 位运算得到（`data/README.md` §六.1.2 / §六.1.3）：\n"
          u"`perm = 8`（bits1–3 恰一位 → `direct`）；`may_subset = (fsType & 0x0100) == 0` → `false`。\n"
          u"其余四条：`embed_pdf = perm!=2 and !bit9` → `true`（bit8 只禁子集，不禁嵌入）；"
          u"`embed_app = perm==0` → `false`；`embed_web = perm!=2 and !bit8 and !bit9` → `false`；"
          u"`may_modify = perm in (0,8)` → `true`。\n"
          u"不是「跑一遍工具再看输出」，而是对**输入位值**的独立复算。",
    "F2": u"`bits = 0x000E`，`version = 0 <= 2` → 取最宽松 = bit3 Editable（`least_restrictive`）；"
          u"`may_subset = (0x000E & 0x0100) == 0` → `true`。\n"
          u"其余四条：`embed_pdf = true`、`embed_app = false`（perm≠0）、`embed_web = true`"
          u"（perm≠2 且 bit8/bit9 均未置位）、`may_modify = true`。\n"
          u"规范原文：「the least-restrictive permission indicated take precedence」（`data/README.md` §3.2）。",
    "F3": u"`bits = 0x000E`，`version = 3 ≥ 3` → **互斥违规**（`error`）。\n"
          u"最宽松权限仍是 Editable（`least_restrictive`），五元结论与 F2 **完全相同** —— "
          u"违规本身独立成条，两者不互相抵消（这是 F2/F3 对照的判别点）。",
    "F4": u"需求集 `R = {{a,b,c,汉,字}}`，产物覆盖 `T = {{a,b,c}}`，源覆盖 `S ⊇ R`：\n"
          u"`LOST_IN_SUBSET = (R ∩ S) \\ T = {{汉, 字}}`；`MISSING_IN_SOURCE = R \\ S = ∅`。\n"
          u"由「合成本身」决定，不依赖被测实现（`data/README.md` §六.2）。",
    "F5": u"源有 13/14、产物没有 → 差集非空 → 判「默认剥离」；"
          u"语言记录数由产物 name 表实读得到 `1`。\n"
          u"（若源也没有 13/14，则应判「原作者没写」 —— 这一分类需要 `--source` 才能做。）",
    "F6": u"码页 bit0 声明 Latin-1，而 cmap 覆盖 ∩ `U+0000–U+00FF` = ∅ → 矛盾。\n"
          u"同时 `ulUnicodeRange1 = 0` 是**正确重算**（bit59 在 `ulUnicodeRange2`）→ **不得**报矛盾。",
}


def _write_text(path, text):
    """UTF-8 + LF，不依赖平台换行（`newline=''` 在 3.8 的 ``io.open`` 里可用）。"""
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _fonttools_version():
    try:
        import fontTools
        return str(fontTools.version)
    except Exception:  # noqa: BLE001
        return "unknown"


#: golden **铸造时**的 fontTools 版本（不是"当前运行环境的版本"）。
#:
#: 为什么是常量：``expect.json`` 与 ``manifest.json`` 要跨解释器逐字节可比 ——
#: 若写入运行时版本，3.8 通道（4.57.0）与 3.12 通道（4.67.0）生成的 golden 会分叉，
#: ``--check`` 在每个 CI 矩阵格子里都会红。**实测**（2026-10-21）：两个版本的产物
#: 二进制逐字节相同，唯一差异就是这行版本串 → 说明"漂移"其实来自记录方式，
#: 不是来自 fontTools 行为。
#:
#: 语义仍然成立（``plan/04`` §4.3）：本值 = 铸造 golden 的版本；将来 fontTools
#: 升级若真的改变产物，``--check`` 会因**字节差异**变红 → 视为 fixture 迁移事件，
#: 逐条复核后重生成并把本常量改成新版本。
GOLDEN_FONTOOLS_VERSION = "4.57.0"


def generate(selected, out_root, verbose=True):
    """生成选中的 fixture；返回 ``[(fid, name, path, expect_path, size, sha256)]``。"""
    results = []
    for fid in selected:
        name = FIXTURE_NAMES[fid]
        out_dir = os.path.join(out_root, name, "out")
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        path, expect = BUILDERS[fid](out_dir)
        expect["fonttools_version"] = GOLDEN_FONTOOLS_VERSION
        problems = self_check(fid, path, expect)
        if problems:
            raise AssertionError("%s %s 自证失败：%s" % (fid, name, "；".join(problems)))
        expect_path = os.path.join(out_root, name, "expect.json")
        _write_text(expect_path, _dumps(expect))
        summary = "\n".join("%s: %s" % (k, json.dumps(v, ensure_ascii=False))
                            for k, v in sorted(expect["expect"].items()))
        _write_text(os.path.join(out_root, name, "README.md"),
                    FIXTURE_README.format(name=name, id=fid,
                                          construction=CONSTRUCTION[fid],
                                          truth=TRUTH[fid], summary=summary))
        size = os.path.getsize(path)
        sha = _sha256(path)
        results.append((fid, name, path, expect_path, size, sha))
        if verbose:
            print("  %s %-22s %7d B  %s  %s"
                  % (fid, name, size, sha[:16], os.path.basename(path)))
    return results


def _write_manifest(out_root, results):
    """``manifest.json`` **只在全量运行时写**（部分运行绝不许改写全集清单）。"""
    body = {
        "version": 1,
        "fonttools_version": GOLDEN_FONTOOLS_VERSION,
        "note": "产物不入仓；本清单由 tools/gen_fixtures.py 全量运行时生成。",
        "fixtures": [
            {"id": fid, "name": name, "font": os.path.basename(path),
             "bytes": size, "sha256": sha}
            for (fid, name, path, _expect, size, sha) in results
        ],
    }
    _write_text(os.path.join(out_root, "manifest.json"), _dumps(body))


# ── --check：重生成到临时目录 → 逐字节比对 ─────────────────────────────────
def _text_files_under(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(dirnames)
        for name in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
            out.append(rel)
    return out


def check(selected, out_root, verbose=True):
    """重生成到临时目录 → 与已生成产物逐字节 ``cmp``。返回 (ok, problems)。"""
    import shutil
    import tempfile

    tmp_root = tempfile.mkdtemp(prefix="subsetaudit-fixtures-")
    problems = []
    try:
        fresh = generate(selected, tmp_root, verbose=False)
        if len(selected) == len(FIXTURES):
            _write_manifest(tmp_root, fresh)
        for rel in _text_files_under(tmp_root):
            a = os.path.join(tmp_root, rel)
            b = os.path.join(out_root, rel)
            if not os.path.isfile(b):
                problems.append("产物缺失：%s（先跑一次 py tools/gen_fixtures.py）" % rel)
                continue
            with open(a, "rb") as fa, open(b, "rb") as fb:
                ba, bb = fa.read(), fb.read()
            if ba != bb:
                problems.append("逐字节不一致：%s（fresh %d B sha=%s / 仓库 %d B sha=%s）"
                                % (rel, len(ba), _sha256(a)[:16], len(bb), _sha256(b)[:16]))
        # 反向：仓库里多出来的文件同样是漂移
        for rel in _text_files_under(out_root):
            if not os.path.isfile(os.path.join(tmp_root, rel)):
                problems.append("仓库有、重生成没有：%s（残留产物？）" % rel)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
    if verbose:
        if problems:
            for p in problems:
                print("  MISMATCH %s" % p)
        else:
            print("  %d 个文件逐字节一致（%d 个 fixture）" % (len(_text_files_under(out_root)),
                                                       len(selected)))
    return (not problems), problems


def _display_path(path):
    """打印用的路径：仓库内给相对路径，跨盘（C: 临时目录 vs D: 仓库）时退回 basename。

    ``os.path.relpath`` 在跨盘符时抛 ``ValueError`` —— 这是 Windows 实测坑，
    不是"理论上的边界情况"（M1 实测：pytest 的 tmp_path 在 C:，仓库在 D:）。
    """
    try:
        rel = os.path.relpath(path, ROOT)
    except ValueError:
        return os.path.basename(path.rstrip("\\/")) or path
    return rel.replace(os.sep, "/")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="gen_fixtures.py",
        description="F1–F6 合成破损 fixture 生成器（确定性、离线、产物不入仓）。",
    )
    parser.add_argument("--only", metavar="F1,F3", help="只生成指定 fixture（不写 manifest.json）")
    parser.add_argument("--out", metavar="DIR", default=DATA, help="输出根目录（默认 data/fixtures）")
    parser.add_argument("--check", action="store_true",
                        help="重生成到临时目录并与已有产物逐字节比对")
    args = parser.parse_args(argv)

    selected = [fid for fid, _ in FIXTURES]
    if args.only:
        wanted = [x.strip().upper() for x in args.only.split(",") if x.strip()]
        unknown = [x for x in wanted if x not in FIXTURE_NAMES]
        if unknown:
            sys.stderr.write("未知 fixture: %s（可选：%s）\n"
                             % (",".join(unknown), ",".join(fid for fid, _ in FIXTURES)))
            return 2
        selected = [fid for fid, _ in FIXTURES if fid in wanted]

    # 相对 --out 相对**当前工作目录**解析（而不是仓库根）：`os.path.relpath(out_root, ROOT)`
    # 在跨盘符（C: 临时目录 vs D: 仓库）时会抛 ValueError —— 用 abspath 归一后仍可能跨盘，
    # 所以打印时用 try/except 兜底，判定本身不依赖这个字符串。
    out_root = args.out if os.path.isabs(args.out) else os.path.abspath(args.out)

    if args.check:
        print("gen_fixtures --check：重生成 %d 个 fixture 并逐字节比对" % len(selected))
        ok, problems = check(selected, out_root)
        print("结论: %s" % ("位级一致" if ok else "发现 %d 处不一致" % len(problems)))
        return 0 if ok else 1

    print("gen_fixtures：生成 %d 个 fixture → %s"
          % (len(selected), _display_path(out_root)))
    try:
        results = generate(selected, out_root)
    except AssertionError as exc:
        sys.stderr.write("生成期自证失败: %s\n" % exc)
        return 1
    if len(selected) == len(FIXTURES):
        _write_manifest(out_root, results)
        print("  manifest.json 已写入（%d 项，仅全量运行会写）" % len(results))
    else:
        print("  部分运行：未写 manifest.json（纪律：部分运行不许改写全集清单）")
    print("结论: %d 个 fixture 生成成功，自证通过" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
