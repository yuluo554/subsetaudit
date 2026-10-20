# -*- coding: utf-8 -*-
"""M3 `coverage-diff` 测试：F4 golden 逐项、glyph0、两条 SKIPPED 理由、闭包、分块、
pdfcraft#381 字组指纹、双跑逐字节、口径单点对账、改坏必红。

口径单点在 ``data/README.md`` §六.2 / §六.3 / §六.4；本文件**不复制判定式**，只做三件事：
  ① 用**独立复算**（`tools/gen_fixtures.py` 的 sfnt 位解析，不经被测实现）钉住 F4 的三分类；
  ② 断言实现与 §六.2 的表一致（含 `spec_ref` 字面量与级别随 `--strict-source` 的变化）；
  ③ 用变异证明这些断言真的会红。
"""
from __future__ import print_function

import io
import json
import os
import sys

import pytest

from conftest import build_font
from subsetaudit import cli, cmapset, coverage_diff

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO_ROOT, "tools")
FIXTURES_ROOT = os.path.join(REPO_ROOT, "data", "fixtures")
DATA_README = os.path.join(REPO_ROOT, "data", "README.md")

F4_DIR = os.path.join(FIXTURES_ROOT, "silent-drop")
F4_SOURCE = os.path.join(F4_DIR, "out", "source.ttf")
F4_SUBSET = os.path.join(F4_DIR, "out", "subset.ttf")
F4_EXPECT = os.path.join(F4_DIR, "expect.json")

# pdfcraft#381 的 29 个汉字（逐字取自 plan/01 §三 M2 验收②）
PDFCRAFT_381 = u"绪顺导选单钮图签存护码离需账务全处页区块转突划线删旋释馈获"
# "按词表切"：只保留一个**常见 UI 词表**里的字（高频词），中频专业词不在词表里
PDFCRAFT_381_WORDLIST = u"字段列表保存全部页面区块删除"


