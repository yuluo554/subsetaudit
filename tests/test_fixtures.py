# -*- coding: utf-8 -*-
"""M1 数据层测试：fixture 确定性、`--check` 位级一致、golden 逐项、生成器改坏必红。

口径单点在 ``data/README.md`` §六；本文件只断言，不另立判定式。

三条纪律（``plan/04`` §2）在测试里的落法：
  · **确定性**：同一进程内连跑两次 → 逐字节一致（``test_generator_is_byte_deterministic``）；
  · **golden 只存输入与期望**：``expect.json`` 里不得出现 ``observed_*``；
  · **改坏必红**：真去改一次生成器的输入（fsType / 子集字符集）→ 至少一层断言必红。
"""
from __future__ import print_function

import io
import json
import os
import subprocess
import sys
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO_ROOT, "tools")
GEN = os.path.join(TOOLS, "gen_fixtures.py")
FIXTURES_ROOT = os.path.join(REPO_ROOT, "data", "fixtures")

sys.path.insert(0, TOOLS)

FIXTURE_IDS = ["F1", "F2", "F3", "F4", "F5", "F6"]
NAMES = {
    "F1": "fstype-nosubset",
    "F2": "fstype-multibit-v0",
    "F3": "fstype-multibit-v3",
    "F4": "silent-drop",
    "F5": "metadata-stripped",
    "F6": "codepage-mismatch",
}


def _gen_module():
    import gen_fixtures
    return gen_fixtures


def _run_gen(args, cwd=REPO_ROOT):
    proc = subprocess.run([sys.executable, "-X", "utf8", GEN] + args, cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True)
    return proc.returncode, proc.stdout


def _read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _expect_path(fid):
    return os.path.join(FIXTURES_ROOT, NAMES[fid], "expect.json")


# ── 确定性：同进程连跑两次 → 逐字节一致 ────────────────────────────────────
def test_generator_is_byte_deterministic(tmp_path):
    """`--out` 指两个不同目录，全量生成两次 → 每个文件逐字节一致。

    这直接钉住 ``plan/04`` §2 的"禁时钟"：若生成器读了时钟（``head.created``），
    两次生成就会分叉。先后顺序也固定（先建 A 再建 B），避免"顺序不同"掩盖差异。
    """
    gen = _gen_module()
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    first = gen.generate(FIXTURE_IDS, a, verbose=False)
    second = gen.generate(FIXTURE_IDS, b, verbose=False)
    assert len(first) == len(second) == 6
    rels = gen._text_files_under(a)
    assert len(rels) >= 6
    for rel in rels:
        assert _read_bytes(os.path.join(a, rel)) == _read_bytes(os.path.join(b, rel)), rel


def test_repeated_generation_within_same_process_matches_on_disk(tmp_path):
    """再生成一次到临时目录，必须与**仓库里已生成**的产物逐字节一致。

    这条是"golden 是不是被谁悄悄改过"的判据：任何手改产物 / 手改生成器都会红。
    """
    gen = _gen_module()
    c = str(tmp_path / "c")
    gen.generate(FIXTURE_IDS, c, verbose=False)
    rels = gen._text_files_under(c)
    for rel in rels:
        on_disk = os.path.join(FIXTURES_ROOT, rel)
        assert os.path.isfile(on_disk), "仓库缺产物: %s（先跑 py tools/gen_fixtures.py）" % rel
        assert _read_bytes(os.path.join(c, rel)) == _read_bytes(on_disk), rel


# ── --check 子命令：位级一致 / 缺产物必红 ──────────────────────────────────
def test_check_subcommand_reports_bit_level_equality():
    code, out = _run_gen(["--check"])
    assert code == 0, out
    assert "位级一致" in out


def test_check_subcommand_fails_when_product_is_corrupted(tmp_path):
    """变异自证：把某个产物的一个字节改掉 → `--check` 必须报不一致且 exit 1。

    只改**临时拷贝**（不碰仓库产物），跑完即弃。
    """
    import shutil
    scratch = str(tmp_path / "fixtures")
    shutil.copytree(FIXTURES_ROOT, scratch)
    victim = os.path.join(scratch, NAMES["F1"], "out", "fstype-nosubset.ttf")
    raw = bytearray(_read_bytes(victim))
    raw[-1] ^= 0xFF
    with open(victim, "wb") as fh:
        fh.write(bytes(raw))
    code, out = _run_gen(["--check", "--out", scratch])
    assert code == 1, out
    assert "不一致" in out
    assert "fstype-nosubset.ttf" in out


