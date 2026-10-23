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

#: 变异组数声明形态（`plan/05-里程碑.md`）：`**N 组**（布局 L / 脱敏 V / **发布 R**）`
MUTANTS = re.compile(u"\\*\\*(\\d+) 组\\*\\*（布局 (\\d+) / 脱敏 (\\d+) / \\*\\*发布 (\\d+)\\*\\*）")

VERIFY_GATES = os.path.join(REPO_ROOT, "tools", "verify_gates.py")


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


# ── 变异组数：同一事实在文档里也曾出现三个值（D3 的第二种形态）────────────────
#
# 2026-10-23 实测：`verify_gates.py` 的靶子是 L×12 + V×4 + R×9 = **25**，而当时
# `plan/05` 写 24、README 写 24、`plan/RELEASE-M6.md` 写 26 —— 三个值，只有一个是真值。
# 与"全量测试数"同根因（v0.1.1 加 R9 后没人回头改文档），所以同一种判据：**动态取真值**。
#
# 判据范围刻意窄：只钉 `plan/05` 的那一处声明（`tests/test_self_counts.py` 的既有纪律是
# "同一事实只许一处声明"）。历史时点的组数（HANDOFF-M6 里 M6 当时的 24）不参与对账。

def _mutation_ids():
    """从 `verify_gates.py` 的靶子表里解析出 (前缀, 序号) —— 权威真值，不读文档。"""
    text = io.open(VERIFY_GATES, "r", encoding="utf-8").read()
    found = re.findall(u'\\(\\s*"([LVR])(\\d+)"\\s*,', text)
    assert found, "解析不出 `verify_gates.py` 的靶子 id（表结构被改过？）"
    groups = {}
    for prefix, number in found:
        groups.setdefault(prefix, set()).add(int(number))
    return {prefix: len(ids) for prefix, ids in groups.items()}


def test_plan_declares_mutation_group_count():
    """`plan/05` 必须声明变异组数，且只有一处。"""
    found = MUTANTS.findall(_plan_text())
    assert found, "`plan/05-里程碑.md` 里找不到变异组数声明（形如 `**N 组**（布局 L / 脱敏 V / **发布 R**）`）"
    assert len(found) == 1, "变异组数出现 %d 处声明（%s）—— 同一事实只许一处" % (
        len(found), found)


def test_declared_mutation_count_matches_source():
    """文档声明的组数（总数与三组分解）必须等于 `verify_gates.py` 的靶子实数。"""
    total, layout, desens, release = (int(x) for x in MUTANTS.findall(_plan_text())[0])
    actual = _mutation_ids()
    assert (layout, desens, release) == (
        actual.get("L"), actual.get("V"), actual.get("R")), (
        "`plan/05` 写 布局 %d / 脱敏 %d / 发布 %d，实测 布局 %s / 脱敏 %s / 发布 %s"
        % (layout, desens, release,
           actual.get("L"), actual.get("V"), actual.get("R")))
    assert total == sum(actual.values()), (
        "`plan/05` 写共 %d 组，实测共 %d 组（%s）。\n"
        "**判据**：加/删变异靶子后必须同轮更新文档里的这个数字（这是合法口径调整）；\n"
        "不许反过来把靶子删到凑数字。" % (total, sum(actual.values()), actual))


def test_mutation_count_gate_would_catch_a_stale_number():
    """变异自证：组数写错时本门必红（在内存里构造，不碰仓库文件）。"""
    text = _plan_text()
    total = int(MUTANTS.findall(text)[0][0])
    stale = text.replace(u"**%d 组**" % total, u"**%d 组**" % (total + 1), 1)
    assert stale != text, "变异靶子没打中"
    declared_stale = int(MUTANTS.findall(stale)[0][0])
    assert declared_stale != sum(_mutation_ids().values()), (
        "把组数改错后仍与实测相同 —— 判据不承重")
    assert total == sum(_mutation_ids().values()), "当前文档组数应与实测一致"