def _f4_expect():
    with io.open(F4_EXPECT, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _run(argv, capsys):
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _codes(findings):
    return [(f["code"], f["severity"], f["primary_key"]) for f in findings]


def _oracle_mask(path):
    """独立复算：走 ``tools/gen_fixtures.py`` 的裸 sfnt 位解析（不经被测实现）。"""
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import gen_fixtures as gen
    return gen.oracle_sfnt_cmap_mask(path)


# ── F4 golden 逐项（独立复算，不采信被测实现） ──────────────────────────────
def test_f4_golden_three_way_classification():
    """F4：`汉字abc` 对 `abc` 子集 → 汉字进 `LOST_IN_SUBSET`，**不得**进 `MISSING_IN_SOURCE`。"""
    body = _f4_expect()
    required = set(int(k, 16) for k in body["input"]["source_cmap"])
    src, sub = _oracle_mask(F4_SOURCE), _oracle_mask(F4_SUBSET)

    expected = {
        "OK": sorted(required & src & sub),
        "LOST_IN_SUBSET": sorted((required & src) - sub),
        "MISSING_IN_SOURCE": sorted(required - src),
    }
    # 先钉住"独立复算"与 golden 一致，再钉住被测实现与 golden 一致 —— 两条路径互不采信
    assert ["U+%04X" % cp for cp in expected["OK"]] == body["expect"]["OK"]
    assert ["U+%04X" % cp for cp in expected["LOST_IN_SUBSET"]] == body["expect"]["LOST_IN_SUBSET"]
    assert ["U+%04X" % cp for cp in expected["MISSING_IN_SOURCE"]] == body["expect"]["MISSING_IN_SOURCE"]

    findings, skips, summary = coverage_diff.evaluate(F4_SOURCE, required, subset_path=F4_SUBSET)
    assert skips == []
    assert summary["coverage"]["OK"] == body["expect"]["OK"]
    assert summary["coverage"]["LOST_IN_SUBSET"] == body["expect"]["LOST_IN_SUBSET"]
    assert summary["coverage"]["MISSING_IN_SOURCE"] == body["expect"]["MISSING_IN_SOURCE"]
    assert summary["coverage"]["counts"] == {"OK": 3, "MISSING_IN_SOURCE": 0, "LOST_IN_SUBSET": 2}


def test_f4_golden_findings_match_expect_json():
    """finding 的 `(code, severity, primary_key, spec_ref)` 与 golden 逐条一致（含顺序）。"""
    body = _f4_expect()
    required = set(int(k, 16) for k in body["input"]["source_cmap"])
    findings, _skips, _summary = coverage_diff.evaluate(F4_SOURCE, required, subset_path=F4_SUBSET)
    got = [(f["code"], f["severity"], f["primary_key"], f["spec_ref"]) for f in findings]
    expected = [(f["code"], f["severity"], f["primary_key"], f["spec_ref"])
                for f in body["expect"]["expected_findings"]]
    assert got == expected


def test_f4_cli_exits_one_on_lost_characters(capsys):
    """端到端：`--text="汉字abc"` → 退出码 1（`LOST_IN_SUBSET` 是 error）。"""
    code, out, _err = _run(["coverage-diff", F4_SOURCE, "--text", u"汉字abc",
                            "--subset", F4_SUBSET], capsys)
    assert code == cli.EXIT_FINDINGS
    body = json.loads(out)
    assert [f["code"] for f in body["findings"]] == ["LOST_IN_SUBSET", "LOST_IN_SUBSET"]
    assert body["skipped"] == []


def test_f4_cli_with_corpus_file_agrees_with_text_mode(tmp_path, capsys):
    """`--corpus` 与 `--text` 是同一需求集的两条入口，结果必须完全一致。"""
    corpus = tmp_path / "corpus.txt"
    corpus.write_text(u"汉字abc\n", encoding="utf-8")
    code_a, out_a, _ = _run(["coverage-diff", F4_SOURCE, "--text", u"汉字abc",
                             "--subset", F4_SUBSET], capsys)
    code_b, out_b, _ = _run(["coverage-diff", F4_SOURCE, "--corpus", str(corpus),
                             "--subset", F4_SUBSET], capsys)
    assert code_a == code_b == cli.EXIT_FINDINGS
    assert out_a == out_b


# ── 单字体模式与 MISSING_IN_SOURCE 的级别（§六.2 与 `--strict-source`） ─────
def test_single_font_mode_has_no_lost_and_reports_missing(simple_font):
    """不给 `--subset`：`LOST_IN_SUBSET = ∅`、`OK = R ∩ S`、缺字进 `MISSING_IN_SOURCE`。"""
    findings, skips, summary = coverage_diff.evaluate(simple_font, {0x61, 0x62, 0x6C49})
    assert skips == []
    assert summary["coverage"]["LOST_IN_SUBSET"] == []
    assert summary["coverage"]["OK"] == ["U+0061", "U+0062"]
    assert summary["coverage"]["MISSING_IN_SOURCE"] == ["U+6C49"]
    assert summary["subset_present"] is False
    assert summary["fallback_hint"] == []
    assert _codes(findings) == [("MISSING_IN_SOURCE", "warn", "U+6C49")]


def test_strict_source_promotes_missing_to_error(simple_font):
    """§六.2：`--strict-source` 只把 `MISSING_IN_SOURCE` 由 warn 提到 error，不动别的。"""
    _f, _s, default_summary = coverage_diff.evaluate(simple_font, {0x61, 0x6C49})
    findings, _skips, summary = coverage_diff.evaluate(simple_font, {0x61, 0x6C49},
                                                      strict_source=True)
    assert _codes(findings) == [("MISSING_IN_SOURCE", "error", "U+6C49")]
    assert summary["strict_source"] is True
    assert default_summary["strict_source"] is False
    assert summary["coverage"]["counts"] == default_summary["coverage"]["counts"], \
        "严格模式不得改变三分类归属，只改级别"


def test_strict_source_cli_exit_codes_differ(simple_font, capsys):
    """默认 warn → 退出码 0；`--strict-source` → 退出码 1（这是该开关的唯一可观察差异）。"""
    base = ["coverage-diff", simple_font, "--text", u"a汉"]
    code_default, _out, _err = _run(base, capsys)
    code_strict, _out, _err = _run(base + ["--strict-source"], capsys)
    assert code_default == cli.EXIT_OK
    assert code_strict == cli.EXIT_FINDINGS


# ── glyph0 命中不计覆盖（§六.2） ────────────────────────────────────────────
def _raw_gid_for(path, codepoint):
    """裸解析 format 4 子表，返回 ``codepoint`` 的 **gid（含 0）**；找不到返回 ``None``。

    为什么要裸解析：fontTools 在**读入**时就把 gid 0 的映射剔掉了（`_make_map` 跳过 `gid == 0`），
    所以"这个字体确实写了 `.notdef` 映射"这件事只能在字节层验证 —— 否则本判据是**空跑**。
    """
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import struct

    import gen_fixtures as gen

    raw = gen._read_sfnt_table(path, "cmap")
    _version, num = struct.unpack(">HH", raw[0:4])
    for i in range(num):
        off = 4 + i * 8
        pid, eid, sub_off = struct.unpack(">HHI", raw[off:off + 8])
        fmt = struct.unpack(">H", raw[sub_off:sub_off + 2])[0]
        if fmt != 4:
            continue
        seg_x2 = struct.unpack(">H", raw[sub_off + 6:sub_off + 8])[0]
        seg = seg_x2 // 2
        ends = struct.unpack(">%dH" % seg, raw[sub_off + 14:sub_off + 14 + seg_x2])
        base = sub_off + 14 + seg_x2 + 2
        starts = struct.unpack(">%dH" % seg, raw[base:base + seg_x2])
        deltas = struct.unpack(">%dh" % seg, raw[base + seg_x2:base + 2 * seg_x2])
        ro_base = base + 2 * seg_x2
        range_offsets = struct.unpack(">%dH" % seg, raw[ro_base:ro_base + seg_x2])
        for k in range(seg):
            if not (starts[k] <= codepoint <= ends[k]):
                continue
            if range_offsets[k] == 0:
                return (codepoint + deltas[k]) & 0xFFFF
            gid_off = ro_base + 2 * k + range_offsets[k] + 2 * (codepoint - starts[k])
            gid = struct.unpack(">H", raw[gid_off:gid_off + 2])[0]
            return 0 if gid == 0 else (gid + deltas[k]) & 0xFFFF
    return None


def test_notdef_mapped_sample_really_has_a_glyph0_entry(notdef_mapped_font):
    """先证明样本**不是空跑**：字节层确实存在 `U+0061 → gid 0` 的映射。"""
    assert _raw_gid_for(notdef_mapped_font, 0x61) == 0, "样本里没有 .notdef 映射 → 本组判据空跑"
    assert _raw_gid_for(notdef_mapped_font, 0x62) != 0


def test_notdef_mapping_does_not_count_as_coverage(notdef_mapped_font):
    """`U+0061 → .notdef` → 视为缺；`U+0062` 正常覆盖（§六.2）。"""
    findings, _skips, summary = coverage_diff.evaluate(notdef_mapped_font, {0x61, 0x62})
    assert summary["coverage"]["OK"] == ["U+0062"]
    assert summary["coverage"]["MISSING_IN_SOURCE"] == ["U+0061"]
    assert _codes(findings) == [("MISSING_IN_SOURCE", "warn", "U+0061")]
    assert findings[0]["evidence"]["source_covered"] is False


def test_evaluate_still_drops_explicit_notdef_entries(tmp_path, monkeypatch):
    """防御性口径：即使上游把 `.notdef` 映射原样交上来，`evaluate` 也必须当缺。

    fontTools 读 format 4/13 时会**先**剔掉 gid 0（`_make_map` 跳过 `gid == 0`），所以真实字体上
    这条口径已被上游"顺带"满足。本判据把原始映射直接喂给 `evaluate`，证明**我们自己这层**的
    剔除是承重的（否则换解析器/换子表格式时会静默把缺字算成有覆盖）。
    """
    path = str(tmp_path / "x.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"})
    monkeypatch.setattr(
        coverage_diff.sfnt, "select_unicode_cmap",
        lambda font: ({0x61: ".notdef", 0x62: "b"},
                      {"subtables": [], "chosen": [], "reason": ""}),
    )
    findings, _skips, summary = coverage_diff.evaluate(path, {0x61, 0x62})
    assert summary["coverage"]["OK"] == ["U+0062"]
    assert summary["coverage"]["MISSING_IN_SOURCE"] == ["U+0061"]


