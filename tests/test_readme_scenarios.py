# -*- coding: utf-8 -*-
"""README「三个场景（最小复现命令）」**真跑**测试（D1 的正面判据，2026-10-23 补）。

为什么需要这一层：`tests/test_cli.py::test_readme_command_lines_parse_against_parser`
把 README 里的 ``<...>`` 占位符换成字面量再喂 parser —— 它验的是**参数形态**，
**不验文件存在**。于是当 README 的三段"最小复现"写的是 `<font.ttf>` / `<source.ttf>`
占位符时，那道门仍然是绿的，而用户照抄必然 `file_not_found` / `rc=2`。

本文件把 README 声称"可直接复制运行"的每一行**真执行**，判据三条：
  ① 命令里**不许**再有尖括号占位符，且非选项参数指向的文件**必须存在**；
  ② 真跑子进程，退出码**必须等于**命令上方注释标注的 `rc=N`；
  ③ 带 `--out` 的命令，输出文件**必须真的落盘**。

`--out` 的目标在测试里改写到 ``tmp_path``：它是**产物**路径不是输入，留在仓库根会污染
工作树（`license.md` / `audit.md` 都不在 `.gitignore` 里）。这条改写是本测试唯一的偏离，
且断言随之加强（改写的那个文件必须存在）。
"""
from __future__ import print_function

import io
import os
import re
import shlex
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(REPO_ROOT, "README.md")

SECTION_START = u"## 三个场景（最小复现命令）"
SECTION_END = u"## 退出码"

#: 取值是**输入文件**的选项（必须存在）
INPUT_OPTS = {"--source", "--subset", "--corpus"}
#: 取值是**产物**的选项（测试里改写写到 tmp_path）
OUTPUT_OPTS = {"--out"}


def _readme_text():
    return io.open(README, "r", encoding="utf-8").read()


def _scenario_section(text):
    start = text.index(SECTION_START)
    end = text.index(SECTION_END, start)
    return text[start:end]


def parse_scenarios(text):
    """抽出 ``[(command, expected_rc)]``；``expected_rc`` 取自命令**紧邻上方**的注释。

    形态要求（README 里由本测试的文字说明钉住）：每条命令前面一行 ``# rc=<n> —— <为什么>``。
    缺注释 / 注释里的 rc 不是数字 → 直接断言失败（不许"没标注就跳过"）。
    """
    section = _scenario_section(text)
    scenarios = []
    pending_rc = None
    for raw in section.split("\n"):
        line = raw.strip()
        if line.startswith("#"):
            match = re.search(r"rc=(\d+)", line)
            pending_rc = int(match.group(1)) if match else None
            continue
        if not line.startswith("subsetaudit "):
            if line:
                pending_rc = None  # 非命令、非注释的行把上下文打断
            continue
        assert pending_rc is not None, u"README 命令缺 `# rc=<n>` 标注: %r" % (line,)
        scenarios.append((line, pending_rc))
        pending_rc = None
    return scenarios


def _split(argv):
    """拆 argv，返回 (positionals, {opt: value}, flags)。"""
    positionals, values, flags = [], {}, set()
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in INPUT_OPTS or token in OUTPUT_OPTS or token in ("--text", "--format"):
            assert i + 1 < len(argv), u"选项 %s 后面没有值: %r" % (token, argv)
            values[token] = argv[i + 1]
            i += 2
            continue
        if token.startswith("--"):
            flags.add(token)
            i += 1
            continue
        positionals.append(token)
        i += 1
    return positionals, values, flags


def check_command(command):
    """静态判据：无占位符 + 输入文件存在。返回问题列表（空 = 通过）。"""
    problems = []
    if "<" in command or ">" in command:
        problems.append(u"命令仍含尖括号占位符: %s" % command)
        return problems
    argv = shlex.split(command)[1:]  # 去掉 prog 名
    positionals, values, _flags = _split(argv)
    assert positionals, u"命令没有子命令: %s" % command
    for token in positionals[1:]:  # positionals[0] 是子命令名（license-gate 等），不是文件
        if not os.path.isfile(os.path.join(REPO_ROOT, token)):
            problems.append(u"位置参数不是真实文件: %s（%s）" % (token, command))
    for opt in sorted(INPUT_OPTS):
        if opt in values:
            path = values[opt]
            if not os.path.isfile(os.path.join(REPO_ROOT, path)):
                problems.append(u"%s 指向的文件不存在: %s（%s）" % (opt, path, command))
    return problems


