#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""布局门（方法论装订的第②件）：把"项目还长在方法论上"变成可跑红的断言。

判据一律落**仓库内文件**（不读 git 元数据——浅克隆 / tarball 下 git tag、历史深度会翻转）。
退出码：0 全绿 / 1 有 FAIL / 2 用法错误。

纪律（来自 ai-tool-project-sprint 的「布局门自己的假门族」）：
  · 非空跑自证：每个判据都要报"这轮扫到了几个"；
  · 真值不取自任何单一副本：状态逐副本采集，任一里程碑出现两种状态即 FAIL；
  · 判据锚到**状态行**（表格行且首格就是里程碑号），不扫自由文本；
  · 缺口表按表头定位列号、扫描面收到"首条非表格行"，并把行数打进结论；
  · 永不崩：任何判据异常 → 报一条 FAIL 并继续（不许 rc=1 却一条结论都没跑）。

变异验证（每条判据至少一组，改完必须重跑全组）：
  V1  删 AGENTS.md                          → LAYOUT.FILES 红
  V2  把一个 ✅ 里程碑在某一份副本翻成 ⬜     → LAYOUT.STATUS 红
  V3  往 plan/06 缺口格写一个已 ✅ 的里程碑   → LAYOUT.GAPS 红
  V4  删一份 HANDOFF-M<k>                    → LAYOUT.HANDOFFS 红
  V5  删 plan/00 顶部装订行                  → LAYOUT.BINDING_HEAD 红
  V6  删发布留档的覆盖对账整节               → LAYOUT.RELEASE 红
  V7  删一份 plan/0<k>                       → LAYOUT.FILES 红
  V8  去掉发布留档 §二 标题里的 "tag 后"      → LAYOUT.RELEASE 红
  V9  把台账里某条 ✅ 行改成 ⬜ 待 M<k>        → LAYOUT.LEDGER 红
  V10 保留发布里程碑 ✅ 但删掉 RELEASE 留档   → LAYOUT.RELEASE 红
  V11 在文档里点名一个不存在的 tools/*.py     → LAYOUT.DOC_TOOLS 红
  V12 把 PENDING_TOOLS 里某工具所属里程碑翻 ✅ → LAYOUT.DOC_TOOLS 红（登记项必须自清理）
"""
from __future__ import print_function

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECKS = []
SCANNED = {"docs": 0, "handoffs": 0, "copies": 0, "doc_tools": 0}


def add(check_id, ok, detail):
    CHECKS.append({"id": check_id, "ok": ok, "detail": detail})


def read(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return None
    with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


# ── 配置（改项目只改这一段） ────────────────────────────────────────────────
REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "data/README.md",
    "plan/00-README总览.md",
    "plan/01-题目文档.md",
    "plan/02-架构与技术选型.md",
    "plan/03-模块详设.md",
    "plan/04-数据计划.md",
    "plan/05-里程碑.md",
    "plan/06-交付对标与决策.md",
]

# 装订行判据：三个锚点**必须同现于一行**（前瞻 = 顺序无关），不许写成"或"关系。
BINDING_LINE = re.compile(
    r"^>(?=.*ai-tool-project-sprint)(?=.*check[-_]sprint[-_]layout)(?=.*20\d{2}-\d{2}-\d{2}).*$",
    re.M,
)

REQUIRED_SECTIONS = {
    "plan/00-README总览.md": ["文档索引", "决策记录", "承诺-证据台账", "里程碑"],
    "plan/01-题目文档.md": ["任务要求", "评分标准", "边界与非目标"],
    "plan/02-架构与技术选型.md": ["分层", "选型", "退出码"],
    "plan/03-模块详设.md": ["子命令", "数据结构", "测试点"],
    "plan/04-数据计划.md": ["数据清单", "真值纪律", "数值口径"],
    "plan/05-里程碑.md": ["DoD", "已知未验证项"],
    "plan/06-交付对标与决策.md": ["评分对标", "风险登记"],
    "data/README.md": ["查证记录", "数值口径"],
}

# 项目**已声明**的豁免与冻结规则——门必须复用它，别另立更严的一套。
EXEMPT_MILESTONES = [0]  # M0 = 计划与装订；其收尾记录 = 计划套件本身（AGENTS.md 已声明）
HANDOFF_FORMAT_FROM = 1  # M1 起交接单必须七节齐
HANDOFF_SECTIONS = ["当前进度", "当前事实", "待办", "既定口径", "环境坑", "DoD", "命令速查"]

STATUS_COPIES = [
    "plan/00-README总览.md",
    "plan/05-里程碑.md",
    "README.md",
]

# 只认"状态行"：表格行且首格就是里程碑号（自由文本不参与判定，防张冠李戴的假红）。
STATUS_LINE = re.compile(r"^\|\s*\*{0,2}M(\d+)\b")
PENDING_MARKERS = ["⬜", "🟡", "未开始", "未执行", "待执行", "待确认"]

# 发布里程碑：固定为 M6。它未 ✅ 时，发布留档"尚不适用"→ PASS 并写明。
RELEASE_MILESTONE = 6

# 文档点名但**尚未到该里程碑**的工具：显式登记（而不是删掉引用）。
# 规则：登记项所属里程碑翻 ✅ 之后必须删除本条，否则 DOC_TOOLS 变红（自清理）。
PENDING_TOOLS = {
    "tools/gen_fixtures.py": 1,
    "tools/fetch_fonts.py": 1,
    "tools/check_release.py": 6,
}


# ── 判据 ────────────────────────────────────────────────────────────────────
def check_required_files():
    missing = [rel for rel in REQUIRED_FILES if not os.path.isfile(os.path.join(ROOT, rel))]
    SCANNED["docs"] = len(REQUIRED_FILES) - len(missing)
    add(
        "LAYOUT.FILES",
        not missing,
        ("缺: " + ",".join(missing)) if missing else "%d 份齐备" % SCANNED["docs"],
    )


def check_binding_head():
    text = read("plan/00-README总览.md") or ""
    ok = bool(BINDING_LINE.search(text))
    add(
        "LAYOUT.BINDING_HEAD",
        ok,
        "plan/00 顶部有装订行（三锚点齐）"
        if ok
        else "plan/00 顶部缺装订行（需同行：方法论名 + 布局门命令 + 装订日期）",
    )


def check_sections():
    bad = []
    for rel, needles in REQUIRED_SECTIONS.items():
        text = read(rel)
        if text is None:
            continue
        missing = [n for n in needles if n not in text]
        if missing:
            bad.append("%s: %s" % (rel, "/".join(missing)))
    add(
        "LAYOUT.SECTIONS",
        not bad,
        "；".join(bad) if bad else "%d 份小节齐备" % len(REQUIRED_SECTIONS),
    )


def collect_states():
    """逐副本采集 -> {k: set("done"|"pending")}；真值不取自任何一个副本。

    **按每份文档自己的"里程碑表"表头定位**（表头须同时含『里程碑』与『状态』两个单元格），
    只扫该表的行、扫到首条非表格行即止。理由（假门族 ⑨/⑩）：
      · 不按表头定位而扫全文时，同一文件里的**第四份副本**（承诺-证据台账，其状态列也写
        `✅ 含 5 条验收`）会被误当里程碑状态行 → M1–M5 全部"done vs pending"假红；
      · 自由文本（"当前状态：M0–M6 完成……未验证项保持 ⬜"）也不得参与判定。
    """
    states = {}
    for rel in STATUS_COPIES:
        text = read(rel)
        if text is None:
            continue
        SCANNED["copies"] += 1
        header_idx = -1
        for i, line in enumerate(text.split("\n")):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")]
            if any("里程碑" in c for c in cells) and any("状态" in c for c in cells):
                header_idx = i
                break
        if header_idx < 0:
            states.setdefault(-1, set()).add("pending")  # 视作缺陷：会让 STATUS 判红
            continue
        for line in text.split("\n")[header_idx + 2:]:
            if not line.startswith("|"):
                break
            m = STATUS_LINE.match(line)
            if not m:
                continue
            pending = any(mark in line for mark in PENDING_MARKERS)
            states.setdefault(int(m.group(1)), set()).add("pending" if pending else "done")
    return states


def check_status_agreement(states):
    conflicts = []
    for k in sorted(states):
        if k < 0:
            conflicts.append("有一份状态副本里找不到『里程碑』表头（判据表搬走了？）")
            continue
        if len(states[k]) > 1:
            conflicts.append("M%d 在副本间状态不一致（%s）" % (k, " vs ".join(sorted(states[k]))))
    add(
        "LAYOUT.STATUS",
        not conflicts,
        "；".join(conflicts)
        if conflicts
        else "%d 处副本 × %d 个里程碑 状态全一致" % (SCANNED["copies"], len(states)),
    )


def check_handoffs(done):
    missing = []
    for k in done:
        if k in EXEMPT_MILESTONES:
            continue
        rel = "plan/HANDOFF-M%d.md" % k
        text = read(rel)
        if text is None:
            missing.append("%s(缺)" % rel)
            continue
        SCANNED["handoffs"] += 1
        if k < HANDOFF_FORMAT_FROM:
            continue
        lack = [n for n in HANDOFF_SECTIONS if n not in text]
        if lack:
            missing.append("%s(缺节: %s)" % (rel, "/".join(lack)))
    add(
        "LAYOUT.HANDOFFS",
        not missing,
        "；".join(missing)
        if missing
        else "%d 份交接单齐（M0 已声明豁免）" % SCANNED["handoffs"],
    )


def check_stale_gaps(done):
    lines = (read("plan/06-交付对标与决策.md") or "").split("\n")
    header_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("|") and "缺口" in line:
            header_idx = i
            break
    if header_idx < 0:
        add("LAYOUT.GAPS", False, "plan/06 找不到含『缺口』表头的表（判据表搬走了？）")
        return
    # **按表头定位"缺口"列号**，不是"取最后一列"、也不是"行里含『缺口』二字"。
    # 首版取的是最后一列（= 关闭条件），于是"缺口格里写了已 ✅ 的里程碑"永远抓不到
    # ——变异验证 L3 抓出的真缺陷（假门族 ②）。
    header_cells = lines[header_idx].split("|")
    col = -1
    for idx, cell in enumerate(header_cells):
        if "缺口" in cell:
            col = idx
            break
    if col < 0:
        add("LAYOUT.GAPS", False, "plan/06 缺口表头里找不到『缺口』列（列名被改了？）")
        return
    stale = []
    scanned_rows = 0
    for i in range(header_idx + 2, len(lines)):
        if not lines[i].startswith("|"):
            break  # 表结束（不是"本行跳过"）——扫描面收窄，防扫到后面章节
        scanned_rows += 1
        cells = lines[i].split("|")
        cell = cells[col] if col < len(cells) else ""
        for k in done:
            if re.search(r"(^|[^0-9A-Za-z])M%d([^0-9]|$)" % k, cell):
                stale.append("plan/06 缺口列仍提 M%d: %s" % (k, cell.strip()[:80]))
    add(
        "LAYOUT.GAPS",
        not stale,
        "；".join(stale)
        if stale
        else "plan/06 缺口列扫了 %d 行，无已 ✅ 里程碑" % scanned_rows,
    )


def check_ledger(done):
    """承诺-证据台账 = 第四份状态副本，且不在状态表里（按自己的表头单独定位）。"""
    lines = (read("plan/00-README总览.md") or "").split("\n")
    header_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("|") and "承诺" in line and "状态" in line:
            header_idx = i
            break
    if header_idx < 0:
        add("LAYOUT.LEDGER", False, "plan/00 找不到『承诺-证据台账』表头（承诺项与状态列）")
        return
    SCANNED["copies"] += 1
    bad = []
    rows = 0
    for i in range(header_idx + 2, len(lines)):
        if not lines[i].startswith("|"):
            break
        rows += 1
        cells = [c.strip() for c in lines[i].split("|")]
        status = cells[-2] if len(cells) >= 2 else ""
        if not re.search(r"[⬜🟡]|未开始|待 M\d|待开工", status):
            continue
        for k in done:
            if re.search(r"(^|[^0-9A-Za-z])M%d([^0-9]|$)" % k, status, re.I):
                bad.append("台账行仍挂未完成: %s" % status[:60])
    add(
        "LAYOUT.LEDGER",
        (not bad) and rows > 0,
        "台账表 0 行——判据空跑"
        if rows == 0
        else ("；".join(bad) if bad else "台账 %d 行，已成 ✅ 的里程碑无未完成标记" % rows),
    )


def check_release_doc(done, all_milestones):
    if RELEASE_MILESTONE not in done:
        add(
            "LAYOUT.RELEASE",
            True,
            "发布里程碑 M%d 未完成，收尾记录尚不适用（已扫 %d 个 ✅ 里程碑）"
            % (RELEASE_MILESTONE, len(done)),
        )
        return
    release = read("plan/RELEASE-M%d.md" % RELEASE_MILESTONE)
    wrapup = read("plan/WRAPUP-M%d.md" % RELEASE_MILESTONE)
    if release is None and wrapup is None:
        add(
            "LAYOUT.RELEASE",
            False,
            "缺 plan/RELEASE-M%d.md 或 plan/WRAPUP-M%d.md" % (RELEASE_MILESTONE, RELEASE_MILESTONE),
        )
        return
    if release is not None:
        cols = bool(re.search(r"^##\s*一、tag 前事实", release, re.M)) and bool(
            re.search(r"^##\s*二、tag 后追加", release, re.M)
        )
        heading = bool(re.search(r"^#{2,3}.*覆盖对账", release, re.M))
        rows = len(re.findall(r"^\|.*(实现|不适用|待首推).*\|$", release, re.M))
        add(
            "LAYOUT.RELEASE",
            cols and heading and rows >= 3,
            "两栏:%s 覆盖对账小节:%s 三态行数:%d" % (cols, heading, rows),
        )
        return
    add("LAYOUT.RELEASE", True, "WRAPUP 形态")


DOC_SCAN = ["AGENTS.md", "README.md"]
TOOL_PATH = re.compile(r"tools/[\w.-]+\.(?:py|mjs|js|cjs|sh|ps1)")


def check_documented_tools(done):
    """文档点名的每条 tools/* 命令都要有实物；未到里程碑的按 PENDING_TOOLS 显式 SKIP。"""
    docs = list(DOC_SCAN)
    plan_dir = os.path.join(ROOT, "plan")
    if os.path.isdir(plan_dir):
        for name in sorted(os.listdir(plan_dir)):
            if name.endswith(".md"):
                docs.append("plan/" + name)
    referenced = set()
    scanned_docs = 0
    for rel in docs:
        text = read(rel)
        if text is None:
            continue
        scanned_docs += 1
        for m in TOOL_PATH.finditer(text):
            referenced.add(m.group(0))
    if not referenced:
        add("LAYOUT.DOC_TOOLS", False, "扫了 %d 份文档，0 处 tools/ 引用——判据是空的" % scanned_docs)
        return
    SCANNED["doc_tools"] = len(referenced)
    missing, deferred, stale = [], [], []
    for rel in sorted(referenced):
        exists = os.path.isfile(os.path.join(ROOT, rel))
        if exists:
            continue
        milestone = PENDING_TOOLS.get(rel)
        if milestone is None:
            missing.append(rel)
        elif milestone in done:
            stale.append("%s（M%d 已 ✅，登记项必须清理）" % (rel, milestone))
        else:
            deferred.append("%s(M%d)" % (rel, milestone))
    problems = missing + stale
    detail = "%d 个文档点名的脚本" % len(referenced)
    if problems:
        detail += "；问题: " + ",".join(problems)
    elif deferred:
        detail += "；%d 个待里程碑落位: %s" % (len(deferred), ",".join(deferred))
    elif deferred or not problems:
        detail += " 全部在位"
    add("LAYOUT.DOC_TOOLS", not problems, detail)


def _stdout():
    """中文输出到 GBK/cp1252 控制台会 UnicodeEncodeError —— 入口自加固（不动非文本流）。"""
    stream = sys.stdout
    enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "").replace("_", "")
    if enc not in ("utf8", "utf8mb4", "cp65001", "utf8sig"):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    return stream


def main():
    for fn in (check_required_files, check_binding_head, check_sections):
        try:
            fn()
        except Exception as exc:  # 永不崩：报一条 FAIL 并继续
            add(getattr(fn, "__name__", "check"), False, "异常: %s" % exc)

    states = collect_states()
    done = sorted(k for k, v in states.items() if "done" in v)
    all_milestones = sorted(states)
    for fn in (
        lambda: check_status_agreement(states),
        lambda: check_handoffs(done),
        lambda: check_stale_gaps(done),
        lambda: check_ledger(done),
        lambda: check_release_doc(done, all_milestones),
        lambda: check_documented_tools(done),
    ):
        try:
            fn()
        except Exception as exc:
            add("check", False, "异常: %s" % exc)

    failed = [c for c in CHECKS if not c["ok"]]
    out = _stdout()
    out.write("布局门（方法论装订） · 判据只落仓库内文件\n")
    out.write("=" * 56 + "\n")
    for c in CHECKS:
        out.write("%s  %s  %s\n" % ("PASS" if c["ok"] else "FAIL", c["id"], c["detail"]))
    out.write("=" * 56 + "\n")
    out.write(
        "这轮扫到：文档 %d / 交接单 %d / 状态副本 %d / 文档点名脚本 %d\n"
        % (SCANNED["docs"], SCANNED["handoffs"], SCANNED["copies"], SCANNED["doc_tools"])
    )
    out.write("结论: %s\n" % ("全绿" if not failed else "%d 项 FAIL" % len(failed)))
    out.flush()
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.stderr.write("check_sprint_layout: 不接受参数\n")
        sys.exit(2)
    main()
