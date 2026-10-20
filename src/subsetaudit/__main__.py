# -*- coding: utf-8 -*-
"""``python -m subsetaudit`` 入口 —— 与 ``subsetaudit`` 控制台脚本等价。

存在的理由：CI 与"没有安装、只设 PYTHONPATH"的环境里，`python -m subsetaudit` 是最稳的调用形态；
没有它，用户/CI 会撞上 `No module named subsetaudit.__main__`（本项目 M0 冒烟实测）。
"""
from __future__ import print_function

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