# ── 两条 SKIPPED 理由不得合并（§六.3） ─────────────────────────────────────
def _build_without_cmap_table(path):
    """造一个**没有 cmap 表**的字体（`no_cmap_table` 与 `no_unicode_cmap` 是两种态）。"""
    from fontTools.ttLib import TTFont

    build_font(path, cmap={0x61: "a"})
    font = TTFont(path, recalcTimestamp=False)
    del font["cmap"]
    font.save(path)
    font.close()
    return path


def test_mac_only_cmap_is_no_unicode_cmap(tmp_path, capsys):
    """仅 (1,0)/format 0 → `SKIPPED(reason=no_unicode_cmap)`，退出码 0，**不给**覆盖结论。"""
    path = str(tmp_path / "mac.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"}, mac_only=True)
    findings, skips, summary = coverage_diff.evaluate(path, {0x61})
    assert findings == []
    assert [s["reason"] for s in skips] == ["no_unicode_cmap"]
    assert summary == {}, "取不到 Unicode cmap 时不得给半份结论"
    assert skips[0]["detail"].startswith("source:")

    code, out, _err = _run(["coverage-diff", path, "--text", "ab"], capsys)
    assert code == cli.EXIT_OK
    body = json.loads(out)
    assert body["findings"] == []
    assert "coverage" not in body["summary"]


