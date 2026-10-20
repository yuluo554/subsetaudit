# -*- coding: utf-8 -*-
"""M4 · `layout-survival` 布局保真 —— **M0 骨架**。

签名与返回形状（M4 填实，接口不改）：

    evaluate(source_path, subset_path) -> (findings, skips, summary)

M4 的实现要点（见 `plan/03` §4、`data/README.md` §六.5）：
  · GSUB/GPOS Header → ScriptList → FeatureList → LookupList → FeatureVariations；
  · **LookupType 7（Extension）必须解包 `ExtSubTable`**，否则整棵子树读不到
    （朴素遍历与解包后的计数必须分开报：`naive` 只作对照，不作结论）；
  · 输出丢失的 `(script, langsys, feature)` 三元组、涉及必需字符的连字规则、lookup 计数。

M0 阶段：**显式跳过，不伪造判定**。
"""
from __future__ import print_function

from ._skeleton import skeleton_result, validate_inputs
from .canonical import skipped

MODULE = "layout-survival"


def evaluate(source_path, subset_path):
    """M0 骨架：先校验输入（不可读/非字体 → 退出码 2），再显式跳过判定。"""
    validate_inputs([source_path, subset_path])
    return skeleton_result(MODULE, "布局保真在 M4 实现；M0 只保证命令可解析、输入校验与退出码正确")