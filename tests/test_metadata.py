# -*- coding: utf-8 -*-
"""M5 `metadata` 测试：F5/F6 golden 逐项、两类缺失、码页矛盾、`ulUnicodeRange1=0` 反例守护、
`maxp` 相等不报、四条 SKIPPED、双跑、口径对账、改坏必红。

口径单点在 ``data/README.md`` §六.9；本文件**不复制判定式**，只做三件事：
  ① 断言实现与 §六.9 的口径一致（含 `spec_ref` 字面量逐字对账）；
  ② 用独立 oracle（裸 sfnt 位解析 / 另一条代码路径）复算，与 golden 三方对齐；
  ③ 用变异证明这些断言真的会红。
"""
from __future__ import print_function

import io
import json
import os
import struct

import pytest

from conftest import build_font
from subsetaudit import canonical, cli, metadata, sfnt

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_ROOT = os.path.join(REPO_ROOT, "data", "fixtures")
DATA_README = os.path.join(REPO_ROOT, "data", "README.md")

NAMES = {"F5": "metadata-stripped", "F6": "codepage-mismatch"}


def _read(rel):
    with io.open(os.path.join(REPO_ROOT, rel), "r", encoding="utf-8") as fh:
        return fh.read()


def _fixture(fid):
    with io.open(os.path.join(FIXTURES_ROOT, NAMES[fid], "expect.json"),
                 "r", encoding="utf-8") as fh:
        body = json.load(fh)
    out = os.path.join(FIXTURES_ROOT, NAMES[fid], "out")
    return (os.path.join(out, body["input"]["subset"]),
            os.path.join(out, body["input"]["source"]), body)


def _codes(findings):
    return [(f["code"], f["severity"], f["primary_key"]) for f in findings]


def _run(argv, capsys):
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out


# ── ① F5/F6 golden 逐项 ────────────────────────────────────────────────────
def test_f5_golden_findings_and_classification():
    """F5：缺 13/14 判「默认剥离」；缺 7/11/16/17 判「原作者没写」→ **两种都不得混**。"""
    subset, source, body = _fixture("F5")
    findings, skips, summary = metadata.evaluate(subset, source_path=source)
    exp = body["expect"]

    assert skips == []
    assert [(f["code"], f["severity"], f["primary_key"], f["spec_ref"]) for f in findings] == [
        (item["code"], item["severity"], item["primary_key"], item["spec_ref"])
        for item in exp["expected_findings"]
    ]
    classes = summary["metadata"]["name"]["classification"]
    assert classes["default_stripped"] == exp["default_stripped_name_ids"]
    assert classes["author_absent"] == exp["author_absent_name_ids"]
    assert classes["unclassified"] == []
    assert summary["metadata"]["name"]["classification_source"] == "source"


@pytest.mark.parametrize("absent", ["NAME_TRADEMARK_STRIPPED", "NAME_VENDOR_URL_STRIPPED",
                                    "NAME_TYPOGRAPHIC_FAMILY_STRIPPED",
                                    "NAME_TYPOGRAPHIC_SUBFAMILY_STRIPPED"])
def test_f5_author_absent_ids_produce_no_finding(absent):
    """「原作者没写」**不得**产 finding —— 这是 §六.9.1 与"见缺就报"的分界线。"""
    subset, source, _body = _fixture("F5")
    findings, _skips, _summary = metadata.evaluate(subset, source_path=source)
    assert absent not in [f["code"] for f in findings]


def test_f5_golden_absent_findings_match_expect_json():
    """golden 的 `expected_absent_findings` 逐条断言"确实没出现"（不是抽查）。"""
    subset, source, body = _fixture("F5")
    findings, _skips, _summary = metadata.evaluate(subset, source_path=source)
    got = set((f["code"], f["primary_key"]) for f in findings)
    for item in body["expect"]["expected_absent_findings"]:
        assert (item["code"], item["primary_key"]) not in got


def test_f5_without_source_does_not_classify_and_does_not_judge():
    """**无 `--source` → `unclassified`、不产 finding**（看不到原文，分不出责任，不猜）。"""
    subset, _source, _body = _fixture("F5")
    findings, skips, summary = metadata.evaluate(subset)
    assert skips == []
    assert findings == [], "无源时不得把『缺』当成『被剥』"
    name = summary["metadata"]["name"]
    assert name["classification_source"] == "none"
    assert name["source_present"] is False
    assert name["classification"]["unclassified"] == [7, 11, 13, 14, 16, 17]
    assert name["classification"]["default_stripped"] == []
    assert name["classification"]["author_absent"] == []


def test_f5_language_shrink_is_reported_but_not_a_finding():
    """语言裁剪只计数、不产 finding（§六.9.1 末条）。"""
    subset, source, _body = _fixture("F5")
    findings, _skips, summary = metadata.evaluate(subset, source_path=source)
    langs = summary["metadata"]["name"]["languages"]
    assert langs["subset"] == [1033]
    assert langs["source"] == [0, 1033, 1041]
    assert summary["metadata"]["name"]["language_count"] == {"subset": 1, "source": 3}
    assert all("LANGUAGE" not in f["code"] for f in findings), "语言裁剪不得产 finding"