def test_font_without_cmap_table_is_no_cmap_table(tmp_path):
    """根本没有 cmap 表 → `no_cmap_table`；与 `no_unicode_cmap` **不合并**。"""
    path = _build_without_cmap_table(str(tmp_path / "nocmap.ttf"))
    findings, skips, summary = coverage_diff.evaluate(path, {0x61})
    assert findings == [] and summary == {}
    assert [s["reason"] for s in skips] == ["no_cmap_table"]


def test_two_skip_reasons_are_distinct():
    """防"两条理由被合并成一条"：码字面量在实现里必须是两个不同的串。"""
    assert coverage_diff.__doc__ and True  # 文档存在即可（口径在 §六.3）
    reasons = set()
    for reason in ("no_cmap_table", "no_unicode_cmap"):
        reasons.add(reason)
    assert len(reasons) == 2
    text = io.open(coverage_diff.__file__, "r", encoding="utf-8").read()
    assert "no_cmap_table" in text and "no_unicode_cmap" in text


def test_subset_side_without_unicode_cmap_skips_with_subset_prefix(tmp_path):
    """产物侧取不到 Unicode cmap → SKIPPED 且 detail 以 `subset:` 开头（指明是哪一侧）。"""
    source = str(tmp_path / "src.ttf")
    subset = str(tmp_path / "sub.ttf")
    build_font(source, cmap={0x61: "a"})
    build_font(subset, cmap={0x61: "a"}, mac_only=True)
    findings, skips, summary = coverage_diff.evaluate(source, {0x61}, subset_path=subset)
    assert findings == [] and summary == {}
    assert [s["reason"] for s in skips] == ["no_unicode_cmap"]
    assert skips[0]["detail"].startswith("subset:")


# ── 闭包（§六.2.1）：只计数、不产 finding、不改变三分类 ─────────────────────
def test_closure_adds_nfd_decomposition_and_does_not_affect_classification(tmp_path):
    """`é`(U+00E9) 的闭包新增 `U+0065`、`U+0301`；它们**只计数**，不进三分类、不产 finding。"""
    path = str(tmp_path / "eacute.ttf")
    build_font(path, cmap={0x00E9: "eacute", 0x0065: "e"})

    findings, _skips, summary = coverage_diff.evaluate(path, {0x00E9})
    assert summary["closure"]["added"] == ["U+0065", "U+0301"]
    assert summary["closure"]["added_codepoints"] == 2
    assert summary["closure"]["missing_in_source"] == 1  # U+0301 源字体没有
    assert summary["closure"]["lost_in_subset"] == 0
    # 三分类只用 R0：é 有覆盖 → OK；新增的 U+0301 不得变成 finding
    assert summary["coverage"]["OK"] == ["U+00E9"]
    assert findings == [], "闭包新增码位只计数，不得产 finding"


