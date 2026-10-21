#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""发布终态门（M6）—— 三档：`--pre-tag` / 离线（默认）/ `--online`。

为什么它是"门"：`plan/03` 与 `plan/06` 的 G7 要求"交付面在 tag 前后各自可判定"。
发布是一条**不可回头**的动作（tag 之后改交付面 = 让 tag 撒谎），所以判定必须分两段：

  · `--pre-tag`（tag 之前）：**只落仓库内文件**，零网络 —— 版本三处一致 / LICENSE 与
    `pyproject.toml` 一致 / `docs/report-sample.json` 与现行实现同源 / 五子命令齐全 /
    `git ls-files` 无字体二进制 / 布局门 + 脱敏门 + fixture 位级一致全绿 /
    发布留档在位 / `PENDING_TOOLS` 已自清理。**任一 FAIL 就不该打 tag。**
  · 离线（默认，tag 之后）：pre-tag 全部 + 本地 tag 存在且指向 HEAD + `dist/` 里
    sdist/wheel 齐备（打印 sha256，供 `plan/RELEASE-M6.md` 两栏回填）。
  · `--online`：再加 GitHub 侧的**远端事实**（公开可见 / tag 已推 / Release 带产物 /
    推送数 = 工作流运行数）。**只有这一档联网**，与"运行期零网络"纪律不冲突（用户显式触发）。

退出码：0 全绿（SKIP 可视 + 计数，不算 FAIL）/ 1 有 FAIL / 2 用法错误。
用法：py tools/check_release.py [--pre-tag|--online] [--tag TAG] [--verbose]

