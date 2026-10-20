# -*- coding: utf-8 -*-
"""M5 · `metadata` 元数据与位域一致性 —— **M0 骨架**。

签名与返回形状（M5 填实，接口不改）：

    evaluate(subset_path, source_path=None) -> (findings, skips, summary)

M5 的实现要点（见 `plan/03` §5、`data/README.md` §六）：
  · name 存活报告（name ID 0 / 7 / 11 / 13 / 14 / 16 / 17），缺 13/14 分两类：
    "默认剥离"（给了 `--source` 且原文有）与"原作者没写"（原文也没有）；
  · `OS/2` 位域 ↔ cmap 实测集合的**交叉一致性**（按位比对，不得只比"是否为 0"）；
  · `maxp.numGlyphs` vs 实际字形数；`usFirstCharIndex/usLastCharIndex` 与 cmap 范围。

M0 阶段：**显式跳过，不伪造判定**。
"""
from __future__ import print_function

from ._skeleton import skeleton_result, validate_inputs
from .canonical import skipped

MODULE = "metadata"


def evaluate(subset_path, source_path=None):
    """M0 骨架：先校验输入（不可读/非字体 → 退出码 2），再显式跳过判定。"""
    validate_inputs([subset_path, source_path])
    return skeleton_result(MODULE, "元数据与位域一致性在 M5 实现；M0 只保证命令可解析、输入校验与退出码正确")