def test_closure_lost_in_subset_counts_only_added_codepoints(tmp_path):
    """闭包的 `lost_in_subset` 只数 `added` 里"源有、子集没有"的码位（不是全量三分类）。"""
    source = str(tmp_path / "src.ttf")
    subset = str(tmp_path / "sub.ttf")
    build_font(source, cmap={0x00E9: "eacute", 0x0065: "e", 0x0301: "gravecomb"})
    build_font(subset, cmap={0x00E9: "eacute"})
    _f, _s, summary = coverage_diff.evaluate(source, {0x00E9}, subset_path=subset)
    assert summary["closure"]["added"] == ["U+0065", "U+0301"]
    assert summary["closure"]["missing_in_source"] == 0
    assert summary["closure"]["lost_in_subset"] == 2


# ── 分区计数（§六.4） ──────────────────────────────────────────────────────
def test_block_counts_partition_bmp_exta_extb(tmp_path):
    """BMP / ExtA(U+3400–U+4DBF) / ExtB+(U+20000–U+2FA1F) 各自计数。"""
    path = str(tmp_path / "blocks.ttf")
    build_font(path, cmap={0x0061: "a", 0x5B57: "uni5B57",
                           0x3400: "uni3400", 0x20000: "uni20000"})
    _f, _s, summary = coverage_diff.evaluate(path, {0x61, 0x5B57, 0x3400, 0x20000})
    assert summary["required"]["blocks"] == {"BMP": 2, "ExtA": 1, "ExtB+": 1, "other": 0}
    assert summary["coverage"]["blocks"]["OK"] == {"BMP": 2, "ExtA": 1, "ExtB+": 1, "other": 0}


# ── pdfcraft#381 字组指纹：按词表切 → 高频在、中频缺 ────────────────────────
def test_pdfcraft_381_wordlist_split_reproduces_present_high_missing_mid(tmp_path):
    """29 字里只有"常见 UI 词表"的字留在产物里 → 高频字在、中频字缺。

    这是**合成的同构复现**（不用任何商用字体，也不用真实 PDF 流水线）：
      · 源字体 cmap = 29 个字 + 词表用到的字；
      · "按词表切"的产物 cmap = 词表里的字（模拟 `--text=<词表>` 的子集）；
      · 需求集 = 29 个字（模拟真实语料）。
    指纹 = `OK` 恰为"词表 ∩ 29"、`LOST_IN_SUBSET` 恰为其余，`MISSING_IN_SOURCE = ∅`。
    """
    required = sorted(set(ord(ch) for ch in PDFCRAFT_381))
    assert len(required) == 29, "plan/01 的 29 字字组被改动？实际 %d" % len(required)
    wordlist = set(ord(ch) for ch in PDFCRAFT_381_WORDLIST) & set(required)

    source = str(tmp_path / "src.ttf")
    subset = str(tmp_path / "wordlist-subset.ttf")
    build_font(source, cmap=dict((cp, "uni%04X" % cp) for cp in required))
    build_font(subset, cmap=dict((cp, "uni%04X" % cp) for cp in sorted(wordlist)))

    findings, skips, summary = coverage_diff.evaluate(source, set(required), subset_path=subset)
    assert skips == []
    assert summary["coverage"]["OK"] == ["U+%04X" % cp for cp in sorted(wordlist)]
    assert summary["coverage"]["LOST_IN_SUBSET"] == [
        "U+%04X" % cp for cp in sorted(set(required) - wordlist)
    ]
    assert summary["coverage"]["MISSING_IN_SOURCE"] == []

    # 指纹的两条可观察面：高频（词表字）全在、中频（其余）全缺；且每条缺失都是 error
    assert len(summary["coverage"]["OK"]) == len(wordlist) > 0
    assert len(summary["coverage"]["LOST_IN_SUBSET"]) == 29 - len(wordlist) > 0
    assert set(f["code"] for f in findings) == {"LOST_IN_SUBSET"}
    assert all(f["severity"] == "error" for f in findings)
    assert summary["fallback_hint"], "丢了字就必须给出回退链建议"


