# -*- coding: utf-8 -*-
"""CI 接线测试：workflow YAML 本地解析 + 步骤断言。

为什么要在本地解析：**step ``name`` 里一个裸 ``: `` 会让 GitHub 直接不建 job**
（run 显示 failure 而 ``jobs=0``，文件字节一切正常）。这类缺陷只有解析器能当场抓住，
推到远端看红太晚。
"""
from __future__ import print_function

import io
import os

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(io.open(WORKFLOW, "r", encoding="utf-8").read())


def test_workflow_parses_and_has_exactly_one_job(workflow):
    assert "jobs" in workflow and list(workflow["jobs"]) == ["test"]


def test_workflow_triggers_on_push_and_pull_request(workflow):
    # PyYAML 会把裸 `on:` 读成布尔 True —— 两种形态都接受（关键是"有触发"）
    triggers = workflow.get("on", workflow.get(True))
    assert triggers is not None
    assert "push" in triggers and "pull_request" in triggers


def test_every_step_has_a_name_and_no_bare_colon_in_name(workflow):
    steps = workflow["jobs"]["test"]["steps"]
    assert len(steps) >= 8, "步骤数少于预期（少了一条门=少了一条证据）"
    for step in steps:
        name = step.get("name", "")
        assert name, "step 缺 name: %r" % (step,)
        assert "run" in step or "uses" in step, step
        # 裸 ": " 是 GitHub 不建 job 的已知诱因（本项目 M0 已改掉一处）
        assert ": " not in name, "step name 含裸 ': '：%r" % name


def test_layout_and_desensitized_gates_are_ci_steps(workflow):
    runs = "\n".join(step.get("run", "") for step in workflow["jobs"]["test"]["steps"])
    assert "tools/check_sprint_layout.py" in runs, "布局门必须有 CI 步骤"
    assert "tools/check_desensitized.py" in runs, "脱敏门必须有 CI 步骤"
    assert "tools/verify_gates.py" in runs, "门变异验证必须有 CI 步骤"
    assert "tools/smoke_cli.py" in runs, "离线冒烟必须有 CI 步骤"


def test_m1_data_layer_has_ci_steps(workflow):
    """M1 数据层：生成器全量跑 + `--check` + 离线 `fetch_fonts --check` 三件都必须在 CI 里。

    "本地跑过"不是证据 —— 这三条正是 M1 DoD 的可复现面，必须在每个矩阵格子里跑。
    """
    runs = "\n".join(step.get("run", "") for step in workflow["jobs"]["test"]["steps"])
    assert "tools/gen_fixtures.py" in runs, "生成器必须有 CI 步骤（否则产物无从重建）"
    assert "tools/gen_fixtures.py --check" in runs, "位级一致必须有 CI 步骤"
    assert "tools/fetch_fonts.py --check" in runs, "离线锁文件校验必须有 CI 步骤"


def test_ci_checks_generator_before_check_mode(workflow):
    """顺序判据：必须先**生成**再 `--check`，否则 `--check` 只会报"产物缺失"。

    这条防的是"两个步骤都在、但顺序写反 → 永远红/永远假绿"。
    """
    steps = workflow["jobs"]["test"]["steps"]
    gen_idx = check_idx = None
    for i, step in enumerate(steps):
        run = step.get("run", "")
        if "tools/gen_fixtures.py --check" in run:
            check_idx = i
        elif "tools/gen_fixtures.py" in run:
            gen_idx = i
    assert gen_idx is not None and check_idx is not None
    assert gen_idx < check_idx, "生成步骤必须在 --check 之前（实得 %r < %r）" % (gen_idx, check_idx)


def test_ci_installs_dependencies_before_scripts_that_need_them(workflow):
    """顺序判据：**运行期**需要 fontTools 的脚本必须在 ``pip install`` **之后**。

    实测背景（2026-10-21 M1）：`gen_fixtures.py` 与 `fetch_fonts.py` 都 import fontTools。
    把数据层步骤放在 install 之前 → 四个矩阵格子全红，而且红在"环境"而不是"判据"上。

    **2026-10-21 M6 首推实测**：`verify_gates.py` 也进这张表了 —— 它自己仍是 stdlib-only，
    但它现在会连**发布门**一起跑，而发布门要复跑 `gen_fixtures.py --check`。首次推送时
    `verify_gates.py` 在 install 之前 → 四格子同红，红在
    `RELEASE.FIXTURES_BITWISE gen_fixtures --check rc=1 ModuleNotFoundError: fontTools`。
    "顶层 import 干净"与"运行期依赖是否就位"是两件事，这张表管的是后者。
    """
    steps = workflow["jobs"]["test"]["steps"]
    install_idx = None
    for i, step in enumerate(steps):
        if "pip install" in step.get("run", "") and "-e" in step.get("run", ""):
            install_idx = i
            break
    assert install_idx is not None, "找不到 editable 安装步骤"

    needs_fonttools = ["tools/gen_fixtures.py", "tools/fetch_fonts.py", "tools/verify_gates.py"]
    for i, step in enumerate(steps):
        run = step.get("run", "")
        for script in needs_fonttools:
            if script in run:
                assert i > install_idx, \
                    "%s 在 install（第 %d 步）之前（第 %d 步）—— 会因缺 fontTools 而红" % (
                        script, install_idx, i)


