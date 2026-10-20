# -*- coding: utf-8 -*-
"""输入校验共用层（M0 起；M5 起已无骨架模块在使用本文件的跳过出口）。

历史：M0 的骨架模块用 ``skeleton_result`` 走 `SKIPPED(reason=module_not_implemented_in_m0)`，
**不许伪造判定**。M2–M5 逐个里程碑把判定填实后，`skeleton_result` 已**无人调用**
（`tests/test_cli.py` 反向扫描钉住），只剩 ``validate_inputs`` 在用 —— 那是**真实现**：
不可读 / 非 sfnt 必须走退出码 2，否则"退出码正确"这句话就是假的。

`NOT_IMPLEMENTED` / `skeleton_result` 保留为**历史符号**：将来若再加骨架模块，
`tests/test_cli.py::test_skeleton_modules_do_not_fabricate_findings` 的 `SKELETON_MODULES`
填上名字即可复用同一套纪律（断言它也走这个出口且不构造 finding）。
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