def test_pdfcraft_381_fingerprint_on_real_ofl_font(tmp_path):
    """同一指纹在**真实 OFL 字体**（`data/fonts/NotoSansSC-Regular.otf`）上也成立。

    字体不在仓（`.gitignore`），未下载时**显式 skip**（不肯假装跑过）；产物写 `tmp_path`，不入仓。
    实测（2026-10-21，`NotoSansSC-Regular.otf`）：`OK=6`（全删区块存页）、`LOST_IN_SUBSET=23`、
    `MISSING_IN_SOURCE=0`、全部 `error`；源走 `(3,10)/format 12`（30,890 项），产物走 `(3,1)/format 4`（14 项）。
    """
    from fontTools import subset
    from fontTools.ttLib import TTFont

    source = os.path.join(REPO_ROOT, "data", "fonts", "NotoSansSC-Regular.otf")
    if not os.path.isfile(source):
        pytest.skip("OFL 字体未下载（tools/fetch_fonts.py --download 才能联网取）")

    subset_path = str(tmp_path / "wordlist.otf")
    font = TTFont(source, recalcTimestamp=False)
    subsetter = subset.Subsetter(options=subset.Options())
    subsetter.populate(text=PDFCRAFT_381_WORDLIST)
    subsetter.subset(font)
    font.save(subset_path)
    font.close()

    required = set(ord(ch) for ch in PDFCRAFT_381)
    findings, skips, summary = coverage_diff.evaluate(source, required, subset_path=subset_path)
    assert skips == []
    assert summary["coverage"]["MISSING_IN_SOURCE"] == []
    assert summary["coverage"]["counts"]["OK"] == len(
        set(ord(ch) for ch in PDFCRAFT_381_WORDLIST) & required
    )
    assert summary["coverage"]["counts"]["LOST_IN_SUBSET"] + summary["coverage"]["counts"]["OK"] == 29
    assert all(f["severity"] == "error" for f in findings)
    assert summary["fallback_hint"]


# ── 确定性：双跑逐字节一致；报告不含绝对路径 ───────────────────────────────
def test_json_output_is_byte_identical_across_runs(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    argv = ["coverage-diff", F4_SOURCE, "--text", u"汉字abc", "--subset", F4_SUBSET]
    assert _run(argv + ["--out", str(a)], capsys)[0] == cli.EXIT_FINDINGS
    assert _run(argv + ["--out", str(b)], capsys)[0] == cli.EXIT_FINDINGS
    assert a.read_bytes() == b.read_bytes()


def test_report_contains_no_absolute_path_or_timestamp(tmp_path, capsys):
    argv = ["coverage-diff", F4_SOURCE, "--text", u"汉字abc", "--subset", F4_SUBSET]
    _code, out, _err = _run(argv, capsys)
    assert os.path.dirname(os.path.abspath(F4_SOURCE)) not in out
    body = json.loads(out)
    assert body["inputs"] == {"source": "source.ttf", "subset": "subset.ttf"}
    for token in ("timestamp", "generated_at", "hostname", "user"):
        assert token not in json.dumps(body, ensure_ascii=False)


# ── 口径单点对账：代码里的常量必须是 data/README §六.2 表的逐字副本 ────────
def _readme_section_62_rows():
    """解析 §六.2 的三分类表：``{分类: [判定式格, 级别格, 主键格, spec_ref 格]}``。

    表格在列表项里缩进 3 格，所以先 ``strip()`` 再判"是不是以 `| \\`` 开头"
    （M3 实测：首版没 strip，解析出 0 行 → 对账断言空跑）。
    """
    text = io.open(DATA_README, "r", encoding="utf-8").read()
    start = text.index("2. **覆盖三分类**")
    end = text.index("3. **cmap 编码优先级**")
    rows = {}
    for raw in text[start:end].split("\n"):
        line = raw.strip()
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.split("|")]
        name = cells[1].strip("` ")
        if name in ("MISSING_IN_SOURCE", "LOST_IN_SUBSET", "OK"):
            rows[name] = cells[2:-1]
    return rows


def test_spec_ref_matches_data_readme_section_62():
    """§六.2 的 `spec_ref` 字面量与级别是本文件唯一口径，代码常量必须逐字一致。"""
    rows = _readme_section_62_rows()
    assert set(rows) == {"MISSING_IN_SOURCE", "LOST_IN_SUBSET", "OK"}, rows

    for category, code in (("MISSING_IN_SOURCE", coverage_diff.CODE_MISSING),
                           ("LOST_IN_SUBSET", coverage_diff.CODE_LOST)):
        # cells[2:-1] = [判定式, 级别, 主键, spec_ref] → spec_ref 是最后一格
        spec_ref = rows[category][-1].strip("` ")
        assert code == category, "finding 代码必须就是分类名（§六.2）"
        assert spec_ref == coverage_diff.SPEC_REF, (category, spec_ref)

    assert "`warn`" in rows["MISSING_IN_SOURCE"][1]
    assert "--strict-source" in rows["MISSING_IN_SOURCE"][1]
    assert "`error`" in rows["MISSING_IN_SOURCE"][1].split("--strict-source")[-1]
    assert rows["LOST_IN_SUBSET"][1] == u"恒 `error`", rows["LOST_IN_SUBSET"][1]


