# -*- coding: utf-8 -*-
"""M0 骨架共用：**输入校验是真实现，判定是跳过**。

纪律：M0 不许伪造判定（`SKIPPED(reason=module_not_implemented_in_m0)`），
但**输入合法性必须当场校验** —— 不可读 / 非 sfnt 必须走退出码 2，
否则"骨架阶段退出码正确"这句话就是假的（三档退出码是 M0 就承诺的可演示物）。
"""
from __future__ import print_function

from . import sfnt
from .canonical import skipped

NOT_IMPLEMENTED = "module_not_implemented_in_m0"

#: 各子命令需要的输入槽位 —— 只影响报错时的命名，不影响判定
INPUT_SLOTS = {
    "license-gate": ("font",),
    "coverage-diff": ("source", "subset"),
    "layout-survival": ("source", "subset"),
    "metadata": ("subset", "source"),
    "report": ("source", "subset"),
}


def validate_inputs(paths):
    """逐个只读打开（随后立即关闭）；任一失败即抛 ``InputError`` → 退出码 2。

    ``None`` 槽位（可选参数未给出）跳过——"缺必需参数"由 argparse 的 required 负责。
    """
    for path in paths:
        if path is None:
            continue
        font = sfnt.open_font(path)
        sfnt.close_font(font)


def skeleton_result(module, note=""):
    return ([], [skipped(module, NOT_IMPLEMENTED, note)], {})