def test_f6_codepage_contradiction_is_an_error():
    """F6：`ulCodePageRange1 = 0x1`（Latin-1）而 cmap 无任何 `≤ U+00FF` → 矛盾。"""
    subset, source, body = _fixture("F6")
    findings, _skips, summary = metadata.evaluate(subset, source_path=source)
    exp = body["expect"]

    hits = [f for f in findings if f["code"] == "CODEPAGE_CLAIMS_LATIN1_WITHOUT_COVERAGE"]
    assert len(hits) == 1
    item = hits[0]
    assert item["severity"] == "error"
    assert item["primary_key"] == "cp1:latin1"
    assert item["spec_ref"] == "fontTools O_S_2f_2.recalcCodePageRanges"
    assert item["evidence"]["claims_latin1"] is True
    assert item["evidence"]["latin1_codepoints"] == 0
    assert summary["metadata"]["codepage"]["ulCodePageRange1"] == exp["ulCodePageRange1"]
    assert summary["metadata"]["codepage"]["judged_bits"] == [0]


def test_f6_ulunicode_range1_zero_is_not_a_contradiction():
    """**反例守护**：`ulUnicodeRange1 = 0` 是正确重算（bit59 在 `ulUnicodeRange2`）。

    这条是本模块最容易被"写得更严"而误伤的地方：只要实现拿"是否为 0"当判据，它必红。
    对应初稿的假阳性（`data/README.md` §七 #3）。
    """
    subset, source, body = _fixture("F6")
    findings, _skips, summary = metadata.evaluate(subset, source_path=source)
    ur = summary["metadata"]["unicode_range"]

    assert ur["declared"] == body["expect"]["unicode_range_declared_bits"] == [59]
    assert ur["declared_empty"] is False
    # 任何"拿 ur1 是否为零"的判据都会产这两条 → 必须一条都没有
    assert "UNICODE_RANGE_CONTRADICTION" not in [f["code"] for f in findings]
    assert "ur1:zero" not in [f["primary_key"] for f in findings]
    # bit59 声明了且 cmap 真有 CJK → 过度声明也不得开火
    assert ur["over_declared"] == []
    assert "UNICODE_RANGE_OVER_DECLARED" not in [f["code"] for f in findings]


def test_f6_maxp_and_char_index_agree():
    """F6：`maxp` 与实际字形数相等、首末码位恰好覆盖 → **都不产 finding**（DoD）。"""
    subset, source, _body = _fixture("F6")
    findings, _skips, summary = metadata.evaluate(subset, source_path=source)
    maxp = summary["metadata"]["maxp"]
    assert maxp["numGlyphs"] == maxp["measured"] == 3
    assert maxp["match"] is True
    idx = summary["metadata"]["char_index"]
    assert idx["judged"] is True
    assert idx["measured_min"] == "U+5B57" and idx["measured_max"] == "U+6C49"
    assert "MAXP_NUM_GLYPHS_MISMATCH" not in [f["code"] for f in findings]
    assert "CHAR_INDEX_MISMATCH" not in [f["code"] for f in findings]


def test_f6_exit_code_is_one(capsys):
    """F6 有 `error` 级发现 → 退出码 1（§六.6）。"""
    subset, source, _body = _fixture("F6")
    code, out = _run(["metadata", subset, "--source", source], capsys)
    assert code == cli.EXIT_FINDINGS
    assert json.loads(out)["findings"]


# ── ② 独立 oracle（裸 sfnt 位解析）三方对齐 ────────────────────────────────
def _oracle_os2(path):
    """裸读 OS/2 字节（偏移照规范写死），返回位号集合与码页字。"""
    raw = open(path, "rb").read()
    num = struct.unpack(">H", raw[4:6])[0]
    tables = {}
    for i in range(num):
        off = 12 + i * 16
        tag = raw[off:off + 4].decode("latin-1")
        _ck, ofs, ln = struct.unpack(">III", raw[off + 4:off + 16])
        tables[tag] = (ofs, ln)
    base = tables["OS/2"][0]
    words = list(struct.unpack(">IIII", raw[base + 42:base + 58]))
    cp1, cp2 = struct.unpack(">II", raw[base + 78:base + 86])
    first, last = struct.unpack(">HH", raw[base + 64:base + 68])
    bits = set()
    for index, word in enumerate(words):
        for i in range(32):
            if word & (1 << i):
                bits.add(32 * index + i)
    return {"bits": bits, "cp": (cp1, cp2), "first": first, "last": last,
            "maxp_offset": tables.get("maxp")}


def _oracle_maxp(path):
    raw = open(path, "rb").read()
    num = struct.unpack(">H", raw[4:6])[0]
    for i in range(num):
        off = 12 + i * 16
        tag = raw[off:off + 4].decode("latin-1")
        _ck, ofs, _ln = struct.unpack(">III", raw[off + 4:off + 16])
        if tag == "maxp":
            return struct.unpack(">H", raw[ofs + 4:ofs + 6])[0]
    raise AssertionError("没有 maxp 表")


def _oracle_loca_count(path):
    """独立字形数：`loca` 表长 / 每项字节数 - 1（不经过 fontTools）。"""
    raw = open(path, "rb").read()
    num = struct.unpack(">H", raw[4:6])[0]
    tables = {}
    for i in range(num):
        off = 12 + i * 16
        tag = raw[off:off + 4].decode("latin-1")
        _ck, ofs, ln = struct.unpack(">III", raw[off + 4:off + 16])
        tables[tag] = (ofs, ln)
    head = tables["head"][0]
    per = 2 if struct.unpack(">h", raw[head + 50:head + 52])[0] == 0 else 4
    return tables["loca"][1] // per - 1