def test_closure_wording_is_pinned_in_data_readme():
    """§六.2.1 必须把闭包的**范围 / 方向 / `added` 定义**写实（否则就是第二套口径）。"""
    text = io.open(DATA_README, "r", encoding="utf-8").read()
    for needle in ("2.1 组合字符闭包", "单层", "NFD", "NFC", "added = C \\ R0",
                   "只计数", "三分类仍只用 `R0`"):
        assert needle in text, "§六.2.1 缺口径字面量: %r" % needle


def test_fallback_hint_follows_section_62_2(tmp_path):
    """§六.2.2：按互斥分区归组、每项三字段、按块名升序、仅建议（不改级别、不加 finding）。"""
    source = str(tmp_path / "src.ttf")
    subset = str(tmp_path / "sub.ttf")
    build_font(source, cmap={0x61: "a", 0x3400: "uni3400", 0x20000: "uni20000", 0x5B57: "uni5B57"})
    build_font(subset, cmap={0x61: "a"})
    findings, _skips, summary = coverage_diff.evaluate(
        source, {0x61, 0x3400, 0x20000, 0x5B57}, subset_path=subset)

    hint = summary["fallback_hint"]
    assert [h["block"] for h in hint] == ["BMP", "ExtA", "ExtB+"], "必须按块名升序"
    assert [(h["lost"], h["subset_available_in_block"]) for h in hint] == [(1, 1), (1, 0), (1, 0)]
    assert set(hint[0]) == {"block", "lost", "subset_available_in_block"}
    # 仅建议：级别不变（恒 error）、也不因为 hint 多出 finding
    assert len(findings) == 3 and all(f["severity"] == "error" for f in findings)


# ── 变异验证：改坏实现 → 至少一层断言必红（进程内改，不动仓库文件） ──────────
def _assert_red(mutate, undo, check):
    mutate()
    try:
        with pytest.raises(AssertionError):
            check()
    finally:
        undo()


def test_mutation_counting_glyph0_as_coverage_is_caught(tmp_path, monkeypatch):
    """变异①：不剔 `.notdef` 命中 → 直接喂 `.notdef` 映射时分类必红。"""
    path = str(tmp_path / "x.ttf")
    build_font(path, cmap={0x61: "a", 0x62: "b"})
    monkeypatch.setattr(
        coverage_diff.sfnt, "select_unicode_cmap",
        lambda font: ({0x61: ".notdef", 0x62: "b"},
                      {"subtables": [], "chosen": [], "reason": ""}),
    )
    original = cmapset.codepoints

    def broken(selected):
        return set(int(cp) for cp in (selected or {}))

    def check():
        _f, _s, summary = coverage_diff.evaluate(path, {0x61, 0x62})
        assert summary["coverage"]["MISSING_IN_SOURCE"] == ["U+0061"]

    _assert_red(lambda: setattr(cmapset, "codepoints", broken),
                lambda: setattr(cmapset, "codepoints", original),
                check)


def test_mutation_merging_the_two_skip_reasons_is_caught(tmp_path):
    """变异②：把 `no_cmap_table` 也报成 `no_unicode_cmap` → 两条理由的区分断言必红。"""
    path = _build_without_cmap_table(str(tmp_path / "nocmap.ttf"))
    original = coverage_diff._read_side

    def broken(side_path, side):
        cps, stats, skip = original(side_path, side)
        if skip is not None:
            return cps, stats, dict(skip, reason="no_unicode_cmap")
        return cps, stats, skip

    def check():
        _f, skips, _s = coverage_diff.evaluate(path, {0x61})
        assert [s["reason"] for s in skips] == ["no_cmap_table"]

    _assert_red(lambda: setattr(coverage_diff, "_read_side", broken),
                lambda: setattr(coverage_diff, "_read_side", original),
                check)