def test_check_subcommand_fails_when_product_missing(tmp_path):
    """缺产物（没先跑生成器）→ `--check` 报缺失而不是"静默通过"。"""
    import shutil
    scratch = str(tmp_path / "empty")
    shutil.copytree(FIXTURES_ROOT, scratch)
    os.remove(os.path.join(scratch, NAMES["F3"], "out", "fstype-multibit-v3.ttf"))
    code, out = _run_gen(["--check", "--out", scratch])
    assert code == 1, out
    assert "fstype-multibit-v3.ttf" in out


# ── 部分运行纪律：`--only` 不许改写 manifest.json ──────────────────────────
def test_only_run_does_not_write_manifest(tmp_path):
    """部分运行**绝不写** manifest.json；全量运行才写（plan/04 §2 纪律）。

    走 ``main()`` 而不是 ``generate()`` —— 写不写 manifest 是**命令层**的决定，
    判据必须落在命令边界上（否则测的是"我有没有手动调那个函数"）。
    """
    import gen_fixtures as gen

    partial = str(tmp_path / "partial")
    assert gen.main(["--only", "F1", "--out", partial]) == 0
    assert not os.path.exists(os.path.join(partial, "manifest.json")), \
        "部分运行不得写 manifest.json"

    full = str(tmp_path / "full")
    assert gen.main(["--out", full]) == 0
    assert os.path.exists(os.path.join(full, "manifest.json")), "全量运行必须写 manifest.json"

    # 反向判据：部分运行**不得**删改已存在的全集清单
    before = _read_bytes(os.path.join(full, "manifest.json"))
    assert gen.main(["--only", "F3", "--out", full]) == 0
    assert _read_bytes(os.path.join(full, "manifest.json")) == before


def test_manifest_lists_all_six_fixtures():
    path = os.path.join(FIXTURES_ROOT, "manifest.json")
    assert os.path.isfile(path), "manifest.json 缺失（全量生成会写）"
    with io.open(path, "r", encoding="utf-8") as fh:
        body = json.load(fh)
    assert body["version"] == 1
    ids = [f["id"] for f in body["fixtures"]]
    assert ids == FIXTURE_IDS
    for item in body["fixtures"]:
        assert item["bytes"] > 0
        assert len(item["sha256"]) == 64


# ── golden 纪律：expect.json 只存输入与期望 ────────────────────────────────
@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_expect_json_exists_and_has_discipline(fid):
    path = _expect_path(fid)
    assert os.path.isfile(path), path
    with io.open(path, "r", encoding="utf-8") as fh:
        body = json.load(fh)
    assert body["id"] == fid
    assert body["name"] == NAMES[fid]
    assert "input" in body and "expect" in body
    assert "fonttools_version" in body, "golden 必须绑 fontTools 版本（plan/04 §4.3）"

    def walk(node, trail):
        if isinstance(node, dict):
            for key, value in node.items():
                assert not str(key).startswith("observed_"), \
                    "expect.json 不得出现 observed_*: %s/%s" % (trail, key)
                walk(value, trail + "/" + str(key))
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, "%s[%d]" % (trail, i))

    walk(body, fid)


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_fixture_readme_exists(fid):
    path = os.path.join(FIXTURES_ROOT, NAMES[fid], "README.md")
    assert os.path.isfile(path), path
    text = io.open(path, "r", encoding="utf-8").read()
    for needle in ("构造", "真值来源", "重生成"):
        assert needle in text, "%s 缺小节: %s" % (path, needle)


