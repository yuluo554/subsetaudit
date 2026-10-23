#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""门自证：对**三道门**做**变异验证**（改坏被测对象 → 指定判据必须变红 → 还原逐字节一致）。

为什么常驻：`ai-tool-project-sprint` 的纪律是"判据有几条，变异就做几组"，而**变异靶子会随
项目进度过期**（某个里程碑翻 ✅ 后，原来的靶子就不存在了）。把它做成脚本，每棒收尾重跑一次，
比"我记得上次验过"可审计。

判据（每条都独立断言，不是"断言了全世界"）：
  · 变异前：marker 必须存在（否则是静默 no-op）；
  · 变异后：文件字节必须**确实变了**（否则测的是空转）；
  · 跑门：目标判据 ID 必须报 FAIL（**只认那一条**，别的判据红不红不影响本条结论）；
  · 还原后：文件字节与原始**逐字节一致**，且门复绿。

分组：
  L* 布局门（`check_sprint_layout.py`）／ V* 脱敏门（`check_desensitized.py`）／
  R* 发布终态门（`check_release.py --pre-tag`，M6 加的新门 → 判据有几条、变异就补几组）。

退出码：0 全部符合预期 / 1 有不符合 / 2 用法错误。
用法：py tools/verify_gates.py [--only L1,L3] [--verbose]
"""
from __future__ import print_function

import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

LAYOUT = "tools/check_sprint_layout.py"
DESENS = "tools/check_desensitized.py"
RELEASE = "tools/check_release.py"


# ── 文件工具 ────────────────────────────────────────────────────────────────
def path_of(rel):
    return os.path.join(ROOT, rel)


def read(rel):
    with io.open(path_of(rel), "r", encoding="utf-8") as fh:
        return fh.read()


def write(rel, text):
    with io.open(path_of(rel), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def current_version():
    """从 `__init__.py` 取当前版本串 —— 变异靶子用它**动态取值**。

    硬编码版本串会让每次升版后的靶子失配：`_replace_once` 的 ``assert old in text`` 会先把
    **整条变异**打成失败（不会静默空转，但会让人每次升版都来改门）。动态取值让升级与门脱钩。
    """
    match = re.search(r'^__version__\s*=\s*"([^"]+)"',
                      read("src/subsetaudit/__init__.py"), re.M)
    assert match, "取不到 __version__（`src/subsetaudit/__init__.py` 形态变了？）"
    return match.group(1)


def run_gate(rel, extra=None):
    proc = subprocess.Popen(
        [PY, "-X", "utf8", os.path.join(ROOT, rel)] + list(extra or []),
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    out = proc.communicate()[0]
    try:
        text = out.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        text = str(out)
    return proc.returncode, text


def _git(*args):
    proc = subprocess.Popen(["git"] + list(args), cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    out = proc.communicate()[0]
    return proc.returncode, out.decode("utf-8", "replace")


def failed_ids(output):
    """抽出命中的判据/规则 ID。

    两种门两种行形态，必须都认：
      · 布局门：``FAIL  LAYOUT.FILES  缺: ...``
      · 脱敏门：``FAIL  path/to/file.md:40: [absolute-session-path] 原文``
    首版只取 ``line[6:].split()[0]``，对脱敏门拿到的是**文件路径**而不是规则名
    → 4 组变异全被误判为"没红"（变异验证 V1–V4 抓出的验证器自身缺陷）。
    """
    ids = []
    for line in output.split("\n"):
        if not line.startswith("FAIL  "):
            continue
        rest = line[6:].strip()
        if rest.startswith("["):
            ids.append(rest[1:].split("]", 1)[0])
        elif ": [" in rest:
            ids.append(rest.split(": [", 1)[1].split("]", 1)[0])
        else:
            ids.append(rest.split()[0] if rest else "")
    return ids


# ── 变异定义 ────────────────────────────────────────────────────────────────
# 每条 = (id, 说明, 门, 期望判据, apply() -> undo(), 前置 setup() -> teardown() or None)
def _replace_once(rel, old, new):
    text = read(rel)
    assert old in text, "marker 不存在，变异会静默 no-op: %r in %s" % (old, rel)
    write(rel, text.replace(old, new, 1))
    assert read(rel) != text, "替换后文件未变化: %s" % rel

    def undo():
        write(rel, text)

    return undo


def _remove(rel):
    original = read(rel)
    os.remove(path_of(rel))
    assert not os.path.exists(path_of(rel))

    def undo():
        write(rel, original)

    return undo


def _chain(*steps):
    """按序执行；返回逆序 undo。"""
    undos = [step() for step in steps]

    def undo():
        for fn in reversed(undos):
            fn()

    return undo


def _append_bytes(rel, extra):
    """往文件**追加字节**（改坏 fixture 产物用）。undo 还原原字节。"""
    path = path_of(rel)
    with open(path, "rb") as fh:
        original = fh.read()
    with open(path, "ab") as fh:
        fh.write(extra)
    with open(path, "rb") as fh:
        assert fh.read() != original, "追加后文件未变化: %s" % rel

    def undo():
        with open(path, "wb") as fh:
            fh.write(original)

    return undo


def _stage_font_binary(rel, payload=b"not-a-real-font"):
    """造一个**入库的字体二进制**：写文件 + 强制 `git add`（绕过 .gitignore）。

    靶子语义 = "红线被破时 `RELEASE.NO_FONT_BINARIES` 必须红"。undo 必须**恢复 git 索引**，
    否则工作树虽然干净、索引里却留着一条假入库项（`verify_gates` 的逐字节复核看不见索引）。
    """
    path = path_of(rel)
    assert not os.path.exists(path), "临时文件已存在: %s" % rel
    with open(path, "wb") as fh:
        fh.write(payload)
    rc, out = _git("add", "-f", rel)
    assert rc == 0, "git add -f 失败: %s" % out
    _, staged = _git("ls-files", "--", rel)
    assert staged.strip() == rel, "文件没进索引: %r" % staged

    def undo():
        _git("rm", "--cached", "-f", "--quiet", rel)
        if os.path.exists(path):
            os.remove(path)

    return undo


# 2026-10-21 M6 收尾：`_create` / `RELEASE_STUB` / `HANDOFF_STUB_INCOMPLETE` / `_mark_done`
# 四个 helper 随"下一个 ⬜ 里程碑"机制一起退役（它们是那个机制的零件：造临时件 + 把里程碑
# 翻 ✅）。留着会让人以为还有"造靶子件"的能力 —— 靶子已改为打在**既有真实文件**上。


def _leak_payload(*parts):
    """在**运行期**拼出脱敏门要抓的字面量。

    为什么不在本文件里直接写这些串：本脚本会被脱敏门扫到，写了就成了"门要抓的东西躺在门
    能扫到的文件里"——要么豁免本文件（把豁免面从 1 份扩到 2 份），要么像这里一样拼装。
    **拼装优于豁免**：豁免面越大，越可能有人把真泄露藏进豁免文件。
    """
    return "".join(parts)


# 四个 payload 与 check_desensitized.py 的四条规则一一对应
LEAK_ABSOLUTE = _leak_payload("D", ":/ProgramData/", "leak")
LEAK_HOST_USER = _leak_payload("C:", "\\Users\\", "AS", "US", "\\x")
LEAK_MSYS = _leak_payload("/c/Users/", "AS", "US", "/x")
LEAK_LOOPBACK = _leak_payload("127.0.0.", "1:7897")


#: 发布终态门只跑 `--pre-tag`（离线、零网络）—— 与 CI 里那一步同口径。
#: 逐门的调用参数表：门的"模式"是实现的一部分，变异必须跑在与 CI/发布棒相同的模式下。
RELEASE_ARGS = ("--pre-tag",)
GATE_ARGS = {RELEASE: RELEASE_ARGS}


def _corrupt_sha256sums():
    """把 `dist/SHA256SUMS` 里第一条摘要的首字符改掉 → `RELEASE.SHA256SUMS` 必须红。

    靶子语义 = "附件里的校验值过期/写错时，门能发现"。这比"删掉 SHA256SUMS"更强：
    删掉只测"文件在不在"，改错才测"内容对不对"（后者才是用户真正依赖的性质）。
    """
    rel = "dist/SHA256SUMS"
    path = path_of(rel)

    def apply():
        assert os.path.isfile(path), "缺 %s（先构建 dist/ 并生成 SHA256SUMS）" % rel
        with io.open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        rows = [r for r in text.split("\n") if r.strip()]
        assert rows, "%s 是空的" % rel
        digest, name = rows[0].split("  ", 1)
        bad = ("0" if digest[0] != "0" else "1") + digest[1:]
        rows[0] = "%s  %s" % (bad, name)
        write(rel, "\n".join(rows) + "\n")
        assert read(rel) != text, "替换后文件未变化: %s" % rel

        def undo():
            write(rel, text)

        return undo

    return apply()


MUTATIONS = [
    ("L1", "删 AGENTS.md", LAYOUT, "LAYOUT.FILES",
     lambda: _remove("AGENTS.md")),
    ("L2", "把 README 的 M0 翻成 ⬜（副本间不一致）", LAYOUT, "LAYOUT.STATUS",
     lambda: _replace_once("README.md", "| M0 | 方法论装订 + 计划套件 + 可运行骨架 | ✅ |",
                           "| M0 | 方法论装订 + 计划套件 + 可运行骨架 | ⬜ |")),
    ("L3", "往 plan/06 缺口格写一个已 ✅ 的里程碑", LAYOUT, "LAYOUT.GAPS",
     # 靶子锚在**缺口表里一行真实存在的缺口**上；缺口表内容会随里程碑推进变化，
     # 锚点失效时本组会显式 SKIP（2026-10-21 M6 实测：原锚点"CI 实跑 | 无远端…"随该缺口
     # 关闭而消失 → 已改锚到仍存在的"判定实现"行）。
     lambda: _replace_once("plan/06-交付对标与决策.md",
                           "| 判定实现（元数据 / 报告聚合） |",
                           "| 判定实现（元数据 / 报告聚合，M5） |")),
    # ── 靶子纪律（2026-10-21 M6 收尾，见 HANDOFF-M6 §二.8）──────────────────────
    # M6 之后**没有下一个 ⬜ 里程碑**了，所以"把下一个里程碑标 ✅、再改坏它的收尾件"
    # 这一类靶子（L4/L6/L8/L9/L10/L12 原先都靠 `_mark_done(6)`）整体失效：`_mark_done`
    # 在"该行本来就不是 ⬜"处断言失败 → 六条一起 SKIP。
    # 处置 = **换成不依赖下一个里程碑的靶子**：打在**已 ✅ 里程碑的真实交接单**（M5）与
    # **真实发布留档**（`plan/RELEASE-M6.md`）上。判据面不变（HANDOFFS / RELEASE /
    # LEDGER / DOC_TOOLS 四条照旧），但前提从"未来进度"变成"既有事实"，不会再过期。
    ("L4", "已 ✅ 里程碑（M5）的交接单缺节", LAYOUT, "LAYOUT.HANDOFFS",
     lambda: _replace_once("plan/HANDOFF-M5.md",
                           "## 五、本机环境坑（只写实测过的）",
                           "## 五、环境（七节关键词被改写）")),
    ("L5", "删 plan/00 顶部装订行", LAYOUT, "LAYOUT.BINDING_HEAD",
     lambda: _replace_once("plan/00-README总览.md",
                           "> 方法论：`ai-tool-project-sprint`（装订 2026-10-21）",
                           "> （装订行被移除）方法论：")),
    ("L6", "删发布留档的覆盖对账整节", LAYOUT, "LAYOUT.RELEASE",
     lambda: _replace_once("plan/RELEASE-M6.md",
                           "## 三、阶段 7 覆盖对账", "## 三、其它")),
    ("L7", "删 plan/02（计划套件缺一份）", LAYOUT, "LAYOUT.FILES",
     lambda: _remove("plan/02-架构与技术选型.md")),
    ("L8", "去掉发布留档 §二 标题里的 'tag 后'", LAYOUT, "LAYOUT.RELEASE",
     lambda: _replace_once("plan/RELEASE-M6.md",
                           "## 二、tag 后追加事实", "## 二、追加事实")),
    # L9 的语义是"**已 ✅ 的里程碑**在台账里仍挂未完成标记"。M6 收尾后靶子改打在
    # **已 ✅ 的 M1** 那一行上（不再需要先把某个里程碑翻 ✅）。
    ("L9", "已 ✅ 里程碑（M1）在台账里仍挂 ⬜ 待办", LAYOUT, "LAYOUT.LEDGER",
     lambda: _replace_once("plan/00-README总览.md",
                           "| M1 `license-gate`（版本分流 + 三类闸门） | plan/01 §三 M1 | ✅ 含 5 条验收；**M2 里程碑已实现**（五元结论口径入 §六.1.3） |",
                           "| M1 `license-gate`（版本分流 + 三类闸门） | plan/01 §三 M1 | ⬜ 待 M1 复核 |")),
    ("L10", "发布里程碑 ✅ 但删掉 RELEASE 留档", LAYOUT, "LAYOUT.RELEASE",
     lambda: _remove("plan/RELEASE-M6.md")),
    ("L11", "文档点名一个不存在的 tools/*.py", LAYOUT, "LAYOUT.DOC_TOOLS",
     lambda: _replace_once("plan/06-交付对标与决策.md",
                           "## 3. 验收门（每棒都要过的门，按顺序）",
                           "## 3. 验收门（每棒都要过的门，按顺序）\n\n> 变异验证用：`tools/does_not_exist.py`\n")),
    ("L12", "PENDING_TOOLS 登记一个已 ✅ 里程碑名下、却不存在的脚本", LAYOUT, "LAYOUT.DOC_TOOLS",
     # 2026-10-21 M6 收尾：`PENDING_TOOLS` 已清空（最后一个登记项随 M6 自清理）→ 原来
     # "把登记项所属里程碑翻 ✅"的靶子不再可构造。改法：**直接往登记表里塞一条过期登记**
     # （里程碑 5 已 ✅）+ 在文档里点名该脚本 —— 判据仍是"登记项必须自清理"这一条。
     lambda: _chain(
         lambda: _replace_once("tools/check_sprint_layout.py",
                               "PENDING_TOOLS = {}",
                               'PENDING_TOOLS = {\n    "tools/pending_probe.py": 5,\n}'),
         lambda: _replace_once("plan/06-交付对标与决策.md",
                               "## 3. 验收门（每棒都要过的门，按顺序）",
                               "## 3. 验收门（每棒都要过的门，按顺序）\n\n> 变异验证用：`tools/pending_probe.py`\n"))),
    ("V1", "写一行绝对会话路径", DESENS, "absolute-session-path",
     lambda: _replace_once("plan/06-交付对标与决策.md", "## 4. 风险登记",
                           "## 4. 风险登记\n\n<!-- 变异验证用：%s -->\n" % LEAK_ABSOLUTE)),
    ("V2", "写带真实用户名的盘符路径", DESENS, "host-username",
     lambda: _replace_once("plan/06-交付对标与决策.md", "## 4. 风险登记",
                           "## 4. 风险登记\n\n<!-- 变异验证用：%s -->\n" % LEAK_HOST_USER)),
    ("V3", "写 MSYS 形态的用户路径", DESENS, "msys-user-path",
     lambda: _replace_once("plan/06-交付对标与决策.md", "## 4. 风险登记",
                           "## 4. 风险登记\n\n<!-- 变异验证用：%s -->\n" % LEAK_MSYS)),
    ("V4", "写回环代理端口", DESENS, "loopback-proxy",
     lambda: _replace_once("plan/06-交付对标与决策.md", "## 4. 风险登记",
                           "## 4. 风险登记\n\n<!-- 变异验证用：%s -->\n" % LEAK_LOOPBACK)),
    # ── 发布终态门 R1–R8（M6 加的新门 → 判据有几条、变异就补几组）─────────────────
    # 靶子全部打在**真实交付面**上（版本三处 / LICENSE / 报告样例 / cli 参数面 /
    # git 索引 / 发布留档 / PENDING_TOOLS），不依赖"下一个 ⬜ 里程碑"。
    # R1/R3 的靶子用 `current_version()` **动态取值**：硬编码版本串会让每次升版都得回来改门。
    ("R1", "把 README 状态行的版本改回旧值（三处不一致）", RELEASE, "RELEASE.VERSION_TRIPLE",
     lambda: _replace_once("README.md", "- **版本**：v%s" % current_version(),
                           "- **版本**：v0.0.9"), RELEASE_ARGS),
    ("R2", "把 pyproject 的 license 字段改成非 MIT", RELEASE, "RELEASE.LICENSE_CONSISTENT",
     lambda: _replace_once("pyproject.toml", 'license = { text = "MIT" }',
                           'license = { text = "Apache-2.0" }'), RELEASE_ARGS),
    ("R3", "把报告样例的 tool.version 改旧（与现行实现不同源）", RELEASE, "RELEASE.SAMPLE_JSON",
     lambda: _replace_once("docs/report-sample.json", '"version": "%s"' % current_version(),
                           '"version": "0.0.1"'), RELEASE_ARGS),
    ("R4", "删 cli.py 的 report 子命令（五子命令不全）", RELEASE, "RELEASE.SUBCMDS",
     lambda: _replace_once("src/subsetaudit/cli.py", 'sub.add_parser("report"',
                           'sub.add_parser("report-renamed"'), RELEASE_ARGS),
    ("R5", "把一个字体二进制强加进 git 索引（破'无商用/无字体二进制'红线）",
     RELEASE, "RELEASE.NO_FONT_BINARIES",
     lambda: _stage_font_binary("tools/_probe_redline.ttf"), RELEASE_ARGS),
    ("R6", "改坏一个 fixture 产物（位级一致性被破）", RELEASE, "RELEASE.FIXTURES_BITWISE",
     lambda: _append_bytes("data/fixtures/silent-drop/out/subset.ttf", b"X"), RELEASE_ARGS),
    ("R7", "删发布留档的覆盖对账整节", RELEASE, "RELEASE.RELEASE_DOC",
     lambda: _replace_once("plan/RELEASE-M6.md", "## 三、阶段 7 覆盖对账", "## 三、其它"),
     RELEASE_ARGS),
    # R9 走 `RELEASE_ARGS`（pre-tag 档）：`RELEASE.SHA256SUMS` 就在那一档（见 D-M7-2）。
    # CI 不构建 `dist/`，那时这条变异会显式 SKIP（不是 FAIL、也不冒充通过）。
    ("R9", "把 dist/SHA256SUMS 里的一条摘要改错（附件过期仍声称可校验）", RELEASE,
     "RELEASE.SHA256SUMS",
     lambda: _corrupt_sha256sums(), RELEASE_ARGS),
    ("R8", "往 PENDING_TOOLS 塞一条已 ✅ 里程碑名下的过期登记", RELEASE,
     "RELEASE.PENDING_TOOLS_CLEARED",
     lambda: _replace_once("tools/check_sprint_layout.py", "PENDING_TOOLS = {}",
                           'PENDING_TOOLS = {\n    "tools/probe.py": 5,\n}'), RELEASE_ARGS),
]


def _snapshot():
    """变异前的门结论（用于"还原后复绿"）。"""
    return run_gate(LAYOUT), run_gate(DESENS), run_gate(RELEASE, RELEASE_ARGS)


def _tree_hashes():
    """全仓文本/源码文件的 sha256（跳过 .git / 缓存 / 临时目录）。

    用途：全部变异跑完后，与开工前的快照逐文件比对 —— **"还原逐字节一致"必须是断言，
    不是"我看了一眼 git status"**。首版只打印 git status，而工作树在开发期本来就脏，
    于是"还原干净了没有"这个问题实际上没人回答。
    """
    import hashlib

    skip_dirs = {".git", "__pycache__", "_scratch", ".pytest_cache", ".venv", "venv",
                 "build", "dist", ".venv-readme"}
    out = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in sorted(dirnames) if d not in skip_dirs]
        for name in sorted(filenames):
            if name.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            with open(full, "rb") as fh:
                out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


def main(argv):
    only = None
    verbose = "--verbose" in argv
    for arg in argv:
        if arg.startswith("--only="):
            only = set(arg.split("=", 1)[1].split(","))
        elif arg == "--verbose":
            continue
        else:
            sys.stderr.write("verify_gates: 未知参数 %r\n" % arg)
            return 2

    base_layout, base_desens, base_release = _snapshot()
    baseline = {LAYOUT: base_layout, DESENS: base_desens, RELEASE: base_release}
    for gate, (rc, out) in baseline.items():
        if rc != 0:
            sys.stderr.write("基线不绿，变异验证没有意义：%s rc=%s\n%s\n" % (gate, rc, out))
            return 1

    results = []
    before = _tree_hashes()
    for mutation in MUTATIONS:
        if len(mutation) == 6:
            mut_id, desc, gate, expected, apply_mut, gate_args = mutation
        else:
            mut_id, desc, gate, expected, apply_mut = mutation
            gate_args = GATE_ARGS.get(gate)
        if only is not None and mut_id not in only:
            continue
        undo = None
        try:
            try:
                undo = apply_mut()
            except AssertionError as exc:
                # **构造不出靶子 = 显式 SKIP，不是 FAIL、也不是 PASS**。
                # 随项目进度推进，某个变异的前提可能自然消失（本项目：M0 收尾后
                # HANDOFF-M1.md 真的存在了，"造一个缺节的临时件"就不再成立）。
                # SKIP 必须可见（打印 + 计数），不许静默，也不许冒充通过。
                print("SKIP %-4s %s（靶子已随进度消失: %s）" % (mut_id, desc, exc))
                results.append((mut_id, desc, expected, None, ["skipped"], "-"))
                continue
            rc, out = run_gate(gate, gate_args)
            ids = failed_ids(out)
            ok = rc == 1 and expected in ids
            results.append((mut_id, desc, expected, ok, ids, rc))
            if verbose or not ok:
                print("%s %-4s %s -> 期望 %s，实得 rc=%s FAIL=%s"
                      % ("PASS" if ok else "MISS", mut_id, desc, expected, rc, ids))
        finally:
            if undo is not None:
                undo()
            rc2, out2 = run_gate(gate, gate_args)
            if rc2 != 0 and undo is not None:
                print("!! %s 还原后门未复绿 rc=%s\n%s" % (mut_id, rc2, out2))
                results.append((mut_id + "-restore", "还原后复绿", gate, False, failed_ids(out2), rc2))

    # 还原后逐字节复核：全部变异跑完后与开工前快照逐文件比对
    after = _tree_hashes()
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if changed:
        print("!! 还原后仓库未逐字节复原，差异文件：")
        for rel in changed:
            print("   %s  before=%s after=%s" % (rel, (before.get(rel) or "-")[:12],
                                                 (after.get(rel) or "-")[:12]))
        results.append(("restore", "还原逐字节一致", "-", False, changed, 1))
    else:
        print("还原复核：%d 个文件逐字节一致（无 .bak 残留、无临时件）" % len(before))

    rc_layout, out_layout = run_gate(LAYOUT)
    rc_desens, out_desens = run_gate(DESENS)
    rc_release, out_release = run_gate(RELEASE, RELEASE_ARGS)
    green = rc_layout == 0 and rc_desens == 0 and rc_release == 0
    if not green:
        print("!! 全部还原后三道门未复绿：layout rc=%s desens rc=%s release rc=%s"
              % (rc_layout, rc_desens, rc_release))
        if rc_release != 0:
            print(out_release)
        results.append(("regreen", "还原后三道门复绿", "-", False, [], 1))
    else:
        print("复绿复核：布局门 + 脱敏门 + 发布门均绿")

    ok_all = all(r[3] is True or r[3] is None for r in results)
    verified = sum(1 for r in results if r[3] is True)
    skipped = sum(1 for r in results if r[3] is None)
    print("")
    print("变异验证：%d 项检查，%d 项符合预期，%d 项 SKIP（靶子已随进度消失）"
          % (len(results), verified, skipped))
    if skipped and not verbose:
        print("（SKIP 项需在 HANDOFF 里逐条说明为何当前构造不出靶子）")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))