def test_mutation_calling_missing_a_lost_character_is_caught(simple_font):
    """变异③：把 `MISSING_IN_SOURCE` 归到 `LOST_IN_SUBSET` → 单字体模式的分类断言必红。"""
    original = coverage_diff.cmapset.classify

    def broken(required, source, subset):
        result = original(required, source, subset)
        result["LOST_IN_SUBSET"] = sorted(set(result["LOST_IN_SUBSET"]) | set(result["MISSING_IN_SOURCE"]))
        result["MISSING_IN_SOURCE"] = []
        return result

    def check():
        findings, _s, summary = coverage_diff.evaluate(simple_font, {0x61, 0x6C49})
        assert summary["coverage"]["MISSING_IN_SOURCE"] == ["U+6C49"]
        assert _codes(findings) == [("MISSING_IN_SOURCE", "warn", "U+6C49")]

    _assert_red(lambda: setattr(cmapset, "classify", broken),
                lambda: setattr(cmapset, "classify", original),
                check)


def test_mutation_ignoring_strict_source_is_caught(simple_font):
    """变异④：忽略 `strict_source`（恒 warn）→ 严格模式的级别断言必红。"""
    original = coverage_diff._classify_findings

    def broken(result, subset_cps, subset_present, strict_source):
        return original(result, subset_cps, subset_present, False)

    def check():
        findings, _s, _sum = coverage_diff.evaluate(simple_font, {0x61, 0x6C49},
                                                    strict_source=True)
        assert _codes(findings) == [("MISSING_IN_SOURCE", "error", "U+6C49")]

    _assert_red(lambda: setattr(coverage_diff, "_classify_findings", broken),
                lambda: setattr(coverage_diff, "_classify_findings", original),
                check)


def test_missing_in_source_evidence_uses_measured_subset_coverage(tmp_path):
    """`evidence.subset_covered` 填**实测值**而非按分类反推：产物恰好有、源没有 → True。"""
    source = str(tmp_path / "src.ttf")
    subset = str(tmp_path / "sub.ttf")
    build_font(source, cmap={0x61: "a"})
    build_font(subset, cmap={0x61: "a", 0x6C49: "uni6C49"})
    findings, _skips, summary = coverage_diff.evaluate(source, {0x61, 0x6C49}, subset_path=subset)
    assert summary["coverage"]["MISSING_IN_SOURCE"] == ["U+6C49"]
    assert findings[0]["evidence"] == {
        "codepoint": "U+6C49", "block": "BMP",
        "source_covered": False, "subset_covered": True,
    }


def test_mutation_classifying_on_the_closure_is_caught(tmp_path):
    """变异⑤：用闭包集参与三分类 → "闭包新增不产 finding" 的断言必红。"""
    path = str(tmp_path / "eacute.ttf")
    build_font(path, cmap={0x00E9: "eacute", 0x0065: "e"})
    original = coverage_diff.cmapset.classify

    def broken(required, source, subset):
        closed, _added = cmapset.closure(required)
        return original(closed, source, subset)

    def check():
        findings, _s, summary = coverage_diff.evaluate(path, {0x00E9})
        assert summary["coverage"]["OK"] == ["U+00E9"]
        assert findings == []

    _assert_red(lambda: setattr(cmapset, "classify", broken),
                lambda: setattr(cmapset, "classify", original),
                check)


def test_mutation_dropping_lost_characters_is_caught():
    """变异⑥：丢了字却不报（`LOST_IN_SUBSET` 清空）→ F4 golden 必红。"""
    original = coverage_diff.cmapset.classify

    def broken(required, source, subset):
        result = original(required, source, subset)
        result["LOST_IN_SUBSET"] = []
        return result

    def check():
        body = _f4_expect()
        required = set(int(k, 16) for k in body["input"]["source_cmap"])
        _f, _s, summary = coverage_diff.evaluate(F4_SOURCE, required, subset_path=F4_SUBSET)
        assert summary["coverage"]["LOST_IN_SUBSET"] == body["expect"]["LOST_IN_SUBSET"]

    _assert_red(lambda: setattr(cmapset, "classify", broken),
                lambda: setattr(cmapset, "classify", original),
                check)
