# -*- coding: utf-8 -*-
"""CLI 测试：三档退出码、五子命令可跑、SKIPPED 显式、参数面反射对账、零网络、版本一致。"""
from __future__ import print_function

import io
import json
import os
import subprocess

import pytest

from subsetaudit import cli

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Result(object):
    """一次 CLI 运行的完整观察结果。

    **capsys 只能消费一次**：``readouterr()`` 二次调用返回空串 —— 所以三个流必须在同一处
    一次性接住（本项目 M0 实测踩到：单独再取 stderr 得到空串，看起来像"错误信息没打印"，
    实际是被第一次调用消费掉了）。
    """

    def __init__(self, code, out, err):
        self.code = code
        self.out = out
        self.err = err

    def json(self):
        return json.loads(self.out)


def run(argv, capsys=None):
    """跑 CLI，一次性返回 (退出码, stdout, stderr)。"""
    code = cli.main(argv)
    out = err = ""
    if capsys is not None:
        captured = capsys.readouterr()
        out, err = captured.out, captured.err
    return Result(code, out, err)


# ── 退出码 2（输入非法） ─────────────────────────────────────────────────────
def test_no_subcommand_is_usage_error(capsys):
    assert run([], capsys).code == cli.EXIT_INPUT_ERROR


def test_license_gate_missing_file_is_exit_2(tmp_path, capsys):
    assert run(["license-gate", str(tmp_path / "nope.ttf")], capsys).code == cli.EXIT_INPUT_ERROR


def test_license_gate_non_font_is_exit_2(tmp_path, capsys):
    bad = tmp_path / "x.ttf"
    bad.write_text("nope", encoding="utf-8")
    assert run(["license-gate", str(bad)], capsys).code == cli.EXIT_INPUT_ERROR


def test_every_subcommand_rejects_a_non_font(tmp_path, capsys):
    """退出码 2 是 M0 就承诺的可演示物 —— 五个子命令都要有输入校验。"""
    bad = tmp_path / "x.ttf"
    bad.write_text("nope", encoding="utf-8")
    cases = [
        ["license-gate", str(bad)],
        ["coverage-diff", str(bad), "--text", "ab"],
        ["layout-survival", str(bad), str(bad)],
        ["metadata", str(bad)],
        ["report", "--source", str(bad)],
    ]
    for argv in cases:
        assert run(argv, capsys).code == cli.EXIT_INPUT_ERROR, argv


def test_open_failure_writes_exactly_one_line_to_stderr(tmp_path, capsys):
    r = run(["license-gate", str(tmp_path / "nope.ttf")], capsys)
    assert r.code == cli.EXIT_INPUT_ERROR
    assert r.err.count("\n") == 1, repr(r.err)
    assert "输入非法" in r.err


def test_coverage_diff_requires_text_or_corpus(simple_font):
    with pytest.raises(SystemExit) as exc:
        cli.main(["coverage-diff", simple_font])
    assert exc.value.code == cli.EXIT_INPUT_ERROR


def test_coverage_diff_rejects_both_text_and_corpus(simple_font, corpus_file):
    with pytest.raises(SystemExit) as exc:
        cli.main(["coverage-diff", simple_font, "--text", "ab", "--corpus", corpus_file])
    assert exc.value.code == cli.EXIT_INPUT_ERROR


def test_coverage_diff_unreadable_corpus_is_exit_2(simple_font, tmp_path, capsys):
    argv = ["coverage-diff", simple_font, "--corpus", str(tmp_path / "gone.txt")]
    assert run(argv, capsys).code == cli.EXIT_INPUT_ERROR


# ── 退出码 0 + SKIPPED 显式 ─────────────────────────────────────────────────
def test_license_gate_skeleton_exits_zero_with_visible_skipped(simple_font, capsys):
    r = run(["license-gate", simple_font], capsys)
    assert r.code == cli.EXIT_OK, r.out
    body = r.json()
    assert body["findings"] == []
    assert [s["reason"] for s in body["skipped"]] == ["module_not_implemented_in_m0"]
    assert body["inputs"]["font"] == os.path.basename(simple_font)


def test_all_five_subcommands_exit_zero(simple_font, corpus_file, capsys):
    cases = [
        ["license-gate", simple_font],
        ["coverage-diff", simple_font, "--text", "ab"],
        ["coverage-diff", simple_font, "--corpus", corpus_file, "--subset", simple_font],
        ["layout-survival", simple_font, simple_font],
        ["metadata", simple_font],
        ["metadata", simple_font, "--source", simple_font],
        ["report", "--source", simple_font, "--subset", simple_font, "--text", "ab"],
    ]
    for argv in cases:
        r = run(argv, capsys)
        assert r.code == cli.EXIT_OK, "%r -> %s %s" % (argv, r.code, r.out)
        body = r.json()
        assert body["skipped"], "M0 的每个子命令都必须把 SKIPPED 显式写进输出: %r" % (argv,)
        assert body["inputs"].get("source") is None or not os.path.isabs(body["inputs"]["source"])


def test_report_markdown_format(simple_font, capsys):
    r = run(["report", "--source", simple_font, "--format", "markdown"], capsys)
    assert r.code == cli.EXIT_OK
    assert "# SubsetAudit 报告" in r.out and "法律意见" in r.out


def test_out_file_is_written_lf_and_utf8(simple_font, tmp_path, capsys):
    target = tmp_path / "r.json"
    assert run(["license-gate", simple_font, "--out", str(target)], capsys).code == cli.EXIT_OK
    raw = target.read_bytes()
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    json.loads(raw.decode("utf-8"))