# ── golden 逐项：期望与磁盘上产物实读一致（独立于生成器进程） ──────────────
@pytest.mark.parametrize("fid", ["F1", "F2", "F3"])
def test_fstype_golden_matches_actual_font(fid):
    """用字面量位运算复算 `fsType` 结论，再与产物实读比对（不经生成器）。"""
    from fontTools.ttLib import TTFont

    with io.open(_expect_path(fid), "r", encoding="utf-8") as fh:
        body = json.load(fh)
    font_path = os.path.join(FIXTURES_ROOT, NAMES[fid], "out", body["font"])
    font = TTFont(font_path, lazy=True)
    os2 = font["OS/2"]
    exp = body["expect"]

    assert os2.version == exp["os2_version"]
    assert os2.fsType == int(exp["fsType"], 16)
    assert (os2.fsType & 0x000F) == int(exp["permission_bits"], 16)
    assert ((os2.fsType & 0x0100) == 0) == exp["may_subset"]
    bits = os2.fsType & 0x000F
    assert (bin(bits).count("1") >= 2 and os2.version >= 3) == exp["mutual_exclusion_violation"]
    assert ((os2.fsType & 0xFCF1) != 0) == exp["reserved_bits_set"]
    font.close()


def test_f2_and_f3_differ_only_in_os2_version_and_table_length():
    """F2/F3 是版本分流的唯一判别样本。

    **实测事实**（不是"只差一个字节"）：两处差别 —— `OS/2.version`（0 vs 3），
    以及由版本决定的 OS/2 表长（v0 = 78 B / v3+ = 96 B，`ulCodePageRange` 自 v0 起才有）。
    其余字段与整张 cmap 必须一致；这条断言就是"只改版本、别的一模一样"的证据。
    """
    import gen_fixtures as gen

    a_path = os.path.join(FIXTURES_ROOT, NAMES["F2"], "out", "fstype-multibit-v0.ttf")
    b_path = os.path.join(FIXTURES_ROOT, NAMES["F3"], "out", "fstype-multibit-v3.ttf")
    os2_a = gen._read_sfnt_table(a_path, "OS/2")
    os2_b = gen._read_sfnt_table(b_path, "OS/2")

    assert os2_a[0:2] != os2_b[0:2], "OS/2.version 应不同（0 vs 3）"
    assert len(os2_a) == 78 and len(os2_b) == 96
    # 除 version 与"尾部多出的 ulCodePageRange"之外，前缀必须逐字节一致
    assert os2_a[2:58] == os2_b[2:58], "ulUnicodeRange 及之前字段必须完全一致"

    # cmap 必须逐字节一致 —— 两者只差 OS/2，可见覆盖面无差异
    assert gen._read_sfnt_table(a_path, "cmap") == gen._read_sfnt_table(b_path, "cmap")


def test_f4_golden_lost_in_subset():
    """F4：产物的实际 Unicode 覆盖决定了 `LOST_IN_SUBSET`，与期望逐项一致。"""
    import gen_fixtures as gen

    with io.open(_expect_path("F4"), "r", encoding="utf-8") as fh:
        body = json.load(fh)
    out_dir = os.path.join(FIXTURES_ROOT, NAMES["F4"], "out")
    src = gen.oracle_sfnt_cmap_mask(os.path.join(out_dir, body["input"]["source"]))
    sub = gen.oracle_sfnt_cmap_mask(os.path.join(out_dir, body["font"]))
    required = set(int(k, 16) for k in body["input"]["source_cmap"])

    assert sorted(required - src) == []
    assert sorted(required - sub) == sorted(
        int(x[2:], 16) for x in body["expect"]["LOST_IN_SUBSET"]
    )
    assert sorted(required & src & sub) == sorted(int(x[2:], 16) for x in body["expect"]["OK"])
    assert [] == body["expect"]["MISSING_IN_SOURCE"]


def test_f5_golden_name_metadata():
    """F5：源多语言 + 有 13/14；产物被剥到 0–6 与单一语言。"""
    import gen_fixtures as gen

    with io.open(_expect_path("F5"), "r", encoding="utf-8") as fh:
        body = json.load(fh)
    out_dir = os.path.join(FIXTURES_ROOT, NAMES["F5"], "out")
    src_ids, src_langs = gen._oracle_name_records(os.path.join(out_dir, body["input"]["source"]))
    sub_ids, sub_langs = gen._oracle_name_records(os.path.join(out_dir, body["font"]))

    assert sorted(sub_ids) == sorted(body["expect"]["subset_name_ids"])
    assert sorted(sub_langs) == sorted(body["expect"]["subset_name_languages"])
    assert sorted(set(src_ids) - set(sub_ids)) == sorted(body["expect"]["missing_name_ids"])
    assert len(src_langs) > len(sub_langs), "源并非多语言 → F5 构造失效"


