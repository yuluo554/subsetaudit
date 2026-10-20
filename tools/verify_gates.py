#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""门自证：对两道门做**变异验证**（改坏被测对象 → 指定判据必须变红 → 还原逐字节一致）。

为什么常驻：`ai-tool-project-sprint` 的纪律是"判据有几条，变异就做几组"，而**变异靶子会随
项目进度过期**（某个里程碑翻 ✅ 后，原来的靶子就不存在了）。把它做成脚本，每棒收尾重跑一次，
比"我记得上次验过"可审计。

判据（每条都独立断言，不是"断言了全世界"）：
  · 变异前：marker 必须存在（否则是静默 no-op）；
  · 变异后：文件字节必须**确实变了**（否则测的是空转）；
  · 跑门：目标判据 ID 必须报 FAIL（**只认那一条**，别的判据红不红不影响本条结论）；
  · 还原后：文件字节与原始**逐字节一致**，且门复绿。

退出码：0 全部符合预期 / 1 有不符合 / 2 用法错误。
用法：py tools/verify_gates.py [--only L1,L3] [--verbose]
"""
from __future__ import print_function

import io
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

LAYOUT = "tools/check_sprint_layout.py"
DESENS = "tools/check_desensitized.py"


# ── 文件工具 ────────────────────────────────────────────────────────────────
def path_of(rel):
    return os.path.join(ROOT, rel)


def read(rel):
    with io.open(path_of(rel), "r", encoding="utf-8") as fh:
        return fh.read()


def write(rel, text):
    with io.open(path_of(rel), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def run_gate(rel):
    proc = subprocess.Popen(
        [PY, "-X", "utf8", os.path.join(ROOT, rel)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    out = proc.communicate()[0]
    try:
        text = out.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        text = str(out)
    return proc.returncode, text


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


def _create(rel, text):
    assert not os.path.exists(path_of(rel)), "临时文件已存在: %s" % rel
    write(rel, text)

    def undo():
        if os.path.exists(path_of(rel)):
            os.remove(path_of(rel))

    return undo


def _chain(*steps):
    """按序执行；返回逆序 undo。"""
    undos = [step() for step in steps]

    def undo():
        for fn in reversed(undos):
            fn()

    return undo


RELEASE_STUB = """# RELEASE-M6（变异验证用临时件）

## 一、tag 前事实

| 项 | 值 |
|---|---|
| 版本 | v0.1.0 |

## 二、tag 后追加事实

（临时）

## 三、阶段 7 覆盖对账

