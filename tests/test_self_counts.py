# -*- coding: utf-8 -*-
"""自述测试计数守门（D3 的常驻判据，2026-10-23 补）。

## 为什么需要这道门

`plan/05-里程碑.md:128` 曾写「全量 **278 项**」，而实测是 **280 项**（`--collect-only` 与真跑
都是 280）；`278` 在任何配置下都复现不出来。布局门 `LAYOUT.STATUS` 只判里程碑状态
（✅/⬜），**不判正文里的数字** —— 于是"文档写一个数、实测另一个数"可以长期共存。

## 判据

`plan/05-里程碑.md` 里 `全量 **N 项**` 这个 N 必须等于 `pytest --collect-only` 的实测条数。
文档**声明范围**也一并钉住：`plan/05` 的 M5 段落必须指向本文件存在的那些测试模块。

## 为什么不写成"硬编码期望值"

硬编码任何一个数字都会在**下一次加测试时**变成新的陈旧值（这正是 D3 的成因）。
本门**动态取真值**：加测试 → 收集数变 → 文档必须同轮改，不改就红。

## 何时需要人工介入

只有当有人**故意**改 `plan/05` 的措辞、让正则匹配不到 `全量 **N 项**` 时。那时
`test_plan_declares_a_full_suite_count` 会红（"找不到声明"不是通过），逼人显式处理。
"""
from __future__ import print_function

import io
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(REPO_ROOT, "plan", "05-里程碑.md")

#: 文档里的声明形态：`全量 **N 项**`
DECLARED = re.compile(u"全量 \\*\\*(\\d+) 项\\*\\*")


def _plan_text():
    return io.open(PLAN, "r", encoding="utf-8").read()


def _collected_count():
    """跑一次 `--collect-only -q` 取实测条数（子进程，避免测试内自引用）。"""
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", "-o", "addopts=", "--collect-only", "-q"],
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    assert proc.returncode == 0, proc.stdout[-2000:]
    match = re.search(r"(\d+) tests? collected", proc.stdout)
    assert match is not None, "解析不出收集数:\n%s" % proc.stdout[-2000:]
    return int(match.group(1))


def test_plan_declares_a_full_suite_count():
    """声明必须存在且只有一处（多处声明 = 又是"同一事实几个值"）。"""
    found = DECLARED.findall(_plan_text())
    assert found, "`plan/05-里程碑.md` 里找不到 `全量 **N 项**` 的声明（措辞被改过？）"
    assert len(found) == 1, "全量测试数出现 %d 处声明（%s）—— 同一事实只许一处" % (
        len(found), ",".join(found))


def test_declared_count_matches_actual_collection():
    """文档里的全量测试数 == 实测收集数（D3 的正面判据）。"""
    declared = int(DECLARED.findall(_plan_text())[0])
    actual = _collected_count()
    assert declared == actual, (
        "`plan/05-里程碑.md` 写全量 %d 项，实测 %d 项。\n"
        "**判据**：加/删测试后必须同轮更新文档里的这个数字（这是合法口径调整）；\n"
        "不许反过来把测试删到凑数字。" % (declared, actual))


def test_gate_would_catch_a_stale_number():
    """变异自证：文档数字与实测不符时，本门**必须**红（不是恒等式）。

    在**内存里**构造一份"写错数字"的文本验证判据承重，不碰仓库文件。
    """
    text = _plan_text()
    declared = int(DECLARED.findall(text)[0])
    stale = text.replace(u"全量 **%d 项**" % declared, u"全量 **%d 项**" % (declared + 1), 1)
    assert stale != text, "变异靶子没打中"
    mutated = int(DECLARED.findall(stale)[0])
    actual = _collected_count()
    assert mutated != actual, "把数字改错之后仍与实测相同 —— 判据不承重"
    assert declared == actual, "当前文档数字应与实测一致（否则本门此刻就该红）"


@pytest.mark.parametrize("rel", [
    "tests/test_readme_scenarios.py",
    "tests/test_cross_channel.py",
])
def test_new_gates_are_real_files(rel):
    """本次迭代新增的两道门必须真的在盘上（防止"文档说有门、实物没有"）。"""
    assert os.path.isfile(os.path.join(REPO_ROOT, rel)), rel