def test_f6_golden_codepage_contradiction():
    """F6：码页声明 Latin-1 而 cmap 无 Latin-1；且 `ulUnicodeRange1=0` **不**构成矛盾。"""
    import gen_fixtures as gen

    with io.open(_expect_path("F6"), "r", encoding="utf-8") as fh:
        body = json.load(fh)
    font_path = os.path.join(FIXTURES_ROOT, NAMES["F6"], "out", body["font"])
    os2 = gen.oracle_os2(font_path)
    exp = body["expect"]

    assert "0x%08X" % os2["ulCodePageRange"][0] == exp["ulCodePageRange1"]
    assert "0x%08X" % os2["ulUnicodeRange"][0] == exp["ulUnicodeRange1"]
    assert bool(os2["ulUnicodeRange"][1] & (1 << 27)) == exp["ulUnicodeRange2_bit59_set"]

    covered = gen.oracle_sfnt_cmap_mask(font_path)
    has_latin1 = any(cp <= 0xFF for cp in covered)
    assert has_latin1 == exp["cmap_has_latin1"]
    assert (os2["ulCodePageRange"][0] & 0x1) != 0
    assert has_latin1 != ((os2["ulCodePageRange"][0] & 0x1) != 0), "矛盾未形成"


# ── 生成器被改坏 → 至少一层测试必红（变异验证，在临时拷贝里做） ─────────────
def test_corrupted_generator_is_caught_by_self_check(tmp_path):
    """变异：把 F2 的 `fsType` 从 0x000E 改成 0x0002（单权限位）。

    期望的双层判据：
      ① 生成期自证（``self_check``）必须失败 —— 因为 `permission_resolution` 期望
         "least_restrictive" 而单权限位不满足；
      ② 若自证被绕过，golden 测试也会红 —— 这里直接断言 ①（生成期就拦住）。
    """
    import gen_fixtures as gen

    out = str(tmp_path / "mut")
    original = gen.fixture_f2

    def mutated(out_dir):
        path = os.path.join(out_dir, "fstype-multibit-v0.ttf")
        gen.build_font(path, {0x61: "a", 0x62: "b", 0x63: "c"},
                       fs_type=0x0002, os2_version=0,
                       code_page_range=(0x1, 0x0), unicode_range=(0x1, 0x0, 0x0, 0x0))
        return path, {
            "id": "F2", "name": "fstype-multibit-v0", "font": "fstype-multibit-v0.ttf",
            "input": {"synthetic": True, "fsType": "0x0002", "os2_version": 0},
            "expect": {"os2_version": 0, "fsType": "0x0002", "permission_bits": "0x0002",
                       "permission_name": "Editable", "permission_resolution": "least_restrictive",
                       "may_subset": True, "mutual_exclusion_violation": False},
        }

    try:
        gen.BUILDERS["F2"] = mutated
        with pytest.raises(AssertionError) as exc:
            gen.generate(["F2"], out, verbose=False)
        assert "F2" in str(exc.value)
    finally:
        gen.BUILDERS["F2"] = original


def test_corrupted_cmap_is_caught_by_self_check(tmp_path):
    """变异：F4 的产物改成"其实没丢字"（子集里带上汉字）→ 自证必须红。

    这是"自证真的在看产物"的判据：如果 `self_check` 只是复述期望，这条不会红。
    """
    import gen_fixtures as gen

    out = str(tmp_path / "mut2")
    original = gen.fixture_f4

    def mutated(out_dir):
        # 先按原样构造（拿到同一份 expect），再把产物换成"没丢字"的子集
        _path, expect = original(out_dir)
        src = os.path.join(out_dir, "source.ttf")
        sub = os.path.join(out_dir, "subset.ttf")
        gen._subset(src, sub, [0x61, 0x62, 0x63, 0x5B57, 0x6C49])
        return sub, expect

    try:
        gen.BUILDERS["F4"] = mutated
        with pytest.raises(AssertionError) as exc:
            gen.generate(["F4"], out, verbose=False)
        assert "LOST_IN_SUBSET" in str(exc.value)
    finally:
        gen.BUILDERS["F4"] = original