def _oracle_latin1_hits(path):
    """独立 cmap 覆盖：只数 format 4/12 里 `≤ U+00FF` 的条目（gid 0 不算）。"""
    raw = open(path, "rb").read()
    num = struct.unpack(">H", raw[4:6])[0]
    tables = {}
    for i in range(num):
        off = 12 + i * 16
        tag = raw[off:off + 4].decode("latin-1")
        _ck, ofs, ln = struct.unpack(">III", raw[off + 4:off + 16])
        tables[tag] = (ofs, ln)
    base = tables["cmap"][0]
    _ver, count = struct.unpack(">HH", raw[base:base + 4])
    hits = set()
    for i in range(count):
        rec = base + 4 + i * 8
        pid, eid, sub_off = struct.unpack(">HHI", raw[rec:rec + 8])
        if (pid, eid) not in ((3, 1), (3, 10), (0, 3), (0, 4)):
            continue
        fmt = struct.unpack(">H", raw[base + sub_off:base + sub_off + 2])[0]
        if fmt == 4:
            seg_x2 = struct.unpack(">H", raw[base + sub_off + 6:base + sub_off + 8])[0]
            segs = seg_x2 // 2
            ends_at = base + sub_off + 14
            starts_at = ends_at + seg_x2 + 2
            delta_at = starts_at + seg_x2
            range_at = delta_at + seg_x2
            for s in range(segs):
                end = struct.unpack(">H", raw[ends_at + s * 2:ends_at + s * 2 + 2])[0]
                start = struct.unpack(">H", raw[starts_at + s * 2:starts_at + s * 2 + 2])[0]
                delta = struct.unpack(">h", raw[delta_at + s * 2:delta_at + s * 2 + 2])[0]
                ro = struct.unpack(">H", raw[range_at + s * 2:range_at + s * 2 + 2])[0]
                if start > end or start > 0xFF:
                    continue
                for cp in range(start, min(end, 0xFF) + 1):
                    if ro == 0:
                        gid = (cp + delta) & 0xFFFF
                    else:
                        addr = range_at + s * 2 + ro + (cp - start) * 2
                        gid = struct.unpack(">H", raw[addr:addr + 2])[0]
                        if gid:
                            gid = (gid + delta) & 0xFFFF
                    if gid:
                        hits.add(cp)
        elif fmt == 12:
            groups = struct.unpack(
                ">I", raw[base + sub_off + 12:base + sub_off + 16])[0]
            for g in range(groups):
                at = base + sub_off + 16 + g * 12
                lo, hi, gid = struct.unpack(">III", raw[at:at + 12])
                if gid == 0 and lo == hi:
                    continue
                if lo > 0xFF:
                    break
                for cp in range(lo, min(hi, 0xFF) + 1):
                    if gid + (cp - lo):
                        hits.add(cp)
    return hits


@pytest.mark.parametrize("fid", ["F5", "F6"])
def test_oracle_agrees_on_os2_bits(fid):
    """裸字节 oracle 与实现算出的位号集合逐位一致（不是"抽查几个位"）。"""
    subset, _source, _body = _fixture(fid)
    oracle = _oracle_os2(subset)
    font = sfnt.open_font(subset)
    try:
        info = sfnt.os2_info(font)
        # 码页字与首末码位的原始字面量也要对上（换成 hex 串比，避免字节序误判）
        assert "0x%08X" % info["ulCodePageRange"][0] == "0x%08X" % oracle["cp"][0]
        assert "0x%08X" % info["ulCodePageRange"][1] == "0x%08X" % oracle["cp"][1]
        assert info["usFirstCharIndex"] == oracle["first"]
        assert info["usLastCharIndex"] == oracle["last"]
        unicode_bits, codepage_bits = metadata.os2_bits(info)
    finally:
        sfnt.close_font(font)
    assert unicode_bits == oracle["bits"]
    latin1_claims = 0 in codepage_bits
    assert latin1_claims == bool(oracle["cp"][0] & 0x1)


@pytest.mark.parametrize("fid", ["F5", "F6"])
def test_oracle_agrees_on_maxp_and_latin1_coverage(fid):
    """`maxp` 与 Latin-1 覆盖用裸字节复算，跟实现给出的 summary 三方对齐。"""
    subset, _source, _body = _fixture(fid)
    findings, _skips, summary = metadata.evaluate(subset)
    meta = summary["metadata"]

    assert _oracle_maxp(subset) == meta["maxp"]["numGlyphs"]
    assert _oracle_loca_count(subset) == meta["maxp"]["measured"]
    latin1 = _oracle_latin1_hits(subset)
    fired = [f for f in findings if f["code"] == "CODEPAGE_CLAIMS_LATIN1_WITHOUT_COVERAGE"]
    assert bool(fired) == (not latin1 and 0 in meta["codepage"]["bits"]), \
        "矛盾判据必须与裸字节覆盖一致（oracle 说没有 Latin-1 才该开火）"