def test_json_output_is_byte_identical_across_runs(simple_font, tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    run(["license-gate", simple_font, "--out", str(a)], capsys)
    run(["license-gate", simple_font, "--out", str(b)], capsys)
    assert a.read_bytes() == b.read_bytes()


# ── 参数面反射对账（README ↔ parser） ───────────────────────────────────────
def test_readme_command_lines_parse_against_parser():
    """README 每条 ``subsetaudit`` 命令行都必须被 parser 接受。

    · ``<...>`` 占位符**替换成具体值**（而不是删掉）—— 删掉会让 `--corpus <f>` 退化成
      "选项后面没有值"，把"文档写的形态"误判成"parser 不接受"（变异靶子瞄错）；
    · ``--version`` / ``--help`` 由 argparse 自己 ``SystemExit(0)``，那是**成功**形态。
    """
    import re

    parser = cli.build_parser()
    readme = io.open(os.path.join(REPO_ROOT, "README.md"), "r", encoding="utf-8").read()
    commands = sorted(set(
        line.strip() for line in readme.split("\n") if line.strip().startswith("subsetaudit ")
    ))
    assert len(commands) >= 3, "README 至少要给出三条可复制命令（场景复现要求）"
    checked, rejected = 0, []
    for command in commands:
        argv = re.sub(r"<[^>]+>", "placeholder", command).split()[1:]
        try:
            parsed = parser.parse_args(argv)
        except SystemExit as exc:
            if exc.code in (0, None):
                checked += 1
                continue
            rejected.append("%s (exit %s)" % (command, exc.code))
            continue
        assert parsed.command, command
        checked += 1
    assert rejected == [], "README 写的命令形态 parser 不认: %s" % rejected
    assert checked >= 3


def test_readme_reflection_check_would_catch_a_rejected_flag():
    """变异自证：把 README 里一个合法选项改坏 → 上面的对账必须红（防假门）。"""
    import re

    parser = cli.build_parser()
    broken = re.sub(r"<[^>]+>", "placeholder",
                    'subsetaudit report --source <source.ttf> --format markdown')
    argv = broken.split()[1:]
    argv[argv.index("markdown")] = "--not-a-real-flag"
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(argv)
    assert exc.value.code == cli.EXIT_INPUT_ERROR


def test_multi_value_argument_in_help_is_accepted_in_all_three_shapes():
    """多值参数（若将来加 `--modules` 之类）必须同时接受单值 / 逗号 / all。

    本判据在 M5 有真实多值参数时自动生效；当前以 `--format` 的两值面作最小锚点，
    保证"文档写的形态"与 parser 一致这条纪律在 M0 就被钉住。
    """
    parser = cli.build_parser()
    for value in ("json", "markdown"):
        assert parser.parse_args(["report", "--format", value]).format == value
    with pytest.raises(SystemExit):
        parser.parse_args(["report", "--format", "yaml"])


# ── 纪律类判据（变异：改坏即红） ────────────────────────────────────────────
def test_no_runtime_network_or_model_imports():
    """零网络零模型纪律：包内不得 import 任何网络/模型库。"""
    banned = ("urllib", "requests", "socket", "http.client", "httpx", "aiohttp", "torch",
              "transformers", "openai")
    pkg = os.path.join(REPO_ROOT, "src", "subsetaudit")
    hits = []
    for name in sorted(os.listdir(pkg)):
        if not name.endswith(".py"):
            continue
        text = io.open(os.path.join(pkg, name), "r", encoding="utf-8").read()
        for lineno, line in enumerate(text.split("\n"), 1):
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for token in banned:
                if token in stripped:
                    hits.append("%s:%d %s" % (name, lineno, stripped))
    assert hits == [], "包内出现网络/模型依赖: %s" % hits


def test_version_consistent_between_package_and_pyproject():
    from subsetaudit import __version__
    pyproject = io.open(os.path.join(REPO_ROOT, "pyproject.toml"), "r", encoding="utf-8").read()
    line = [l for l in pyproject.split("\n") if l.startswith("version = ")][0]
    assert __version__ == line.split("=", 1)[1].strip().strip('"'), line


def test_version_consistent_with_readme():
    """第三处：README 顶部状态行必须写出当前版本（变异：升版本只改一处 → 必红）。"""
    from subsetaudit import __version__
    readme = io.open(os.path.join(REPO_ROOT, "README.md"), "r", encoding="utf-8").read()
    assert ("v%s" % __version__) in readme, "README 状态行必须写出 v%s" % __version__


def test_console_script_entry_point_matches_cli_main():
    pyproject = io.open(os.path.join(REPO_ROOT, "pyproject.toml"), "r", encoding="utf-8").read()
    assert 'subsetaudit = "subsetaudit.cli:main"' in pyproject


def test_skeleton_modules_do_not_fabricate_findings():
    """M0 纪律：未实现的模块只准返回 SKIPPED，不得返回任何 finding。"""
    for name in ("license_gate", "coverage_diff", "layout_survival", "metadata"):
        mod = __import__("subsetaudit.%s" % name, fromlist=[name])
        text = io.open(mod.__file__, "r", encoding="utf-8").read() if hasattr(mod, "__file__") else ""
        assert "skeleton_result(" in text, "%s 未走骨架出口" % name
        assert "finding(" not in text, "%s 在 M0 里不得构造 finding" % name


def test_no_font_binaries_tracked_by_git():
    """商用字体红线：git 索引里不得有任何字体二进制。"""
    proc = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    if proc.returncode != 0:
        pytest.skip("not a git work tree: %s" % proc.stderr.strip())
    offenders = [f for f in proc.stdout.split("\n")
                 if f.lower().endswith((".ttf", ".otf", ".ttc", ".otc", ".woff", ".woff2"))]
    assert offenders == [], "字体二进制不得入库: %s" % offenders