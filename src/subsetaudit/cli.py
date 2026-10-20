# -*- coding: utf-8 -*-
"""CLI：五子命令 + 退出码唯一收口点。

用法（与 README 的"三条场景"逐条对应；改动必须同步改 README，并跑参数面反射对账测试）::

    subsetaudit license-gate FONT [--out PATH] [--markdown]
    subsetaudit coverage-diff SOURCE (--text TEXT | --corpus FILE) [--subset SUBSET]
                              [--strict-source] [--out PATH] [--markdown]
    subsetaudit layout-survival SOURCE SUBSET [--out PATH] [--markdown]
    subsetaudit metadata SUBSET [--source SOURCE] [--out PATH] [--markdown]
    subsetaudit report [--source SOURCE] [--subset SUBSET] [--text TEXT] [--corpus FILE]
                       [--format json|markdown] [--out PATH]

退出码（`data/README.md` §六.6，只在 ``main`` 里收口）：0 通过 / 1 有 error 级发现 / 2 输入非法。
``SKIPPED(reason=...)`` 恒为 note，恒出现在输出里，恒不影响退出码。
"""
from __future__ import print_function

import argparse
import io
import sys

from . import __version__, canonical, coverage_diff, layout_survival, license_gate, metadata, report

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT_ERROR = 2

MODULE_ORDER = canonical.MODULES