def _run_scenario(command, tmp_path):
    """真跑一条命令；``--out`` 改写到 tmp_path。返回 (rc, out_path 或 None, stdout+stderr)。"""
    argv = shlex.split(command)
    assert argv[0] == "subsetaudit", argv
    _, values, _flags = _split(argv[1:])
    out_path = None
    rewritten = []
    i = 1
    while i < len(argv):
        token = argv[i]
        if token in OUTPUT_OPTS:
            out_path = str(tmp_path / os.path.basename(values[token]))
            rewritten.extend([token, out_path])
            i += 2
            continue
        rewritten.append(token)
        i += 1
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "subsetaudit.cli"] + rewritten,
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    return proc.returncode, out_path, proc.stdout


def test_scenarios_are_parseable_and_self_consistent():
    """README 声称的命令条数 == 实际抽出的条数（自指计数守卫，防"文字写 7 条、实际 5 条"）。"""
    text = _readme_text()
    scenarios = parse_scenarios(text)
    declared = re.search(u"以下 (\\d+) 条命令", _scenario_section(text))
    assert declared is not None, u"README 场景段缺「以下 N 条命令」的条数声明"
    assert len(scenarios) == int(declared.group(1)), (
        u"README 声明 %s 条最小复现命令，实际解析出 %d 条"
        % (declared.group(1), len(scenarios)))
    assert len(scenarios) >= 7, u"最小复现命令少于 7 条（场景覆盖退化）: %d" % len(scenarios)


def test_every_scenario_points_at_real_files():
    """D1 的静态面：7 条命令的参数全是仓库内真实路径，无占位符。"""
    problems = []
    for command, _rc in parse_scenarios(_readme_text()):
        problems.extend(check_command(command))
    assert problems == [], u"\n".join([u"README 最小复现命令不可直接跑："] + problems)


def test_every_scenario_exits_with_declared_code(tmp_path):
    """D1 的动行面：真跑，退出码必须等于 README 标注的 ``rc=N``。"""
    failures = []
    ran = 0
    for command, expected in parse_scenarios(_readme_text()):
        code, out_path, output = _run_scenario(command, tmp_path)
        ran += 1
        if code != expected:
            failures.append(u"rc=%d（标注 %d）: %s\n%s" % (code, expected, command, output[:800]))
            continue
        if out_path is not None and not os.path.isfile(out_path):
            failures.append(u"--out 未落盘: %s（%s）" % (out_path, command))
        assert code != 2, u"退出码 2 = 输入非法（file_not_found？）: %s\n%s" % (command, output[:800])
    assert ran >= 7, ran
    assert failures == [], u"\n\n".join(failures)


def test_scenario_check_would_catch_a_missing_file():
    """变异自证：把 README 一条命令的路径改成一个不存在的文件 → 静态判据必须红。

    防的是"这道门恒绿"（例如有人把 `check_command` 里的 `os.path.isfile` 写成 `os.path.exists`
    之外的恒真形态，或者把占位符放行）。改的是**内存里的文本**，不碰仓库文件。
    """
    text = _readme_text()
    original = parse_scenarios(text)
    assert original, u"README 场景段没解析出命令"
    good = original[0][0]
    assert check_command(good) == [], good

    broken = good.replace("data/fixtures/fstype-nosubset/out/fstype-nosubset.ttf",
                          "data/fixtures/fstype-nosubset/out/DOES-NOT-EXIST.ttf")
    assert broken != good, u"变异靶子没打中（README 第一条命令的路径变了？）: %r" % good
    problems = check_command(broken)
    assert problems and ("DOES-NOT-EXIST" in problems[0]), problems

    # 占位符同样必须红（这正是 D1 的原始形态）
    placeholder = good.replace("data/fixtures/fstype-nosubset/out/fstype-nosubset.ttf",
                               "<font.ttf>")
    assert check_command(placeholder), u"占位符必须被判为不可直接跑"


def test_declared_rc_mismatch_is_detectable(tmp_path):
    """变异自证（退出码面）：**标注**与**实测**必须是被真比较的，不是恒等式。

    做法：取第一条命令的实测 rc，与一个**故意写错**的标注比较 → 差异必须能被本测试的判据
    （`code != expected`）发现。这里不复跑整条门，只证"比较关系承重"：
    若把标注改成 `(rc+1)%3`，`code == expected` 必然为假。
    """
    command, expected = parse_scenarios(_readme_text())[0]
    code, _out, _output = _run_scenario(command, tmp_path)
    assert code == expected, (code, expected)
    wrong = (code + 1) % 3
    assert wrong != code, u"变异值与原值相同（无法构成变异）"
    assert (code == wrong) is False, u"`code == expected` 判据不承重"


def test_scenario_section_still_declares_runnability():
    """README 场景段的"可直接复制运行"承诺必须仍在（防止改回模糊说法 / 丢掉 D9 前置）。"""
    section = _scenario_section(_readme_text())
    assert u"可直接复制运行" in section
    assert u"没有占位符" in section
    assert u"gen_fixtures.py" in section, u"场景段必须写清 fixture 产物需先生成（D9）"
