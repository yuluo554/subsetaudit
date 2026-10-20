#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""离线冒烟：对五条已交付命令各跑一次，断言退出码与输出形态。

为什么常驻在 CI 里：**"测试绿"不等于"用户敲的那条命令跑得通"**。测试调的是函数，
这里调的是 `main(argv)` → 与用户输入的路径完全一致（含 argparse 与 stdout 编码）。

零网络、零外部字体：字体在临时目录里用 fontTools 现合成。
退出码：0 全通过 / 1 有失败 / 2 用法错误。
"""
from __future__ import print_function

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from fontTools.fontBuilder import FontBuilder  # noqa: E402
from fontTools.pens.ttGlyphPen import TTGlyphPen  # noqa: E402

CASES = []


def _synthetic_font(path, cmap, fs_type=0x0000):
    glyphs = [".notdef"] + sorted(set(cmap.values()))
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyphs)
    fb.setupCharacterMap(cmap)
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0)); pen.lineTo((20, 0)); pen.lineTo((20, 20)); pen.closePath()
    fb.setupGlyf(dict((name, pen.glyph()) for name in glyphs))
    fb.setupHorizontalMetrics(dict((name, (600, 0)) for name in glyphs))
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "SmokeFixture", "styleName": "Regular",
                       "licenseDescription": "synthetic", "licenseInfoURL": "https://example.invalid"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200)
    fb.font["OS/2"].fsType = fs_type
    fb.setupPost()
    fb.save(path)
    return path


def _run(argv):
    proc = subprocess.Popen([sys.executable, "-X", "utf8", "-m", "subsetaudit"] + argv,
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src")))
    out, err = proc.communicate()
    return proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def main(argv):
    if argv:
        sys.stderr.write("smoke_cli: 不接受参数\n")
        return 2

    tmp = tempfile.mkdtemp(prefix="subsetaudit-smoke-")
    failures = []
    try:
        font = _synthetic_font(os.path.join(tmp, "smoke.ttf"), {0x61: "a", 0x62: "b", 0x63: "c"})
        corpus = os.path.join(tmp, "corpus.txt")
        with io.open(corpus, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("abc\n")

        cases = [
            (["--version"], 0),
            (["license-gate", font], 0),
            (["license-gate", font, "--markdown"], 0),
            (["coverage-diff", font, "--text", "abc"], 0),
            (["coverage-diff", font, "--corpus", corpus, "--subset", font], 0),
            (["layout-survival", font, font], 0),
            (["metadata", font], 0),
            (["metadata", font, "--source", font], 0),
            (["report", "--source", font, "--subset", font, "--text", "abc"], 0),
            (["license-gate", os.path.join(tmp, "missing.ttf")], 2),
        ]
        for args, expected in cases:
            code, out, err = _run(args)
            ok = code == expected
            label = " ".join(args[:1] + ["<file>"] * (len(args) - 1))
            if "--markdown" in args:
                label += " --markdown"
            # 只有 JSON 形态才断言可解析 —— Markdown 是渲染视图（不参与 digest），
            # 拿 JSON 判据去测它会把"合法的另一种输出"判成失败（冒烟首版实测）。
            if ok and code == 0 and args[0] not in ("--version",) and "--markdown" not in args:
                try:
                    body = json.loads(out)
                except ValueError:
                    body = None
                ok = body is not None and "findings" in body and "skipped" in body
            elif ok and "--markdown" in args:
                ok = out.startswith("# SubsetAudit 报告")
            if not ok:
                failures.append("%s -> rc=%s (期望 %s) stderr=%s" % (label, code, expected, err[:200]))
            print("%s  %-46s rc=%s" % ("PASS" if ok else "FAIL", label, code))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("")
    print("冒烟：%d 条命令，%d 条失败" % (len(cases), len(failures)))
    for item in failures:
        print("  " + item)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))