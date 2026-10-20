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