# ── ③ 合成样本：逐条判据的独立触发面 ──────────────────────────────────────
def _patch_table(path, out, tag, writer):
    """把 ``path`` 的某张表按 ``writer(bytearray, offset)`` 改一处后另存 ``out``（测试专用）。"""
    raw = bytearray(open(path, "rb").read())
    num = struct.unpack(">H", raw[4:6])[0]
    for i in range(num):
        off = 12 + i * 16
        name = raw[off:off + 4].decode("latin-1")
        if name != tag:
            continue
        _ck, ofs, _ln = struct.unpack(">III", raw[off + 4:off + 16])
        writer(raw, ofs)
        break
    else:
        raise AssertionError("没有 %r 表" % tag)
    open(out, "wb").write(bytes(raw))
    return out


def test_maxp_mismatch_is_reported(tmp_path):
    """把 `maxp.numGlyphs` 改大 → 独立量（`loca`）没变 → 必报 `error`。

    这是 §六.9.4 "独立量"设计的承重点：若拿 `getGlyphOrder()` 比，fontTools 会跟着
    `maxp` 补名 → 判据恒真、永远不红。
    """
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"})
    bad = str(tmp_path / "bad.ttf")
    _patch_table(path, bad, "maxp",
                 lambda raw, ofs: struct.pack_into(">H", raw, ofs + 4, 9))

    findings, skips, summary = metadata.evaluate(bad)
    hits = [f for f in findings if f["code"] == "MAXP_NUM_GLYPHS_MISMATCH"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "error"
    assert hits[0]["primary_key"] == "maxp"
    assert hits[0]["evidence"]["numGlyphs"] == 9
    assert hits[0]["evidence"]["measured"] == 3
    assert summary["metadata"]["maxp"]["match"] is False
    assert skips == []


def test_char_index_span_short_is_reported(tmp_path):
    """`usLastCharIndex` 比 cmap 最大码位小 → 报 `CHAR_INDEX_MISMATCH`（"没覆盖住"方向）。"""
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"})
    bad = str(tmp_path / "bad.ttf")
    _patch_table(path, bad, "OS/2",
                 lambda raw, ofs: struct.pack_into(">H", raw, ofs + 66, 0x61))

    findings, _skips, summary = metadata.evaluate(bad)
    hits = [f for f in findings if f["code"] == "CHAR_INDEX_MISMATCH"]
    assert [h["primary_key"] for h in hits] == ["usLastCharIndex"]
    assert hits[0]["severity"] == "warn"
    assert summary["metadata"]["char_index"]["judged"] is True


def test_char_index_sentinel_is_not_judged(tmp_path):
    """`0xFFFF` 是哨兵（该方向无约束）→ **不得**报（§六.9.5）。"""
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"})
    ok = str(tmp_path / "ok.ttf")

    def widen(raw, ofs):
        struct.pack_into(">H", raw, ofs + 64, 0xFFFF)
        struct.pack_into(">H", raw, ofs + 66, 0xFFFF)

    _patch_table(path, ok, "OS/2", widen)
    findings, _skips, summary = metadata.evaluate(ok)
    assert [f for f in findings if f["code"] == "CHAR_INDEX_MISMATCH"] == []
    assert summary["metadata"]["char_index"]["judged"] is True


def test_char_index_padding_is_not_reported(tmp_path):
    """字段比实际**宽**（留白）不判（§六.9.5："只判没覆盖住"方向）。"""
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"})
    ok = str(tmp_path / "ok.ttf")

    def widen(raw, ofs):
        struct.pack_into(">H", raw, ofs + 64, 0x0020)
        struct.pack_into(">H", raw, ofs + 66, 0x2000)

    _patch_table(path, ok, "OS/2", widen)
    findings, _skips, _summary = metadata.evaluate(ok)
    assert [f for f in findings if f["code"] == "CHAR_INDEX_MISMATCH"] == []


def test_unicode_range_over_declaration_is_reported(tmp_path):
    """位置了但 cmap 里没有该块的码位 → 报 `UNICODE_RANGE_OVER_DECLARED`（§六.9.3 判的方向）。"""
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a"}, unicode_range=(0x1, 0x0, 0x0, 0x0))
    # 只把 bit1（Latin-1 Supplement）打开：cmap 里只有 U+0061（Basic Latin）
    bad = str(tmp_path / "bad.ttf")
    _patch_table(path, bad, "OS/2",
                 lambda raw, ofs: struct.pack_into(">I", raw, ofs + 42, 0x3))

    findings, _skips, summary = metadata.evaluate(bad)
    hits = [f for f in findings if f["code"] == "UNICODE_RANGE_OVER_DECLARED"]
    assert [h["primary_key"] for h in hits] == ["ur:bit1"]
    assert hits[0]["severity"] == "warn"
    assert hits[0]["spec_ref"] == "MS-OS2 §ulUnicodeRange"
    assert summary["metadata"]["unicode_range"]["over_declared"] == [1]


def test_unicode_range_under_declaration_is_not_reported(tmp_path):
    """**欠声明不判**（§六.9.3）：cmap 有 Latin-1 而一个位都没置 → 不产 finding。"""
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a", 0xE9: "eacute"}, unicode_range=(0x0, 0x0, 0x0, 0x0))
    findings, _skips, summary = metadata.evaluate(path)
    assert [f for f in findings if f["code"].startswith("UNICODE_RANGE")] == []
    assert summary["metadata"]["unicode_range"]["declared_empty"] is True
    assert summary["metadata"]["unicode_range"]["under_declared"], "欠声明要**报数**（只是不判）"


def test_behavioral_bit57_uses_non_bmp_rule_not_the_surrogate_range(tmp_path):
    """bit57 = `Non-Plane 0 *`：判定式是"存在 `> U+FFFF` 码位"，不是"代理区里有字符"。

    这是 M5 实测发现的口径缺口：该位在 fontTools 表里写作 `U+D800–U+DFFF`（代理区，本身不含
    任何可编码字符）。按区间比对 → **恒为假** → 26 个真实字体被误判成过度声明
    （`data/README.md` §六.9.3 / §四.1 #15）。
    """
    assert metadata.unicode_range_block_ranges(57) == [(0xD800, 0xDFFF)]
    assert metadata.is_behavioral_bit(57) is True
    assert metadata.is_behavioral_bit(59) is False

    # ① 置了 bit57 且**有**非 BMP 码位 → 满足（不产 finding）
    good = str(tmp_path / "good.ttf")
    build_font(good, cmap={0x61: "a", 0x1F600: "emoji"},
               unicode_range=(0x0, 0x02000000, 0x0, 0x0))
    findings, _skips, summary = metadata.evaluate(good)
    assert [f for f in findings if f["primary_key"] == "ur:bit57"] == []
    assert 57 in summary["metadata"]["unicode_range"]["declared"]
    assert 57 not in summary["metadata"]["unicode_range"]["over_declared"]

    # ② 置了 bit57 但**只有** BMP 码位 → 过度声明（finding 带 behavioral 标记）
    bad = str(tmp_path / "bad.ttf")
    build_font(bad, cmap={0x61: "a"}, unicode_range=(0x0, 0x02000000, 0x0, 0x0))
    findings, _skips, _summary = metadata.evaluate(bad)
    hits = [f for f in findings if f["primary_key"] == "ur:bit57"]
    assert len(hits) == 1
    assert hits[0]["evidence"]["behavioral"] is True


@pytest.mark.skipif(not os.path.isfile(os.path.join(REPO_ROOT, "data", "fonts",
                                                    "NotoSansSC-Regular.otf")),
                    reason="data/fonts 未下载（离线环境）")
def test_real_ofl_fonts_do_not_trip_the_metadata_rules():
    """三个 OFL 字体上：Noto 两支 0 条 finding；Inter 只报它**真实**的 4 个过度声明位。

    Inter 的 4 条是**上游事实**（它声明了 Hebrew / Alphabetic Presentation Forms /
    Combining Half Marks / Specials 而 cmap 里没有这些区的码位，实测见 §四.1 #15），
    不是本工具的误报 —— 这里逐位钉住，防止"把判据调松到全绿"。
    """
    sc = os.path.join(REPO_ROOT, "data", "fonts", "NotoSansSC-Regular.otf")
    bold = os.path.join(REPO_ROOT, "data", "fonts", "NotoSans-Bold.ttf")
    inter = os.path.join(REPO_ROOT, "data", "fonts", "InterVariable.ttf")

    findings, skips, summary = metadata.evaluate(sc)
    assert findings == [] and skips == []
    assert summary["metadata"]["maxp"]["match"] is True
    assert summary["metadata"]["unicode_range"]["over_declared"] == []

    findings, skips, _summary = metadata.evaluate(bold)
    assert findings == [] and skips == []

    findings, skips, summary = metadata.evaluate(inter)
    assert skips == []
    assert [f["primary_key"] for f in findings] == [
        "ur:bit11", "ur:bit62", "ur:bit64", "ur:bit69"]
    assert all(f["severity"] == "warn" for f in findings)


def test_unicode_range_zero_is_not_a_contradiction(tmp_path):
    """`ulUnicodeRange1 = 0` 且 cmap 非空 → 不是矛盾（初稿假阳性的最小复现样本）。"""
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a"}, unicode_range=(0x0, 0x0, 0x0, 0x0))
    findings, _skips, _summary = metadata.evaluate(path)
    assert findings == []
    assert "UNICODE_RANGE_CONTRADICTION" not in [f["code"] for f in findings]


def test_codepage_bit0_with_latin1_coverage_is_not_reported(tmp_path):
    """声明 Latin-1 且**确实有** `≤ U+00FF` 码位 → 不报（矛盾判据要能区分两侧）。"""
    path = str(tmp_path / "s.ttf")
    # `ulCodePageRange` 自 OS/2 v1 才有 ⇒ `version=1`（v0 上这两个字段根本不存在）
    build_font(path, cmap={0x61: "a"}, version=1, code_page_range=(0x1, 0x0))
    findings, _skips, summary = metadata.evaluate(path)
    assert [f for f in findings if f["code"] == "CODEPAGE_CLAIMS_LATIN1_WITHOUT_COVERAGE"] == []
    assert summary["metadata"]["codepage"]["detail"][0]["hits"] == 1
    assert summary["metadata"]["codepage"]["bits"] == [0]


def test_codepage_non_latin1_bits_are_listed_but_not_judged(tmp_path):
    """非 bit0 的码页位**列事实、不判定**（§六.9.2：逐位判会批量误报）。"""
    path = str(tmp_path / "s.ttf")
    # bit2 = Cyrillic，cmap 只有 Latin-1 → 若逐位判就会误报
    build_font(path, cmap={0x61: "a"}, version=1, code_page_range=(0x4, 0x0))
    findings, _skips, summary = metadata.evaluate(path)
    assert [f for f in findings if f["code"] == "CODEPAGE_CLAIMS_LATIN1_WITHOUT_COVERAGE"] == []
    detail = summary["metadata"]["codepage"]["detail"]
    assert [row["bit"] for row in detail] == [2]
    assert detail[0]["judged"] is False
    assert detail[0]["hits"] == 0
    assert summary["metadata"]["codepage"]["judged_bits"] == [0]


# ── ④ 四条 SKIPPED（不得合并） ─────────────────────────────────────────────
def test_no_os2_table_skips_with_empty_summary(tmp_path, capsys):
    path = str(tmp_path / "noos2.ttf")
    build_font(path, cmap={0x61: "a"}, include_os2=False)
    findings, skips, summary = metadata.evaluate(path)
    assert findings == []
    assert [s["reason"] for s in skips] == [metadata.REASON_NO_OS2]
    assert summary == {}
    assert skips[0]["detail"].startswith("subset:")

    code, out = _run(["metadata", path], capsys)
    assert code == cli.EXIT_OK
    body = json.loads(out)
    assert [s["reason"] for s in body["skipped"]] == ["no_os2_table"]
    assert body["findings"] == []


def test_no_name_table_skips_with_its_own_reason(tmp_path):
    """无 `name` 表 → `no_name_table`（**不得**与 `no_os2_table` 合并）。"""
    from fontTools.ttLib import TTFont

    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a"})
    out = str(tmp_path / "noname.ttf")
    font = TTFont(path)
    del font["name"]
    font.save(out)
    font.close()

    findings, skips, summary = metadata.evaluate(out)
    assert findings == []
    assert [s["reason"] for s in skips] == [metadata.REASON_NO_NAME]
    assert summary == {}


def test_no_cmap_table_skips_with_its_own_reason(tmp_path):
    from fontTools.ttLib import TTFont

    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a"})
    out = str(tmp_path / "nocmap.ttf")
    font = TTFont(path)
    del font["cmap"]
    font.save(out)
    font.close()

    findings, skips, summary = metadata.evaluate(out)
    assert findings == []
    assert [s["reason"] for s in skips] == [metadata.REASON_NO_CMAP_TABLE]
    assert summary == {}


def test_no_unicode_cmap_skips_with_its_own_reason(tmp_path):
    """只有 (1,0)/format 0 → `no_unicode_cmap`（复用 §六.3 的理由名，不另造）。"""
    path = str(tmp_path / "mac.ttf")
    build_font(path, cmap={0x61: "a"}, mac_only=True)
    findings, skips, summary = metadata.evaluate(path)
    assert findings == []
    assert [s["reason"] for s in skips] == [metadata.REASON_NO_UNICODE_CMAP]
    assert summary == {}


def test_the_four_skip_reasons_are_distinct():
    """四条理由两两不同（变异：把两条合并成一条 → 必红）。"""
    reasons = [metadata.REASON_NO_OS2, metadata.REASON_NO_NAME,
               metadata.REASON_NO_CMAP_TABLE, metadata.REASON_NO_UNICODE_CMAP]
    assert len(set(reasons)) == 4
    assert "no_cmap_table" in reasons and "no_unicode_cmap" in reasons


def test_non_font_is_exit_two(tmp_path, capsys):
    bad = tmp_path / "x.ttf"
    bad.write_text("nope", encoding="utf-8")
    code, _out = _run(["metadata", str(bad)], capsys)
    assert code == cli.EXIT_INPUT_ERROR


def test_missing_source_is_exit_two(tmp_path, capsys):
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a"})
    code, _out = _run(["metadata", path, "--source", str(tmp_path / "gone.ttf")], capsys)
    assert code == cli.EXIT_INPUT_ERROR


# ── ⑤ 确定性 / 脱敏 / 渲染 ─────────────────────────────────────────────────
def test_json_is_byte_identical_across_runs(tmp_path):
    subset, source, _body = _fixture("F6")
    a, b = str(tmp_path / "a.json"), str(tmp_path / "b.json")
    for target in (a, b):
        body = cli.main(["metadata", subset, "--source", source, "--out", target])
        assert body == cli.EXIT_FINDINGS
    assert open(a, "rb").read() == open(b, "rb").read()


def test_report_has_no_absolute_path(tmp_path, capsys):
    subset, source, _body = _fixture("F6")
    _code, out = _run(["metadata", subset, "--source", source], capsys)
    body = json.loads(out)
    assert body["inputs"] == {"subset": "subset.ttf", "source": "source.ttf"}
    assert "/" not in body["inputs"]["subset"] and "\\" not in body["inputs"]["subset"]


def test_markdown_view_renders(capsys):
    subset, source, _body = _fixture("F5")
    code, out = _run(["metadata", subset, "--source", source, "--markdown"], capsys)
    assert code == cli.EXIT_OK
    assert out.startswith("# SubsetAudit 报告")
    assert "NAME_LICENSE_DESCRIPTION_STRIPPED" in out


def test_no_timestamp_in_output(capsys):
    """报告不含时间戳（确定性纪律，§六.8）。"""
    import re

    subset, source, _body = _fixture("F5")
    _code, out = _run(["metadata", subset, "--source", source], capsys)
    assert not re.search(r"20\d\d-\d\d-\d\d", out), "报告里不得出现日期"


# ── ⑥ 口径对账（spec_ref 逐字 / §六.9 小节标题可解析） ─────────────────────
def test_spec_ref_matches_data_readme_section():
    """`SPEC_REF` 必须是 `data/README.md` 里真实存在的节号（变异：改一边必红）。"""
    assert metadata.SPEC_REF == "data/README §6.9"
    text = _read("data/README.md")
    for needle in ("§六.9", "9.1 name 存活", "9.2 `ulCodePageRange`", "9.3 `ulUnicodeRange`",
                   "9.4 `maxp.numGlyphs`", "9.5 `usFirstCharIndex`", "9.6 失败路径",
                   "9.7 `report` 聚合口径"):
        assert needle in text, needle


def test_spec_declares_the_counterexample_guard():
    """§六.9.3 必须写清"全零不判"这条反例守护，否则实现会被"写得更严"改坏。"""
    text = _read("data/README.md")
    assert "全零" in text
    assert "UNICODE_RANGE_CONTRADICTION" in text
    assert "ur1:zero" in text


def test_spec_declares_only_bit0_codepage_judgement():
    """§六.9.2 必须写明"只判 bit0"及其理由（否则会被当成漏实现）。"""
    text = _read("data/README.md")
    assert "只判 bit0" in text
    assert metadata.CODEPAGE_LATIN1_SPEC_REF == "fontTools O_S_2f_2.recalcCodePageRanges"


def test_name_codes_are_the_seven_in_spec():
    """只此七条 name 码，且 ID 集合与 §六.9.1 一致（不另立）。"""
    assert sorted(metadata.NAME_CODES) == [0, 7, 11, 13, 14, 16, 17]
    assert sorted(metadata.REQUIRED_NAME_IDS) == sorted(metadata.NAME_CODES)
    assert sorted(set(code for code, _ref in metadata.NAME_CODES.values())) == sorted(
        ["NAME_COPYRIGHT_STRIPPED", "NAME_TRADEMARK_STRIPPED", "NAME_VENDOR_URL_STRIPPED",
         "NAME_LICENSE_DESCRIPTION_STRIPPED", "NAME_LICENSE_INFO_URL_STRIPPED",
         "NAME_TYPOGRAPHIC_FAMILY_STRIPPED", "NAME_TYPOGRAPHIC_SUBFAMILY_STRIPPED"])


def test_spec_refs_are_literal_copies():
    """五个 `spec_ref` 字面量逐字对账（改一边必红）。"""
    assert metadata.NAME_CODES[13][1] == "MS-NAME nameID13"
    assert metadata.NAME_CODES[14][1] == "MS-NAME nameID14"
    assert metadata.UNICODE_RANGE_SPEC_REF == "MS-OS2 §ulUnicodeRange"
    assert metadata.MAXP_SPEC_REF == "MS-maxp §numGlyphs"
    assert metadata.CHAR_INDEX_SPEC_REF == "MS-OS2 §usFirstCharIndex"


def test_unicode_range_blocks_come_from_fonttools_not_a_copy():
    """块范围必须来自 fontTools 的表（§六.9.3：本仓库不复制）——123 个块。"""
    from fontTools.ttLib.tables import O_S_2f_2 as os2_module

    assert len(os2_module.OS2_UNICODE_RANGES) == 123
    assert metadata.unicode_range_block_ranges(59) == [
        (19968, 40959), (11904, 12031), (12032, 12255), (12272, 12287),
        (13312, 19903), (131072, 173791), (12688, 12703),
    ]
    assert metadata.unicode_range_block_ranges(123) is None
    source = _read("src/subsetaudit/metadata.py")
    assert "OS2_UNICODE_RANGES" in source
    assert "19968" not in source, "块范围不得硬编码进实现（复制即第二套口径）"


def test_readonly_layer_still_never_saves():
    """K6：`metadata` 只读 —— 源码里不得出现 `.save(`。"""
    assert ".save(" not in _read("src/subsetaudit/metadata.py")


# ── ⑦ 变异：改坏实现至少一层测试必红 ──────────────────────────────────────
def test_mutation_treating_absent_as_stripped_is_caught(monkeypatch):
    """变异 1：把"原作者没写"也算成"被剥" → 七条码全开火、`author_absent` 归零。"""
    subset, source, _body = _fixture("F5")
    monkeypatch.setattr(metadata, "_name_state",
                        lambda ids, src: (list(ids), [7, 11, 13, 14, 16, 17],
                                          {metadata.CLASS_DEFAULT_STRIPPED: [7, 11, 13, 14, 16, 17],
                                           metadata.CLASS_AUTHOR_ABSENT: [],
                                           metadata.CLASS_UNCLASSIFIED: []}))
    findings, _skips, _summary = metadata.evaluate(subset, source_path=source)
    codes = [f["code"] for f in findings]
    assert "NAME_TRADEMARK_STRIPPED" in codes, "变异必须让『原作者没写』那四条也开火"
    assert len(codes) == 6


def test_mutation_ignoring_source_is_caught(monkeypatch):
    """变异 2：不管 `--source` 一律判 `default_stripped` → 无源调用也产 finding。"""
    subset, _source, _body = _fixture("F5")

    def forced(ids, src):
        return ([], [7, 11, 13, 14, 16, 17],
                {metadata.CLASS_DEFAULT_STRIPPED: [7, 11, 13, 14, 16, 17],
                 metadata.CLASS_AUTHOR_ABSENT: [], metadata.CLASS_UNCLASSIFIED: []})

    monkeypatch.setattr(metadata, "_name_state", forced)
    findings, _skips, _summary = metadata.evaluate(subset)  # 无源
    assert findings, "无源却产 finding = 在猜（变异必须被抓）"


def test_mutation_codepage_zero_check_is_caught(monkeypatch):
    """变异 3：把码页判据退化成"ulCodePageRange1 == 0 就报" → F5 反例必红。"""
    subset, source, _body = _fixture("F5")
    monkeypatch.setattr(metadata, "_codepage_findings",
                        lambda os2, cps: ([] if os2["ulCodePageRange"][0] else
                                          metadata.finding(
                                              metadata.MODULE, metadata.CODE_CODEPAGE_LATIN1,
                                              "error", "cp1:latin1", "x", spec_ref="x")))
    findings, _skips, _summary = metadata.evaluate(subset, source_path=source)
    assert [f["code"] for f in findings if f["code"] == metadata.CODE_CODEPAGE_LATIN1] == []


def test_mutation_unicode_range_zero_becomes_false_positive(monkeypatch):
    """变异 4：加一条"ur1 == 0 即矛盾"的判定 → F6 的反例守护必红。

    这条变异**复现初稿的假阳性**（`data/README.md` §七 #3）：如果实现这么做，
    F6 会多出一条 `UNICODE_RANGE_CONTRADICTION`。
    """
    subset, source, body = _fixture("F6")
    original = metadata._unicode_range_findings

    def naive(os2, codepoints):
        out, unknown = original(os2, codepoints)
        if os2["ulUnicodeRange"][0] == 0:
            out = out + [metadata.finding(
                metadata.MODULE, "UNICODE_RANGE_CONTRADICTION", "warn", "ur1:zero",
                "ur1 为零", spec_ref="x")]
        return out, unknown

    monkeypatch.setattr(metadata, "_unicode_range_findings", naive)
    findings, _skips, _summary = metadata.evaluate(subset, source_path=source)
    got = set((f["code"], f["primary_key"]) for f in findings)
    absent = [(i["code"], i["primary_key"])
              for i in body["expect"]["expected_absent_findings"]]
    assert any(item in got for item in absent), "变异必须让 golden 的 absent 项真的出现"


def test_mutation_char_index_reverse_direction_is_caught(tmp_path, monkeypatch):
    """变异 5：把"留白"也判成矛盾 → 留白样本必红（说明判据方向是承重的）。"""
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"})
    ok = str(tmp_path / "ok.ttf")

    def widen(raw, ofs):
        struct.pack_into(">H", raw, ofs + 64, 0x0020)
        struct.pack_into(">H", raw, ofs + 66, 0x2000)

    _patch_table(path, ok, "OS/2", widen)

    original = metadata._char_index_findings

    def symmetric(os2, codepoints):
        out, judged = original(os2, codepoints)
        bmp = [cp for cp in codepoints if cp <= 0xFFFE]
        if bmp and int(os2["usFirstCharIndex"]) < min(bmp):
            out = out + [metadata.finding(
                metadata.MODULE, metadata.CODE_CHAR_INDEX, "warn", "usFirstCharIndex",
                "留白也算", spec_ref="x")]
        return out, judged

    monkeypatch.setattr(metadata, "_char_index_findings", symmetric)
    findings, _skips, _summary = metadata.evaluate(ok)
    assert [f["code"] for f in findings if f["code"] == metadata.CODE_CHAR_INDEX]


def test_mutation_maxp_using_glyph_order_is_caught(tmp_path, monkeypatch):
    """变异 6：改用 `getGlyphOrder()` 当"独立量" → 改坏 `maxp` 的样本判不出来。"""
    path = str(tmp_path / "s.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"})
    bad = str(tmp_path / "bad.ttf")
    _patch_table(path, bad, "maxp",
                 lambda raw, ofs: struct.pack_into(">H", raw, ofs + 4, 9))

    monkeypatch.setattr(sfnt, "measured_glyph_count",
                        lambda font: len(font.getGlyphOrder()))
    findings, _skips, _summary = metadata.evaluate(bad)
    assert [f for f in findings if f["code"] == metadata.CODE_MAXP_MISMATCH] == [], \
        "用 getGlyphOrder() 当独立量时，这条判据必然失效（变异被抓）"


def test_mutation_spec_ref_drift_is_caught(monkeypatch):
    """变异 7：改 `SPEC_REF` 措辞 → 对账判据必红。"""
    monkeypatch.setattr(metadata, "SPEC_REF", "data/README §6.99")
    with pytest.raises(AssertionError):
        test_spec_ref_matches_data_readme_section()


def test_metadata_is_no_longer_a_skeleton():
    """M5 已实现：`metadata` 不再走骨架出口（反向判据，防"翻完 ✅ 又退回骨架"）。"""
    text = _read("src/subsetaudit/metadata.py")
    assert "skeleton_result(" not in text
    assert "module_not_implemented_in_m0" not in text


def test_summary_does_not_take_the_conclusions_key():
    """K15：`summary["conclusions"]` 仍归 `license-gate` 独占 —— `metadata` 用 `summary["metadata"]`。"""
    subset, source, _body = _fixture("F5")
    _findings, _skips, summary = metadata.evaluate(subset, source_path=source)
    assert "metadata" in summary
    assert "conclusions" not in summary
    assert canonical.MODULES.count("metadata") == 1