| 出口门 | 状态 | 证据 |
|---|---|---|
| A1 本体已验 | 实现 | stub |
| A2 附件同源 | 实现 | stub |
| A3 源码包自足 | 不适用 | stub |
"""


def _mark_done(milestone):
    """把某里程碑在三处副本里都标成 ✅（供 HANDOFFS / RELEASE 类变异用）。"""
    rel_map = {
        "plan/00-README总览.md": "| **M%d",
        "plan/05-里程碑.md": "| M%d",
        "README.md": "| M%d",
    }
    undos = []
    for rel, prefix in rel_map.items():
        text = read(rel)
        lines = text.split("\n")
        hit = None
        for i, line in enumerate(lines):
            if line.startswith(prefix % milestone):
                hit = i
                break
        assert hit is not None, "%s 找不到 M%d 行" % (rel, milestone)
        old_line = lines[hit]
        assert "⬜" in old_line, "M%d 行本来就不是 ⬜: %r" % (milestone, old_line)
        lines[hit] = old_line.replace("⬜", "✅")
        write(rel, "\n".join(lines))
        undos.append((rel, text))
        assert read(rel) != text

    def undo():
        for rel, text in reversed(undos):
            write(rel, text)

    return undo


HANDOFF_STUB_INCOMPLETE = "# HANDOFF-M1\n\n## 当前进度\n\n（变异验证用：故意缺节）\n"


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


MUTATIONS = [
    ("L1", "删 AGENTS.md", LAYOUT, "LAYOUT.FILES",
     lambda: _remove("AGENTS.md")),
    ("L2", "把 README 的 M0 翻成 ⬜（副本间不一致）", LAYOUT, "LAYOUT.STATUS",
     lambda: _replace_once("README.md", "| M0 | 方法论装订 + 计划套件 + 可运行骨架 | ✅ |",
                           "| M0 | 方法论装订 + 计划套件 + 可运行骨架 | ⬜ |")),
    ("L3", "往 plan/06 缺口格写一个已 ✅ 的里程碑", LAYOUT, "LAYOUT.GAPS",
     lambda: _replace_once("plan/06-交付对标与决策.md",
                           "| CI 实跑 | 无远端，未跑过 | 首次 push 后登记 run id |",
                           "| CI 实跑（M0） | 无远端，未跑过 | 首次 push 后登记 run id |")),
    ("L4", "M1 标 ✅ 但交接单缺节", LAYOUT, "LAYOUT.HANDOFFS",
     # 靶子随进度漂移（M0 时 HANDOFF-M1.md 不存在 → 用 _create 造一个缺节的；
     # M0 收尾后它真实存在了 → 改成把真实文件里的某一节标题改掉）。
     # 两种形态都只在"M1 已 ✅"时才有意义，所以统一先 _mark_done(1)。
     lambda: _chain(
         lambda: _mark_done(1),
         (lambda: _create("plan/HANDOFF-M1.md", HANDOFF_STUB_INCOMPLETE))
         if not os.path.exists(path_of("plan/HANDOFF-M1.md"))
         else (lambda: _replace_once("plan/HANDOFF-M1.md", "## 五、本机环境坑", "## 五、环境"))
     )),
    ("L5", "删 plan/00 顶部装订行", LAYOUT, "LAYOUT.BINDING_HEAD",
     lambda: _replace_once("plan/00-README总览.md",
                           "> 方法论：`ai-tool-project-sprint`（装订 2026-10-21）",
                           "> （装订行被移除）方法论：")),
    ("L6", "删发布留档的覆盖对账整节", LAYOUT, "LAYOUT.RELEASE",
     lambda: _chain(lambda: _mark_done(6),
                    lambda: _create("plan/RELEASE-M6.md", RELEASE_STUB),
                    lambda: _replace_once("plan/RELEASE-M6.md",
                                          "## 三、阶段 7 覆盖对账", "## 三、其它"))),
    ("L7", "删 plan/02（计划套件缺一份）", LAYOUT, "LAYOUT.FILES",
     lambda: _remove("plan/02-架构与技术选型.md")),
    ("L8", "去掉发布留档 §二 标题里的 'tag 后'", LAYOUT, "LAYOUT.RELEASE",
     lambda: _chain(lambda: _mark_done(6),
                    lambda: _create("plan/RELEASE-M6.md", RELEASE_STUB),
                    lambda: _replace_once("plan/RELEASE-M6.md",
                                          "## 二、tag 后追加事实", "## 二、追加事实"))),
    # L9 的语义是"**已 ✅ 的里程碑**在台账里仍挂未完成标记"，所以必须先让 M1 翻 ✅
    # 再往台账写 `⬜ 待 M1` —— 否则 M1 本来就没完成，这一行是**正确状态**，不该红
    # （变异验证首版就瞄错了靶子：靶子挑错时"没红"不代表门假）。
    ("L9", "M1 已 ✅ 但台账里仍写 ⬜ 待 M1", LAYOUT, "LAYOUT.LEDGER",
     lambda: _chain(lambda: _mark_done(1),
                    lambda: _replace_once("plan/00-README总览.md",
                                          "| 定位宣言含\"审产物不审项目\" | plan/01 §头部、README | ✅ 已写 |",
                                          "| 定位宣言含\"审产物不审项目\" | plan/01 §头部、README | ⬜ 待 M1 验证 |"))),
    ("L10", "发布里程碑 ✅ 但删掉 RELEASE 留档", LAYOUT, "LAYOUT.RELEASE",
     lambda: _mark_done(6)),
    ("L11", "文档点名一个不存在的 tools/*.py", LAYOUT, "LAYOUT.DOC_TOOLS",
     lambda: _replace_once("plan/06-交付对标与决策.md",
                           "## 3. 验收门（每棒都要过的门，按顺序）",
                           "## 3. 验收门（每棒都要过的门，按顺序）\n\n> 变异验证用：`tools/does_not_exist.py`\n")),
    ("L12", "PENDING_TOOLS 里的工具所属里程碑翻 ✅（登记项未清理）", LAYOUT, "LAYOUT.DOC_TOOLS",
     lambda: _mark_done(1)),
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
]


def _snapshot():
    """变异前的门结论（用于"还原后复绿"）。"""
    return run_gate(LAYOUT), run_gate(DESENS)


def _tree_hashes():
    """全仓文本/源码文件的 sha256（跳过 .git / 缓存 / 临时目录）。

    用途：全部变异跑完后，与开工前的快照逐文件比对 —— **"还原逐字节一致"必须是断言，
    不是"我看了一眼 git status"**。首版只打印 git status，而工作树在开发期本来就脏，
    于是"还原干净了没有"这个问题实际上没人回答。
    """
    import hashlib

    skip_dirs = {".git", "__pycache__", "_scratch", ".pytest_cache", ".venv", "venv",
                 "build", "dist"}
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

    base_layout, base_desens = _snapshot()
    baseline = {LAYOUT: base_layout, DESENS: base_desens}
    for gate, (rc, out) in baseline.items():
        if rc != 0:
            sys.stderr.write("基线不绿，变异验证没有意义：%s rc=%s\n%s\n" % (gate, rc, out))
            return 1

    results = []
    before = _tree_hashes()
    for mut_id, desc, gate, expected, apply_mut in MUTATIONS:
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
            rc, out = run_gate(gate)
            ids = failed_ids(out)
            ok = rc == 1 and expected in ids
            results.append((mut_id, desc, expected, ok, ids, rc))
            if verbose or not ok:
                print("%s %-4s %s -> 期望 %s，实得 rc=%s FAIL=%s"
                      % ("PASS" if ok else "MISS", mut_id, desc, expected, rc, ids))
        finally:
            if undo is not None:
                undo()
            rc2, out2 = run_gate(gate)
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
    green = rc_layout == 0 and rc_desens == 0
    if not green:
        print("!! 全部还原后两道门未复绿：layout rc=%s desens rc=%s" % (rc_layout, rc_desens))
        results.append(("regreen", "还原后两道门复绿", "-", False, [], 1))
    else:
        print("复绿复核：布局门 + 脱敏门均绿")

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