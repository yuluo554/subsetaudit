# -*- coding: utf-8 -*-
"""M5 · `report` 报告与 CI 契约 —— 真实实现（聚合的唯一路径）。

    evaluate(source=None, subset=None, required=None) -> report_dict

**口径单点 = `data/README.md` §六.9.7**：
  · 聚合 + 组装**只在这里**；`cli._run_report` 只做参数翻译，不得再自己合并各模块 summary；
  · 模块固定顺序 `license-gate → metadata → layout-survival → coverage-diff`（跑不跑由参数决定，
    顺序由 `MODULE_ORDER` 决定 —— 那张表是承重的）；
  · 顶级 `summary` 键**不得**跨模块重复 —— 静默覆盖是缺陷 → `SUMMARY_KEY_COLLISION`（`error`）；
  · `summary.modules` 列出实际跑过的模块（空跑写 `[]`），让"某个模块没跑"在报告里可见。

退出码仍只在 `cli.main` 收口（K2）；本模块只产出报告体。
确定性：finding 统一由 ``canonical.build_report`` 排序，汇总键序由构造处固定。
"""
from __future__ import print_function

from . import __version__, canonical, coverage_diff, layout_survival, license_gate, metadata
from ._skeleton import validate_inputs
from .canonical import finding, input_ref

MODULE = "report"

#: §六.9.7 的固定模块顺序（也是 `summary.modules` 的顺序）
MODULE_ORDER = ("license-gate", "metadata", "layout-survival", "coverage-diff")

#: §六.9.7 键冲突的 finding 码（聚合层的**唯一**判定）
CODE_KEY_COLLISION = "SUMMARY_KEY_COLLISION"
COLLISION_SPEC_REF = "data/README §6.9"


def build(findings, skips, inputs, summary=None):
    """把各模块结果组装成规范报告（真实实现，M0 即可用）。

    ``tool`` 只带本包版本；**不带 fontTools 版本**（决策 D-M7-1，见 `canonical.build_report`
    docstring）—— 环境相关量进报告会让"跨环境逐字节一致"不可证。
    """
    return canonical.build_report(
        findings,
        skips,
        inputs,
        summary=summary,
        tool_version=__version__,
    )


def merge_summaries(parts):
    """把 ``[(module, summary), ...]`` 合并成一个 summary，并**报出键冲突**（§六.9.7）。

    返回 ``(merged, owners)``：`owners` = ``{顶级键: [用过它的模块, ...]}``（顺序即 `parts` 顺序）。
    **保留先到者**（顺序即 `MODULE_ORDER`），但用过的模块全记下来 —— 静默覆盖是缺陷。
    """
    merged = {}
    owners = {}
    for module, summary in parts:
        for key in (summary or {}):
            owners.setdefault(key, []).append(module)
            if key not in merged:
                merged[key] = summary[key]
    return merged, owners


def _collision_findings(owners):
    out = []
    for key in sorted(key for key, who in owners.items() if len(who) > 1):
        out.append(finding(
            MODULE, CODE_KEY_COLLISION, "error", key,
            "summary 顶级键 `%s` 被多个模块同时使用（%s）→ 先到者保留，后到者不覆盖"
            % (key, " / ".join(owners[key])),
            evidence={"key": key, "modules": list(owners[key])},
            spec_ref=COLLISION_SPEC_REF,
        ))
    return out


def aggregate(source=None, subset=None, required=None):
    """跑得起来的模块各跑一次，返回 ``(findings, skips, summary, modules)``。

    顺序与条件严格照 §六.9.7：`--source` → license-gate；`--subset` → metadata；
    两侧都有 → layout-survival；`--source` 且有需求集 → coverage-diff。
    **跑的顺序由 `MODULE_ORDER` 说了算**（这张表是承重的，不是注释）。
    """
    runners = {
        "license-gate": (
            bool(source),
            lambda: license_gate.evaluate(source),
        ),
        "metadata": (
            bool(subset),
            lambda: metadata.evaluate(subset, source_path=source),
        ),
        "layout-survival": (
            bool(source and subset),
            lambda: layout_survival.evaluate(source, subset),
        ),
        "coverage-diff": (
            bool(source and required is not None),
            lambda: coverage_diff.evaluate(source, required, subset_path=subset),
        ),
    }

    findings, skips = [], []
    parts = []
    for module in MODULE_ORDER:
        enabled, runner = runners[module]
        if not enabled:
            continue
        f, s, body = runner()
        findings += f
        skips += s
        parts.append((module, body))

    modules = [name for name, _body in parts]
    merged, owners = merge_summaries(parts)
    collisions = sorted(key for key, who in owners.items() if len(who) > 1)
    if collisions:
        findings += _collision_findings(owners)
        merged["summary_key_collisions"] = collisions
    merged["modules"] = modules
    return findings, skips, merged, modules


def evaluate(source=None, subset=None, required=None):
    """报告聚合（**唯一路径**）：返回规范报告体。退出码由 `cli.main` 收口。"""
    validate_inputs([source, subset])  # 不可读 / 非字体 → InputError → 退出码 2

    findings, skips, summary, _modules = aggregate(source, subset, required)
    inputs = {}
    if source:
        inputs["source"] = input_ref(source)
    if subset:
        inputs["subset"] = input_ref(subset)
    return build(findings, skips, inputs, summary)
