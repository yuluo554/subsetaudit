# -*- coding: utf-8 -*-
"""M3 · `coverage-diff` 覆盖差集 —— **M0 骨架**。

签名与返回形状（M3 填实，接口不改）：

    evaluate(source_path, required, subset_path=None, strict_source=False)
        -> (findings, skips, summary)

M3 的实现要点（见 `plan/03` §3、`data/README.md` §六.2–§六.4）：
  · 用 ``sfnt.select_unicode_cmap`` 选表；无 Unicode cmap → ``SKIPPED(reason=no_unicode_cmap)``，
    **不得**输出"覆盖为空"的 OK 结论；
  · 用 ``cmapset.closure`` 做组合字符闭包，新增码位单列计数；
  · 用 ``cmapset.classify`` 产出三分类（``glyph0`` 命中不计覆盖）；
  · 回退链建议用 ``cmapset.fallback_hint``（仅建议，不改判定）。

M0 阶段：**显式跳过，不伪造判定**。
"""
from __future__ import print_function

from ._skeleton import skeleton_result, validate_inputs
from .canonical import skipped

MODULE = "coverage-diff"


def evaluate(source_path, required, subset_path=None, strict_source=False):
    """M0 骨架：先校验输入（不可读/非字体 → 退出码 2），再显式跳过判定。"""
    validate_inputs([source_path, subset_path])
    return skeleton_result(MODULE, "覆盖差集在 M3 实现；M0 只保证命令可解析、输入校验与退出码正确")