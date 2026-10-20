# -*- coding: utf-8 -*-
"""M5 · `report` 报告与 CI 契约 —— **M0 骨架**。

签名与返回形状（M5 填实，接口不改）：

    evaluate(findings_by_module, skips, inputs, summaries) -> (report_dict)

M5 的实现要点（见 `plan/03` §5）：
  · 消费 M2–M4 的原始结果，产出规范 JSON（`findings[]` + `summary` + `inputs`）或 Markdown 渲染视图；
  · 退出码 0 / 1 / 2 的唯一收口点（在 `cli.py`）；
  · finding 带 `module` / `severity` / `evidence` / `spec_ref`；`SKIPPED(reason=...)` 必须出现在输出里；
  · 不写扫描时刻 / 绝对路径 / 主机名 / 用户名；键序与排序键固定。

M0 阶段：`build` 已具备**真实实现**（它只是 `canonical` 的薄封装，与里程碑无关）；
本模块的"聚合多个模块结果 + 渲染"部分在 M5 补齐。
"""
from __future__ import print_function

from . import __version__, canonical
from ._skeleton import NOT_IMPLEMENTED
from .canonical import skipped

MODULE = "report"


def build(findings, skips, inputs, summary=None):
    """把各模块结果组装成规范报告（真实实现，M0 即可用）。"""
    try:
        import fontTools
        ft_version = getattr(fontTools, "version", "unknown")
    except ImportError:  # pragma: no cover - fontTools 是运行期依赖，缺了应报输入错误
        ft_version = "absent"
    return canonical.build_report(
        findings,
        skips,
        inputs,
        summary=summary,
        tool_version=__version__,
        fonttools_version=ft_version,
    )


def evaluate(*args, **kwargs):
    """M0 骨架：聚合与渲染调度在 M5 填实。"""
    return (
        [],
        [skipped(MODULE, NOT_IMPLEMENTED, "报告聚合在 M5 实现；M0 已可直接用 canonical 序列化")],
        {},
    )