纪律（与 `verify_gates.py` 同源）：每条判据都要报"这轮扫到了几个"；跑不成的判据一律
**显式 SKIP 并打印原因**，不许静默通过；永不崩（任何判据异常 → 报一条 FAIL 并继续）。
**顶层只用标准库** —— 门必须能在"未装依赖的干净 checkout"上跑（`src/subsetaudit/cli.py`
一律走 AST 静态解析，不 import 包；否则会拖进 fontTools）。
"""
from __future__ import print_function

import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RELEASE_MILESTONE = 6
RELEASE_DOC = "plan/RELEASE-M%d.md" % RELEASE_MILESTONE

#: 交付面的五条已交付命令（`plan/01` §四 1）
SUBCMDS = ("license-gate", "coverage-diff", "layout-survival", "metadata", "report")

#: 绝不许入库的字体二进制扩展名（`plan/01` §七 红线）
FONT_EXTS = (".ttf", ".otf", ".ttc", ".woff", ".woff2")

SCHEMA = "subsetaudit/report@1"
SAMPLE = "docs/report-sample.json"

CHECKS = []
SCANNED = {}


def add(cid, ok, detail, status=None):
    """`status=None` → PASS/FAIL 由 `ok` 决定；`"skip"` → 显式 SKIP（不算 FAIL）。"""
    CHECKS.append({"id": cid, "ok": bool(ok), "detail": detail, "skip": status == "skip"})


def read(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return None
    with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _run(argv, cwd=None):
    """跑一条本地命令，返回 (rc, 合并输出)。永不抛。"""
    try:
        proc = subprocess.Popen(
            argv, cwd=cwd or ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        out = proc.communicate()[0]
    except OSError as exc:  # 命令不存在等
        return 127, str(exc)
    try:
        text = out.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        text = str(out)
    return proc.returncode, text


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version():
    """从 `__init__.py` 文本取 `__version__`（不依赖导入，避开 fontTools 是否在场）。"""
    text = read("src/subsetaudit/__init__.py") or ""
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.M)
    return match.group(1) if match else None


def pyproject_version():
    text = read("pyproject.toml") or ""
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    return match.group(1) if match else None


def readme_version():
    text = read("README.md") or ""
    match = re.search(r"^\s*-\s*\*\*版本\*\*：v?([0-9][^\s（(]*)", text, re.M)
    return match.group(1) if match else None


# ── 判据 ────────────────────────────────────────────────────────────────────
def check_version_triple():
    """`__init__` / `pyproject.toml` / README 状态行 —— 三处必须是同一个版本串（K9）。"""
    pkg, proj, readme = package_version(), pyproject_version(), readme_version()
    ok = pkg is not None and pkg == proj == readme
    add("RELEASE.VERSION_TRIPLE", ok,
        "三处一致: %s" % pkg if ok
        else "__init__=%r / pyproject=%r / README=%r（必须三处相同）" % (pkg, proj, readme))
    return pkg


def check_license_consistent():
    """`LICENSE`（MIT）与 `pyproject.toml` 的 license 字段一致（`plan/00` M6 的 DoD）。"""
    license_text = read("LICENSE") or ""
    pyproject = read("pyproject.toml") or ""
    field = re.search(r'^license\s*=\s*\{\s*text\s*=\s*"([^"]+)"\s*\}', pyproject, re.M)
    declared = field.group(1) if field else None
    head_ok = license_text.lstrip().startswith("MIT License")
    ok = head_ok and declared == "MIT"
    add("RELEASE.LICENSE_CONSISTENT", ok,
        "LICENSE=MIT License / pyproject license=%r" % declared if ok
        else "LICENSE 首行=%r / pyproject license=%r（须为 MIT License 与 \"MIT\"）"
             % (license_text.split("\n", 1)[0][:40], declared))


def check_sample_json(version):
    """`docs/report-sample.json` 落盘、是规范 JSON、与现行版本同源、inputs 只有 basename。"""
    text = read(SAMPLE)
    if text is None:
        add("RELEASE.SAMPLE_JSON", False, "缺 %s（`plan/04` §1 入仓项）" % SAMPLE)
        return
    try:
        body = json.loads(text)
    except ValueError as exc:
        add("RELEASE.SAMPLE_JSON", False, "%s 不是合法 JSON: %s" % (SAMPLE, exc))
        return
    problems = []
    if body.get("schema") != SCHEMA:
        problems.append("schema=%r" % body.get("schema"))
    got = (body.get("tool") or {}).get("version")
    if got != version:
        problems.append("tool.version=%r（须= %r）" % (got, version))
    for key, value in (body.get("inputs") or {}).items():
        if value != os.path.basename(value):
            problems.append("inputs.%s 不是 basename: %r" % (key, value))
    if "findings" not in body or "skipped" not in body:
        problems.append("缺 findings/skipped 键")
    add("RELEASE.SAMPLE_JSON", not problems,
        "%s 同源（schema/版本/inputs/findings 齐）" % SAMPLE if not problems
        else "%s: %s" % (SAMPLE, "；".join(problems)))


def _parser_subcommands(source):
    """AST 静态解析 `cli.build_parser()`：抽出子命令名与各自的 option 串。

    为什么不用 `import subsetaudit.cli`：那会把 fontTools 拖进门，门就**不能在干净
    checkout 上跑**了（`tests/test_ci_workflow.py::test_gates_are_stdlib_only...` 同纪律）。
    AST 版本判的是同一个交付面（argparse 参数面），而且不依赖任何运行期依赖。
    """
    tree = ast.parse(source)
    func = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "build_parser":
            func = node
            break
    if func is None:
        return None, "cli.py 里找不到 build_parser()"
    # 收集 `...( sub.add_parser("name", ...) ...)` 的「add_parser Call 节点 -> 子命令名」映射。
    # 注意 `cli.py` 里大多数子命令写成 `p = add_out(sub.add_parser("x", help=...))`
    # —— add_parser 是**嵌套**在包装调用里的，所以不能只看"直接调用 add_parser 的那一行"。
    call_to_name = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_parser":
            continue
        if node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            call_to_name[id(node)] = node.args[0].value
    if not call_to_name:
        return None, "build_parser() 里找不到 add_parser 调用"
    # 把赋值语句的**值**（整棵子树）里出现的 add_parser 节点，绑到赋值目标变量上
    var_to_name = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not targets:
            continue
        for cand in ast.walk(node.value):
            name = call_to_name.get(id(cand))
            if name is not None:
                for target in targets:
                    var_to_name[target] = name
    if not var_to_name:
        return None, "add_parser 的返回值没有赋给任何变量（判据认不出子命令）"
    # 收集每个子命令 parser 变量上的 `add_argument("--x", ...)`
    options = dict((name, set()) for name in call_to_name.values())
    for node in ast.walk(func):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_argument" or not isinstance(node.func.value, ast.Name):
            continue
        name = var_to_name.get(node.func.value.id)
        if name is None:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                    and arg.value.startswith("-"):
                options[name].add(arg.value)
    return options, None


def check_subcommands():
    """五子命令在 argparse 里齐备，且 `report` 的四个数据源参数都在（AST 静态解析）。"""
    source = read("src/subsetaudit/cli.py")
    if source is None:
        add("RELEASE.SUBCMDS", False, "缺 src/subsetaudit/cli.py")
        return
    options, problem = _parser_subcommands(source)
    if problem:
        add("RELEASE.SUBCMDS", False, problem)
        return
    present = set(options)
    missing = [c for c in SUBCMDS if c not in present]
    SCANNED["subcmds"] = len(SUBCMDS) - len(missing)
    problems = []
    if missing:
        problems.append("缺子命令: %s" % ",".join(missing))
    lack = [o for o in ("--source", "--subset", "--text", "--corpus", "--format", "--out")
            if o not in options.get("report", set())]
    if lack:
        problems.append("report 缺参数: %s" % ",".join(lack))
    add("RELEASE.SUBCMDS", not problems,
        "%d 个已交付子命令齐备（report 参数面完整）" % len(SUBCMDS) if not problems
        else "；".join(problems))


def check_no_font_binaries():
    """`git ls-files` 里不许出现字体二进制（红线）。

    坑（AGENTS.md）：`git ls-files` 会**静默向上解析到父仓库** → 先比对 toplevel 与本项目根。
    """
    rc, top = _run(["git", "rev-parse", "--show-toplevel"])
    if rc != 0:
        add("RELEASE.NO_FONT_BINARIES", False, "git rev-parse 失败: %s" % top.strip())
        return
    toplevel = os.path.realpath(top.strip())
    if toplevel != os.path.realpath(ROOT):
        add("RELEASE.NO_FONT_BINARIES", False,
            "git toplevel=%s 不是本项目根（会在父仓库里数错文件）" % toplevel)
        return
    rc, out = _run(["git", "ls-files"])
    if rc != 0:
        add("RELEASE.NO_FONT_BINARIES", False, "git ls-files 失败")
        return
    files = [line for line in out.split("\n") if line.strip()]
    bad = [f for f in files if f.lower().endswith(FONT_EXTS)]
    SCANNED["tracked"] = len(files)
    add("RELEASE.NO_FONT_BINARIES", not bad,
        "%d 个入库文件，0 个字体二进制" % len(files) if not bad
        else "入库文件里有字体二进制: %s" % ",".join(bad[:8]))


def _gate(rel, cid):
    rc, out = _run([sys.executable, "-X", "utf8", os.path.join(ROOT, rel)])
    tail = [l for l in out.split("\n") if l.strip()][-1:] or [""]
    add(cid, rc == 0, "%s rc=%s ｜ %s" % (rel, rc, tail[0][:90]))


def check_gates():
    """布局门 + 脱敏门（发布前必绿；`plan/06` G1/G2）。"""
    _gate("tools/check_sprint_layout.py", "RELEASE.LAYOUT_GATE")
    _gate("tools/check_desensitized.py", "RELEASE.DESENS_GATE")


def check_fixtures_bitwise():
    """`gen_fixtures.py --check` 位级一致（发布面里含 golden，必须可重建）。"""
    rc, out = _run([sys.executable, "-X", "utf8", os.path.join(ROOT, "tools/gen_fixtures.py"),
                    "--check"])
    tail = [l for l in out.split("\n") if l.strip()][-1:] or [""]
    add("RELEASE.FIXTURES_BITWISE", rc == 0, "gen_fixtures --check rc=%s ｜ %s" % (rc, tail[0][:80]))


def check_release_doc():
    """`plan/RELEASE-M6.md` 两栏 + 覆盖对账小节 + 三态行（与布局门 LAYOUT.RELEASE 同口径）。"""
    text = read(RELEASE_DOC)
    if text is None:
        add("RELEASE.RELEASE_DOC", False, "缺 %s（发布三件套之一）" % RELEASE_DOC)
        return
    cols = bool(re.search(r"^##\s*一、tag 前事实", text, re.M)) and bool(
        re.search(r"^##\s*二、tag 后追加", text, re.M))
    heading = bool(re.search(r"^#{2,3}.*覆盖对账", text, re.M))
    rows = len(re.findall(r"^\|.*(实现|不适用|待首推).*\|$", text, re.M))
    add("RELEASE.RELEASE_DOC", cols and heading and rows >= 3,
        "两栏:%s 覆盖对账:%s 三态行:%d" % (cols, heading, rows))


def check_pending_tools_cleared():
    """`check_sprint_layout.py` 的 `PENDING_TOOLS` 不得再登记 M6 的工具（K10 自清理）。"""
    text = read("tools/check_sprint_layout.py") or ""
    block = re.search(r"PENDING_TOOLS\s*=\s*\{(.*?)\}", text, re.S)
    if block is None:
        add("RELEASE.PENDING_TOOLS_CLEARED", False, "找不到 PENDING_TOOLS 定义（判据搬走了？）")
        return
    entries = re.findall(r'"([^"]+)"\s*:\s*(\d+)', block.group(1))
    stale = [name for name, mile in entries if int(mile) <= RELEASE_MILESTONE]
    add("RELEASE.PENDING_TOOLS_CLEARED", not stale,
        "PENDING_TOOLS 剩 %d 项，无 ≤M%d 的登记" % (len(entries), RELEASE_MILESTONE)
        if not stale
        else "登记项未随里程碑自清理: %s" % ",".join(stale))


# ── 段一：pre-tag（离线，只落仓库内文件）─────────────────────────────────────
def pre_tag_checks():
    version = check_version_triple()
    check_license_consistent()
    check_sample_json(version)
    check_subcommands()
    check_no_font_binaries()
    check_gates()
    check_fixtures_bitwise()
    check_release_doc()
    check_pending_tools_cleared()
    return version


# ── 段二：tag 之后（离线）────────────────────────────────────────────────────
def tag_checks(tag):
    rc, out = _run(["git", "rev-parse", "-q", "--verify", "refs/tags/%s" % tag])
    if rc != 0:
        add("RELEASE.TAG_EXISTS", False, "本地找不到 tag %s（先 `git tag %s`）" % (tag, tag))
        return
    tag_sha = out.strip().split("\n")[0]
    rc, head = _run(["git", "rev-parse", "HEAD"])
    head_sha = head.strip()
    rc2, anc = _run(["git", "merge-base", "--is-ancestor", tag_sha, head_sha])
    ok = rc2 == 0
    add("RELEASE.TAG_EXISTS", ok,
        "tag %s = %s（%s HEAD %s）"
        % (tag, tag_sha[:12], "含" if ok else "**不含**", head_sha[:12])
        if ok else "tag %s = %s 不是 HEAD 的祖先 → tag 后仍在改交付面" % (tag, tag_sha[:12]))


def dist_checks(version):
    dist = os.path.join(ROOT, "dist")
    if not os.path.isdir(dist):
        add("RELEASE.DIST_ARTIFACTS", False, "缺 dist/（先 `py -m build --no-isolation`）")
        return
    names = sorted(os.listdir(dist))
    sdist = [n for n in names if n.endswith(".tar.gz") and version in n]
    wheel = [n for n in names if n.endswith(".whl") and version in n]
    problems = []
    if not sdist:
        problems.append("无 sdist（%s.tar.gz）" % ("subsetaudit-" + version))
    if not wheel:
        problems.append("无 wheel（subsetaudit-%s-*.whl）" % version)
    if problems:
        add("RELEASE.DIST_ARTIFACTS", False, "；".join(problems))
        return
    lines = []
    for name in sdist + wheel:
        lines.append("%s sha256:%s" % (name, _sha256(os.path.join(dist, name))[:16]))
    add("RELEASE.DIST_ARTIFACTS", True, "；".join(lines))


# ── 段三：GitHub 远端事实（--online，唯一联网档）──────────────────────────────
def _gh(argv):
    return _run(["gh"] + argv)


def remote_checks(tag, version):
    rc, out = _gh(["repo", "view", "--json", "visibility,url"])
    if rc != 0:
        add("RELEASE.REMOTE_REPO_PUBLIC", False, "gh repo view 失败: %s" % out.strip()[:160])
        return
    try:
        body = json.loads(out)
    except ValueError:
        add("RELEASE.REMOTE_REPO_PUBLIC", False, "gh repo view 不是 JSON")
        return
    add("RELEASE.REMOTE_REPO_PUBLIC", body.get("visibility") == "PUBLIC",
        "%s visibility=%s" % (body.get("url"), body.get("visibility")))

    rc, out = _gh(["api", "repos/{owner}/{repo}/git/ref/tags/%s" % tag])
    if rc != 0:
        add("RELEASE.REMOTE_TAG", False, "远端无 tag %s（先 `git push origin %s`）" % (tag, tag))
    else:
        add("RELEASE.REMOTE_TAG", True, "远端 tag %s 在位" % tag)

    rc, out = _gh(["release", "view", tag, "--json", "isDraft,assets,tagName"])
    if rc != 0:
        add("RELEASE.REMOTE_RELEASE", False, "远端无 %s 的 Release: %s" % (tag, out.strip()[:160]))
    else:
        try:
            body = json.loads(out)
        except ValueError:
            body = {}
        assets = body.get("assets") or []
        ok = bool(body.get("tagName")) and not body.get("isDraft") and bool(assets)
        add("RELEASE.REMOTE_RELEASE", ok,
            "Release %s assets=%d" % (tag, len(assets)) if ok
            else "Release %s 缺产物或仍是草稿（assets=%d）" % (tag, len(assets)))

    # 推送数 = 工作流运行数（`plan/05` M6 的"push 数 = run 数对账"）
    rc, out = _gh(["run", "list", "--event", "push", "--limit", "200", "--json", "databaseId"])
    if rc != 0:
        add("RELEASE.PUSH_RUN_PARITY", False, "gh run list 失败: %s" % out.strip()[:160])
        return
    try:
        runs = len(json.loads(out))
    except ValueError:
        add("RELEASE.PUSH_RUN_PARITY", False, "gh run list 不是 JSON")
        return
    rc, out = _run(["git", "rev-list", "--count", "HEAD"])
    pushes = int(out.strip()) if rc == 0 and out.strip().isdigit() else -1
    capped = pushes > 200 or runs > 200
    if capped:
        add("RELEASE.PUSH_RUN_PARITY", True, "push=%d / run=%d（超分页上限，只作提示）"
            % (pushes, runs), status="skip")
        return
    add("RELEASE.PUSH_RUN_PARITY", pushes == runs,
        "push=%d / run=%d" % (pushes, runs))


def _stdout():
    stream = sys.stdout
    enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "").replace("_", "")
    if enc not in ("utf8", "utf8mb4", "cp65001", "utf8sig"):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    return stream


def main(argv):
    mode = "offline"
    tag = None
    verbose = False
    for arg in argv:
        if arg == "--pre-tag":
            mode = "pre-tag"
        elif arg == "--online":
            mode = "online"
        elif arg == "--verbose":
            verbose = True
        elif arg.startswith("--tag="):
            tag = arg.split("=", 1)[1]
        else:
            sys.stderr.write("check_release: 未知参数 %r\n" % arg)
            return 2

    version = package_version()
    tag = tag or ("v%s" % version if version else None)

    for fn in (pre_tag_checks,):
        try:
            fn()
        except Exception as exc:  # 永不崩
            add("RELEASE.INTERNAL", False, "异常: %s" % exc)
    if mode in ("offline", "online"):
        for fn in (lambda: tag_checks(tag), lambda: dist_checks(version)):
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                add("RELEASE.INTERNAL", False, "异常: %s" % exc)
    if mode == "online":
        try:
            remote_checks(tag, version)
        except Exception as exc:  # noqa: BLE001
            add("RELEASE.ONLINE_FAILED", False, "联网判据异常: %s" % exc)

    out = _stdout()
    label = {"pre-tag": "tag 前", "offline": "tag 后（离线）", "online": "tag 后（含 GitHub 远端）"}[mode]
    out.write("发布终态门 · %s · 版本 %s · tag %s\n" % (label, version, tag))
    out.write("=" * 60 + "\n")
    for check in CHECKS:
        mark = "SKIP" if check["skip"] else ("PASS" if check["ok"] else "FAIL")
        out.write("%s  %s  %s\n" % (mark, check["id"], check["detail"]))
    failed = [c for c in CHECKS if not c["ok"]]
    skipped = [c for c in CHECKS if c["skip"]]
    out.write("=" * 60 + "\n")
    out.write("这轮扫到：入库文件 %s / 已交付子命令 %s\n"
              % (SCANNED.get("tracked", "-"), SCANNED.get("subcmds", "-")))
    out.write("结论: %s\n" % ("全绿" if not failed else "%d 项 FAIL" % len(failed)))
    if skipped and verbose:
        for check in skipped:
            out.write("SKIP 原因: %s —— %s\n" % (check["id"], check["detail"]))
    out.flush()
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