def test_release_gate_is_a_ci_step():
    """M6 的发布门必须在 CI 里跑（`--pre-tag` 档）——"本地跑过"不是证据。"""
    workflow = yaml.safe_load(io.open(WORKFLOW, "r", encoding="utf-8").read())
    runs = "\n".join(step.get("run", "") for step in workflow["jobs"]["test"]["steps"])
    assert "tools/check_release.py --pre-tag" in runs, "发布门（--pre-tag）必须有 CI 步骤"


def test_ci_generates_fixtures_before_any_gate_that_checks_them(workflow):
    """顺序判据：**产物必须先于"检查产物"的步骤生成**。

    实测背景（2026-10-21 M6 首推）：`verify_gates.py` 与发布门都会复跑
    `gen_fixtures.py --check`，而 `--check` 是比较"重生成"与"仓库产物"。
    `data/fixtures/**/out/` 是 gitignore 的 → 干净 checkout 里**没有产物**，
    于是"先跑门、后生成"的顺序会让 `RELEASE.FIXTURES_BITWISE` 报"发现 N 处不一致"。
    这条判据把"生成必须排在它们之前"钉死。
    """
    steps = workflow["jobs"]["test"]["steps"]
    gen_idx = None
    for i, step in enumerate(steps):
        run = step.get("run", "")
        if "tools/gen_fixtures.py" in run and "--check" not in run:
            gen_idx = i
            break
    assert gen_idx is not None, "找不到 fixture 生成步骤"

    for i, step in enumerate(steps):
        run = step.get("run", "")
        for script in ("tools/verify_gates.py", "tools/check_release.py"):
            if script in run:
                assert i > gen_idx, \
                    "%s 在第 %d 步，生成在第 %d 步 —— 产物还没生成，它的 --check 只会报缺失" % (
                        script, i, gen_idx)


def test_gate_scripts_are_stdlib_only():
    """门脚本**顶层只依赖标准库** —— 这是"门能在干净 checkout、未装依赖时跑"的前提。

    判据落在**门脚本的顶层 import**上：出现 fontTools / 第三方包即红。
    注意这只保证"脚本自己能起来"，**不保证它编排的被测门不需要依赖**：`verify_gates.py`
    与 `check_release.py` 会长出子进程去跑 `gen_fixtures.py --check`（要 fontTools）——
    那件事由 `test_ci_installs_dependencies_before_scripts_that_need_them` 管。
    """
    import ast

    allowed = {"__future__", "io", "os", "re", "sys", "json", "hashlib", "subprocess",
               "shutil", "argparse", "struct", "unicodedata", "zipfile", "tempfile",
               "textwrap", "collections", "itertools", "errno", "ast"}
    for name in ("check_sprint_layout.py", "check_desensitized.py", "verify_gates.py",
                 "check_release.py"):
        path = os.path.join(REPO_ROOT, "tools", name)
        tree = ast.parse(io.open(path, "r", encoding="utf-8").read())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mods.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
        extra = sorted(m for m in mods if m not in allowed)
        assert extra == [], "%s 顶层 import 了非标准库模块: %s（门必须能在未装依赖时跑）" % (
            name, extra)


def test_ci_uses_python_not_windows_only_py_launcher(workflow):
    """`py` 是 Windows 专用启动器，ubuntu runner 上没有 —— 用了就四矩阵同点红。"""
    for step in workflow["jobs"]["test"]["steps"]:
        run = step.get("run", "")
        for line in run.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue
            assert not stripped.startswith("py "), "CI 里不许用 `py` 启动器: %r" % stripped


def test_ci_sets_utf8_env_for_all_steps(workflow):
    env = workflow["jobs"]["test"].get("env", {})
    assert str(env.get("PYTHONUTF8")) == "1", "CI 必须设 PYTHONUTF8=1（本机 -X utf8 救不了 CI）"


def test_ci_actions_are_on_v7_or_newer(workflow):
    """`actions/checkout` 与 `actions/setup-python` 必须 ≥ v7（D4，2026-10-23）。

    实测背景：v4 / v5 会在每个 job 上产生一条 `Node.js 20 is deprecated` 注解
    （四格子 = 4 条/次），且 Node 20 本身已进入弃用期。升到 v7 后注解归零。
    **判据是"版本 ≥ 7"而不是"恰好等于 v7"**：将来升 v8 时本测试不该红。
    """
    uses = [step.get("uses", "") for step in workflow["jobs"]["test"]["steps"]]
    for action in ("actions/checkout@", "actions/setup-python@"):
        matches = [u for u in uses if u.startswith(action)]
        assert matches, "CI 里找不到 %s（步骤被删了？）" % action
        for ref in matches:
            tag = ref.split("@", 1)[1]
            assert tag.startswith("v"), ref
            major = tag[1:].split(".", 1)[0]
            assert major.isdigit(), "解析不出 action 主版本: %r" % ref
            assert int(major) >= 7, "%s 低于 v7（Node20 弃用注解会回来）: %r" % (action, ref)