# ── 产物不入仓 / 无字体二进制 ──────────────────────────────────────────────
def test_fixture_products_are_gitignored():
    """产物目录必须被 `.gitignore` 阻断 —— 字体二进制永不入仓（plan/04 §1）。"""
    ignored = os.path.join(REPO_ROOT, ".gitignore")
    text = io.open(ignored, "r", encoding="utf-8").read()
    assert "data/fixtures/**/out/" in text or "data/fixtures" in text


def test_generated_products_are_not_tracked_by_git():
    """`git ls-files` 里不得出现 fixture 产物（`.ttf`）—— 与 test_cli 的字体红线互补。"""
    toplevel = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=REPO_ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)
    if toplevel.returncode != 0:
        pytest.skip("not a git work tree")
    resolved = os.path.normcase(os.path.realpath(toplevel.stdout.strip()))
    if resolved != os.path.normcase(os.path.realpath(REPO_ROOT)):
        pytest.skip("解包树且 git 向上解析到别处：不能当作通过")
    proc = subprocess.run(["git", "ls-files", "data/fixtures"], cwd=REPO_ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)
    tracked = [line for line in proc.stdout.split("\n") if line.strip()]
    offenders = [t for t in tracked if t.lower().endswith((".ttf", ".otf", ".ttc"))]
    assert offenders == [], "fixture 产物不得入库: %s" % offenders
    # golden 与脚本**必须**在索引里
    assert any(t.endswith("expect.json") for t in tracked), \
        "expect.json 必须入仓，实得: %s" % tracked


# ── fetch_fonts：离线契约 ─────────────────────────────────────────────────
def test_fetch_fonts_check_never_imports_network_at_module_level():
    """零网络纪律：`fetch_fonts.py` 顶层不得 import 网络库（--check 路径不触发联网）。"""
    text = io.open(os.path.join(TOOLS, "fetch_fonts.py"), "r", encoding="utf-8").read()
    top_level = []
    for lineno, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if not (stripped.startswith("import ") or stripped.startswith("from ")):
            continue
        if line.startswith((" ", "\t")):  # 缩进 = 函数体内，允许（--download 分支）
            continue
        top_level.append((lineno, stripped))
    banned = ("urllib", "requests", "socket", "httpx", "aiohttp")
    hits = ["%d:%s" % (n, s) for n, s in top_level if any(b in s for b in banned)]
    assert hits == [], "顶层 import 网络库: %s" % hits


def test_fetch_fonts_reports_missing_without_crashing(tmp_path):
    """`--check` 指向空目录 → 报 MISSING 且 exit 1（不崩）。"""
    code, out = _run_gen([])  # 只为确认调用形态；真正的断言在下面
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", os.path.join(TOOLS, "fetch_fonts.py"),
         "--check", "--dir", str(tmp_path)],
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True)
    assert proc.returncode == 1, proc.stdout
    assert "MISSING" in proc.stdout


def test_fetch_fonts_lock_is_valid_json_version_1():
    path = os.path.join(REPO_ROOT, "data", "fonts.lock")
    with io.open(path, "r", encoding="utf-8") as fh:
        body = json.load(fh)
    assert body["version"] == 1
    names = [f["name"] for f in body["fonts"]]
    assert len(names) >= 3
    # Inter 的实测值必须与 data/README.md §八 一致
    inter = [f for f in body["fonts"] if f["name"] == "InterVariable.ttf"][0]
    assert inter["bytes"] == 879708
    assert inter["sha256"].startswith("4989b125")


def test_fetch_fonts_check_passes_when_fonts_present(tmp_path):
    """把锁文件里的字体复制进临时目录（若本机已下载）→ `--check` 通过。"""
    font_dir = os.path.join(REPO_ROOT, "data", "fonts")
    if not os.path.isdir(font_dir):
        pytest.skip("data/fonts 未下载（离线环境）；用 --download 获取")
    with io.open(os.path.join(REPO_ROOT, "data", "fonts.lock"), "r", encoding="utf-8") as fh:
        body = json.load(fh)
    missing = [f["name"] for f in body["fonts"]
               if not os.path.isfile(os.path.join(font_dir, f["name"]))]
    if missing:
        pytest.skip("字体未下载: %s" % missing)
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", os.path.join(TOOLS, "fetch_fonts.py"),
         "--check", "--dir", str(font_dir)],
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True)
    assert proc.returncode == 0, proc.stdout