def _ensure_utf8_stdio():
    """CI/管道是 cp1252 时，非 ASCII 输出会 UnicodeEncodeError。

    ``py -X utf8`` 只改本机我们敲的那条命令，改不了 CI 与子进程 —— 所以入口自加固：
    按 ``stream.encoding`` 探针决定是否 reconfigure；已是 UTF-8（含中文控制台 cp936 之外的
    正常 UTF-8 环境）则不动。探针失败（如 StringIO 桩）时静默跳过。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            enc = (stream.encoding or "").lower().replace("-", "").replace("_", "")
        except Exception:  # noqa: BLE001 - 桩对象没有 encoding
            continue
        if enc in ("utf8", "utf8mb4", "cp65001", "utf8sig"):
            continue
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - 老版本 / 非文本流
            pass


def _write(text, out_path):
    if out_path:
        with io.open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    else:
        # 直接写 sys.stdout（不绕 fileno）——否则 pytest 的 capsys 桩会被绕过
        sys.stdout.write(text)
        sys.stdout.flush()


def _emit(report_body, args):
    if getattr(args, "markdown", False) or getattr(args, "format", "json") == "markdown":
        _write(canonical.render_markdown(report_body), getattr(args, "out", None))
    else:
        _write(canonical.dumps(report_body), getattr(args, "out", None))
    return EXIT_FINDINGS if canonical.has_error(report_body["findings"]) else EXIT_OK


# ── 参数面 ──────────────────────────────────────────────────────────────────
def build_parser():
    parser = argparse.ArgumentParser(
        prog="subsetaudit",
        description="字体派生产物体检：子集正确性审计（覆盖 / 布局 / 许可 / 元数据）。",
    )
    parser.add_argument("--version", action="version", version="subsetaudit %s" % __version__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    def add_out(p):
        p.add_argument("--out", metavar="PATH", help="写入文件（默认 stdout）")
        p.add_argument("--markdown", action="store_true", help="输出 Markdown 渲染视图（不参与 digest）")
        return p

    p = add_out(sub.add_parser("license-gate", help="M2 许可闸门：fsType 版本分流 + 嵌入结论"))
    p.add_argument("font", metavar="FONT", help="字体文件（原字体或产物）")

    p = add_out(sub.add_parser("coverage-diff", help="M3 覆盖差集：三分类 + 分块计数 + 回退链建议"))
    p.add_argument("source", metavar="SOURCE", help="原字体")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", metavar="TEXT", help="需求字符集（字面文本）")
    group.add_argument("--corpus", metavar="FILE", help="需求字符集（UTF-8 文本文件）")
    p.add_argument("--subset", metavar="SUBSET", help="子集产物（给了才会算 LOST_IN_SUBSET）")
    p.add_argument("--strict-source", action="store_true",
                   help="原文缺字（MISSING_IN_SOURCE）升级为 error")

    p = add_out(sub.add_parser("layout-survival", help="M4 布局保真：GSUB/GPOS 三元组与连字规则"))
    p.add_argument("source", metavar="SOURCE", help="原字体")
    p.add_argument("subset", metavar="SUBSET", help="子集产物")

    p = add_out(sub.add_parser("metadata", help="M5 元数据与位域一致性"))
    p.add_argument("subset", metavar="SUBSET", help="待检字体（通常是产物）")
    p.add_argument("--source", metavar="SOURCE", help="原字体（用于区分『默认剥离』与『原作者没写』）")

    p = sub.add_parser("report", help="M5 报告聚合：规范 JSON 或 Markdown")
    p.add_argument("--source", metavar="SOURCE", help="原字体")
    p.add_argument("--subset", metavar="SUBSET", help="子集产物")
    p.add_argument("--text", metavar="TEXT", help="需求字符集（字面文本）")
    p.add_argument("--corpus", metavar="FILE", help="需求字符集（UTF-8 文本文件）")
    p.add_argument("--format", choices=("json", "markdown"), default="json", help="输出格式")
    p.add_argument("--out", metavar="PATH", help="写入文件（默认 stdout）")
    return parser


# ── 各子命令 ────────────────────────────────────────────────────────────────
def _run_license_gate(args):
    findings, skips, summary = license_gate.evaluate(args.font)
    body = report.build(findings, skips, {"font": canonical.input_ref(args.font)}, summary)
    return _emit(body, args)


def _run_coverage_diff(args):
    # --corpus 的读取失败属输入非法（退出码 2），不是 finding
    if args.corpus:
        try:
            required = _read_corpus(args.corpus)
        except (OSError, UnicodeDecodeError) as exc:
            raise canonical.InputError(args.corpus, "corpus_unreadable (%s)" % exc.__class__.__name__)
    else:
        required = _from_text(args.text)
    findings, skips, summary = coverage_diff.evaluate(
        args.source, required, subset_path=args.subset, strict_source=args.strict_source
    )
    inputs = {"source": canonical.input_ref(args.source)}
    if args.subset:
        inputs["subset"] = canonical.input_ref(args.subset)
    body = report.build(findings, skips, inputs, summary)
    return _emit(body, args)


def _run_layout_survival(args):
    findings, skips, summary = layout_survival.evaluate(args.source, args.subset)
    body = report.build(
        findings, skips,
        {"source": canonical.input_ref(args.source), "subset": canonical.input_ref(args.subset)},
        summary,
    )
    return _emit(body, args)


def _run_metadata(args):
    findings, skips, summary = metadata.evaluate(args.subset, source_path=args.source)
    inputs = {"subset": canonical.input_ref(args.subset)}
    if args.source:
        inputs["source"] = canonical.input_ref(args.source)
    body = report.build(findings, skips, inputs, summary)
    return _emit(body, args)


def _run_report(args):
    from ._skeleton import validate_inputs

    # 任一路径不可读/非字体 → 退出码 2（与其它子命令同一语义）
    validate_inputs([args.source, args.subset])
    findings, skips, summary = [], [], {}
    inputs = {}
    if args.source:
        inputs["source"] = canonical.input_ref(args.source)
        f1, s1, sum1 = license_gate.evaluate(args.source)
        findings += f1
        skips += s1
        summary.update(sum1)
    if args.subset:
        inputs["subset"] = canonical.input_ref(args.subset)
        f2, s2, sum2 = metadata.evaluate(args.subset, source_path=args.source)
        findings += f2
        skips += s2
        summary.update(sum2)
    if args.source and args.subset:
        f3, s3, sum3 = layout_survival.evaluate(args.source, args.subset)
        findings += f3
        skips += s3
        summary.update(sum3)
    if args.source and (args.text or args.corpus):
        required = _read_corpus(args.corpus) if args.corpus else _from_text(args.text)
        f4, s4, sum4 = coverage_diff.evaluate(args.source, required, subset_path=args.subset)
        findings += f4
        skips += s4
        summary.update(sum4)
    body = report.build(findings, skips, inputs, summary)
    return _emit(body, args)


def _from_text(text):
    from . import cmapset
    return cmapset.from_text(text)


def _read_corpus(path):
    from . import cmapset
    return cmapset.from_corpus_file(path)


HANDLERS = {
    "license-gate": _run_license_gate,
    "coverage-diff": _run_coverage_diff,
    "layout-survival": _run_layout_survival,
    "metadata": _run_metadata,
    "report": _run_report,
}


def main(argv=None):
    _ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.command:
        parser.print_help()
        return EXIT_INPUT_ERROR
    try:
        return HANDLERS[args.command](args)
    except canonical.InputError as exc:
        sys.stderr.write("输入非法: %s: %s\n" % (exc.path, exc.reason))
        return EXIT_INPUT_ERROR


if __name__ == "__main__":
    sys.exit(main())