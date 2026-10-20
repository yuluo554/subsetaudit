# -*- coding: utf-8 -*-
"""规范层：Finding / SKIPPED / Report 的**唯一**构造与序列化入口。

三件事只在这里决定（别在模块里各写一套）：
  1. 键序（构造处固定，不用 ``sort_keys``）；
  2. 排序键 ``(module, severity 序, primary_key)``；
  3. 序列化参数（``ensure_ascii=False``、``indent=2``、末尾单个换行）。

确定性纪律：报告不含时间戳 / 绝对路径 / 主机名 / 用户名。
"""
from __future__ import print_function

import hashlib
import json
import os

SCHEMA = "subsetaudit/report@1"

DISCLAIMER = "技术判定，不是法律意见；每条结论可回指 spec_ref 或实测证据。"

# 排序序 = 此序（越靠前越严重）
SEVERITIES = ("error", "warn", "note")
_SEVERITY_RANK = {name: i for i, name in enumerate(SEVERITIES)}

MODULES = (
    "license-gate",
    "coverage-diff",
    "layout-survival",
    "metadata",
    "report",
)


class InputError(Exception):
    """输入非法 —— 由 CLI 收口为退出码 2，绝不降级成 finding。"""

    def __init__(self, path, reason):
        self.path = path
        self.reason = reason
        Exception.__init__(self, "%s: %s" % (reason, path))


def finding(module, code, severity, primary_key, message, evidence=None, spec_ref=None):
    """构造一条 finding。``evidence`` 的键由各模块自定，但必须可复算。"""
    if module not in MODULES:
        raise ValueError("unknown module: %r" % (module,))
    if severity not in _SEVERITY_RANK:
        raise ValueError("unknown severity: %r" % (severity,))
    return {
        "module": module,
        "code": code,
        "severity": severity,
        "primary_key": str(primary_key),
        "message": message,
        "evidence": dict(evidence or {}),
        "spec_ref": spec_ref,
    }


def skipped(module, reason, detail=""):
    """``SKIPPED(reason=...)`` 恒为 note、恒进输出、恒不影响退出码。"""
    if module not in MODULES:
        raise ValueError("unknown module: %r" % (module,))
    return {"module": module, "reason": reason, "detail": detail}


def sort_findings(items):
    return sorted(
        items,
        key=lambda f: (
            f["module"],
            _SEVERITY_RANK.get(f["severity"], len(SEVERITIES)),
            f["primary_key"],
            f["code"],
        ),
    )


def sort_skipped(items):
    return sorted(items, key=lambda s: (s["module"], s["reason"], s["detail"]))


def has_error(items):
    return any(f["severity"] == "error" for f in items)


def input_ref(path):
    """输入的**逻辑名**：只留 basename，绝不写绝对路径（脱敏与确定性双要求）。"""
    return os.path.basename(path.replace("\\", "/"))


def build_report(findings, skips, inputs, summary=None, tool_version=None, fonttools_version=None):
    """组装规范报告：键序在此固定。"""
    findings = sort_findings(findings)
    skips = sort_skipped(skips)
    body = {
        "schema": SCHEMA,
        "disclaimer": DISCLAIMER,
        "tool": {
            "name": "subsetaudit",
            "version": tool_version,
            "fonttools_version": fonttools_version,
        },
        "inputs": dict(inputs),
        "summary": dict(summary or {}),
        "findings": findings,
        "skipped": skips,
    }
    body["summary"].setdefault("error", sum(1 for f in findings if f["severity"] == "error"))
    body["summary"].setdefault("warn", sum(1 for f in findings if f["severity"] == "warn"))
    body["summary"].setdefault("note", sum(1 for f in findings if f["severity"] == "note"))
    body["summary"].setdefault("skipped", len(skips))
    return body


def dumps(report):
    """规范 JSON：固定 indent、非 ASCII 原样输出、末尾恰好一个换行。"""
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def digest(report):
    return hashlib.sha256(dumps(report).encode("utf-8")).hexdigest()


def render_markdown(report):
    """人读视图：只是渲染，不参与 digest、不参与退出码。"""
    lines = []
    summary = report.get("summary", {})
    lines.append("# SubsetAudit 报告")
    lines.append("")
    lines.append("> " + report.get("disclaimer", DISCLAIMER))
    lines.append("")
    tool = report.get("tool", {})
    lines.append(
        "- 版本：`%s`（fontTools `%s`）" % (tool.get("version"), tool.get("fonttools_version"))
    )
    inputs = report.get("inputs", {})
    if inputs:
        lines.append(
            "- 输入：" + "、".join("%s=`%s`" % (k, v) for k, v in sorted(inputs.items()))
        )
    lines.append(
        "- 汇总：error %s / warn %s / note %s / skipped %s"
        % (
            summary.get("error", 0),
            summary.get("warn", 0),
            summary.get("note", 0),
            summary.get("skipped", 0),
        )
    )
    lines.append("")
    lines.append("## 发现")
    lines.append("")
    findings = report.get("findings", [])
    if not findings:
        lines.append("（无）")
    else:
        lines.append("| 模块 | 级别 | 代码 | 主键 | 说明 | 依据 |")
        lines.append("|---|---|---|---|---|---|")
        for f in findings:
            lines.append(
                "| %s | %s | `%s` | `%s` | %s | %s |"
                % (
                    f["module"],
                    f["severity"],
                    f["code"],
                    f["primary_key"],
                    f["message"].replace("|", "\\|"),
                    ("`%s`" % f["spec_ref"]) if f.get("spec_ref") else "—",
                )
            )
    lines.append("")
    lines.append("## 跳过")
    lines.append("")
    skips = report.get("skipped", [])
    if not skips:
        lines.append("（无）")
    else:
        for s in skips:
            lines.append("- `%s` SKIPPED(reason=%s) %s" % (s["module"], s["reason"], s["detail"]))
    return "\n".join(lines) + "\n"
