# -*- coding: utf-8 -*-
"""M2 · `license-gate` 许可闸门 —— **M0 骨架**。

签名与返回形状（M2 填实，接口不改）：

    evaluate(path) -> (findings, skips, summary)

M2 的实现要点（见 `plan/03` §2、`data/README.md` §三 / §六.1）：
  · 先读 ``OS/2.version``，再判 `bits = fsType & 0x000F`；
  · v0–v2 多位置位 → 取最宽松（**不得**报互斥违规）；v3+ 多位置位 → 互斥违规 `error`；
  · bit8 `0x0100` → `may_subset=false`；bit9 `0x0200` → bitmap only；
  · 保留位掩码 `0xFCF1` 置位单列；
  · 五元结论 `{embed_pdf, embed_app, embed_web, may_subset, may_modify}` 的**每一条判定式**必须先写进
    `data/README.md` §六.1（口径单点），再在代码里实现——**不许在代码里现编**。
  · 每条 finding 必带 `spec_ref`。

M0 阶段：**显式跳过，不伪造判定**。
"""
from __future__ import print_function

from ._skeleton import skeleton_result, validate_inputs
from .canonical import skipped

MODULE = "license-gate"


def evaluate(path):
    """M0 骨架：先校验输入（不可读/非字体 → 退出码 2），再显式跳过判定。"""
    validate_inputs([path])
    return skeleton_result(MODULE, "许可闸门在 M2 实现；M0 只保证命令可解析、输入校验与退出码正确")