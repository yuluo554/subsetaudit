# -*- coding: utf-8 -*-
"""跨 Python / 跨 fontTools 版本**判定一致性**常驻门（D5，2026-10-23 补）。

## 这道门在防什么

`requires-python >=3.8` + `fonttools>=4.40,<5` ⇒ 3.8 装 **4.57.0**、3.12 装 **4.67.0**
（差 10 个小版本，`plan/05` 已登记）。两个通道跑同一 fixture 是否给出**同一份判定**，
在 2026-10-23 之前只有一次性的实测证据（诊断方手工比过一次），**没有任何门盯着**。
上游一旦改变某个判定（码页回退、cmap 选表、GSUB 解包），用户会在 3.8 上看到一种结论、
在 3.12 上看到另一种，而全仓不会有任何东西变红。

## 判据怎么落

**oracle 文件** `docs/cross-channel-oracle.json` 存若干条"输入 → 完整报告体"。
本测试在**当前通道**现跑同样的输入，与 oracle **逐字节**比对：

  · 每个 CI 格子跑同一份 oracle ⇒ **两个格子都绿 = 跨版本判定一致**（这就是"常驻"的实现：
    单格里无法对比另一版本，但两格对比同一份冻结点即可）；
  · 差异时打印逐行 unified diff（不只是一句 "assert failed"），让人能立刻看到是哪个键变了。

`tool` 键**不豁免**、也不需要豁免：决策 D-M7-1 已把环境相关量（`fonttools_version`）
移出报告，`tool` 只剩 `{name, version}` —— 两个通道本来就该相同。**这条门能成立，
正是因为 D2 的修法**（若 `tool` 里还留着 fonttools 版本，这条门在 3.8/3.12 必有一格红）。

## 可选的第二通道实测

本机同时装了 3.8 与 3.12 时（`py -3.8` / `py -3.12`，或用环境变量
``SUBSETAUDIT_CROSS_PYTHON`` 指定），额外**真起子进程**跑一遍另一通道并逐字节比对 ——
这是"跨通道"的直接证据；只有一条解释器的环境（CI 单格）跳过，**跳过不等于通过**，
那一格的证明责任由"两格共比同一份 oracle"承担。

## 重生成 oracle（不是逃生门）

```bash
SUBSETAUDIT_REGENERATE_ORACLE=1 py -3.12 -m pytest -o addopts="" tests/test_cross_channel.py
```

⚠ 重生成是**迁移事件**，不是"门红了就重跑一下"：必须在 **4.57.0 与 4.67.0 两条通道各生成
一次、逐字节相同**之后才能提交；若两次不同，那是上游改变判定的**真实信号**，要按
`data/README §七` 的更正流程逐条复核。oracle 里记了 `generated_with`，便于审计。
"""
from __future__ import print_function

import contextlib
import io
import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORACLE = os.path.join(REPO_ROOT, "docs", "cross-channel-oracle.json")
FIXTURES = os.path.join(REPO_ROOT, "data", "fixtures")

#: 每条用例 = 「一段 CLI 参数」。覆盖四类判定面：
#:   ① 四模块聚合（error 级 finding + 有 skipped）  ② metadata 差分（warn 级）
#:   ③ coverage 三分类（LOST / OK / MISSING_IN_SOURCE）  ④ license 五元结论 + 违规码
CASES = [
    ("report-full-f6", ["report",
                        "--source", "data/fixtures/codepage-mismatch/out/source.ttf",
                        "--subset", "data/fixtures/codepage-mismatch/out/subset.ttf",
                        "--text", "汉字"]),
    ("metadata-f5", ["metadata",
                     "data/fixtures/metadata-stripped/out/subset.ttf",
                     "--source", "data/fixtures/metadata-stripped/out/source.ttf"]),
    ("coverage-f4", ["coverage-diff",
                     "data/fixtures/silent-drop/out/source.ttf",
                     "--text", "abc汉字",
                     "--subset", "data/fixtures/silent-drop/out/subset.ttf"]),
    ("license-f1", ["license-gate",
                    "data/fixtures/fstype-nosubset/out/fstype-nosubset.ttf"]),
    ("layout-f4", ["layout-survival",
                   "data/fixtures/silent-drop/out/source.ttf",
                   "data/fixtures/silent-drop/out/subset.ttf"]),
]


def _fixtures_ready():
    missing = [p for _name, argv in CASES for p in argv
               if p.startswith("data/") and not os.path.isfile(os.path.join(REPO_ROOT, p))]
    return missing


def run_case(argv):
    """在当前解释器里跑一条命令，返回 (rc, 规范 JSON 文本)。"""
    from subsetaudit import cli

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue()


def current_runs():
    """跑全部用例 → ``{"generated_with": {...}, "cases": [...]}``（与 oracle 同构）。"""
    import fontTools

    body = {
        "note": "跨 Python/fontTools 通道的判定一致性冻结点；由 tests/test_cross_channel.py 消费。",
        "generated_with": {
            "python": "%d.%d.%d" % sys.version_info[:3],
            "fonttools": getattr(fontTools, "version", "unknown"),
        },
        "cases": [],
    }
    for name, argv in CASES:
        code, text = run_case(argv)
        body["cases"].append({"name": name, "argv": list(argv), "exit_code": code,
                              "report": json.loads(text)})
    return body


def _dump(body):
    return json.dumps(body, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def _diff_lines(expected, actual):
    """逐行 diff（只取前 60 行差异，避免刷屏但足够定位）。"""
    import difflib

    exp = _dump(expected).split("\n")
    act = _dump(actual).split("\n")
    out = list(difflib.unified_diff(exp, act, fromfile="oracle", tofile="current", lineterm="",
                                    n=1))
    return out[:60]


@pytest.fixture(scope="module")
def oracle():
    if _fixtures_ready():
        pytest.skip("fixture 产物缺失（先跑 py tools/gen_fixtures.py）: %s" % _fixtures_ready())
    if os.environ.get("SUBSETAUDIT_REGENERATE_ORACLE") == "1":
        body = current_runs()
        with io.open(ORACLE, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_dump(body))
        pytest.skip("已按 SUBSETAUDIT_REGENERATE_ORACLE=1 重写 %s" % os.path.basename(ORACLE))
    with io.open(ORACLE, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ── ① 主判据：当前通道 == 冻结点（两格共比同一份 ⇒ 跨版本一致） ─────────────
def test_current_channel_matches_checked_in_oracle(oracle):
    current = current_runs()
    assert sorted(c["name"] for c in current["cases"]) == sorted(c["name"] for c in oracle["cases"]), \
        "oracle 的用例集合与实际不符（加了用例没重生成 oracle？）"
    problems = []
    for want, got in zip(oracle["cases"], current["cases"]):
        if want["exit_code"] != got["exit_code"]:
            problems.append("%s: 退出码 oracle=%r / 现行=%r"
                            % (want["name"], want["exit_code"], got["exit_code"]))
        if want["report"] != got["report"]:
            problems.append("%s: 报告体不同\n%s"
                            % (want["name"], "\n".join(_diff_lines(want["report"],
                                                                  got["report"]))))
    assert problems == [], (
        "本条通道的判定与冻结点不一致 —— 上游（fontTools）可能改变了判定。\n"
        "**先逐条复核**（data/README §七 的更正流程），再决定是改实现还是迁移 oracle；\n"
        "不要用 SUBSETAUDIT_REGENERATE_ORACLE=1 直接盖掉。\n\n" + "\n\n".join(problems))


def test_oracle_covers_all_four_judgement_surfaces(oracle):
    """非空跑自证：oracle 必须真的覆盖四类判定面（不是一条命令敷衍）。"""
    names = set(c["name"] for c in oracle["cases"])
    assert {"report-full-f6", "metadata-f5", "coverage-f4", "license-f1", "layout-f4"} <= names, names
    modules = set()
    for case in oracle["cases"]:
        modules.update(case["report"].get("summary", {}).get("modules", []))
    assert {"license-gate", "metadata", "layout-survival", "coverage-diff"} <= modules, modules


def test_oracle_carries_no_environment_field(oracle):
    """oracle 里每条报告都不得带环境相关字段（决策 D-M7-1）—— 否则跨版本门必然一格红。"""
    for case in oracle["cases"]:
        tool = case["report"].get("tool") or {}
        assert set(tool) == {"name", "version"}, (case["name"], tool)


def test_oracle_is_committed_and_parses():
    """oracle 必须入库（不在 `.gitignore` 里），否则 CI 上本门会因缺文件而失效。"""
    assert os.path.isfile(ORACLE), ORACLE
    proc = subprocess.run(["git", "ls-files", "--error-unmatch",
                           "docs/cross-channel-oracle.json"],
                          cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True)
    if proc.returncode != 0 and "not a git repository" not in proc.stdout.lower():
        # 新文件在 `git add` 之前会是未跟踪态 —— 允许"存在但未跟踪"，但必须能被 add
        ignored = subprocess.run(["git", "check-ignore", "-q", "docs/cross-channel-oracle.json"],
                                 cwd=REPO_ROOT)
        assert ignored.returncode != 0, "oracle 被 .gitignore 忽略了，CI 上会失效"


# ── ② 变异自证：判据承重（改一个字节就必须红） ──────────────────────────────
def test_gate_would_catch_a_single_judgement_change(oracle):
    """把 oracle 里任意一条 finding 的 severity 改掉 → 比较必须发现（不是恒等式）。"""
    mutated = json.loads(json.dumps(oracle))
    target = None
    for case in mutated["cases"]:
        if case["report"]["findings"]:
            target = case["report"]["findings"][0]
            break
    assert target is not None, "oracle 里没有任何 finding —— 这道门是空转的"
    original = target["severity"]
    target["severity"] = {"error": "warn", "warn": "error"}.get(original, "error")

    current = current_runs()
    same = all(w["report"] == g["report"] and w["exit_code"] == g["exit_code"]
               for w, g in zip(mutated["cases"], current["cases"]))
    assert not same, "改了 finding 的 severity，比较仍报相同 —— 判据不是真的在比"


def test_gate_would_catch_an_extra_tool_field(oracle):
    """把 `tool` 里加回 `fonttools_version` → 比较必须发现（这条锚住 D2 的修法）。"""
    mutated = json.loads(json.dumps(oracle))
    mutated["cases"][0]["report"]["tool"]["fonttools_version"] = "4.57.0"
    current = current_runs()
    assert mutated["cases"][0]["report"] != current["cases"][0]["report"]


# ── ③ 可选：真起第二个解释器（本机双通道时的直接证据） ─────────────────────
def _probe(python):
    """这条解释器能不能跑本门？返回 (可跑?, fonttools 版本)。

    判据是**能导入 fontTools 与本包**，不是"这个 python 存在"。实测（2026-10-23 本机）：
    `py -3.12` 指向的系统解释器上**没有** fontTools（只有一个空壳），拿它当"第二通道"
    会让本门误红 —— 那不是"跨版本判定不一致"，而是"这条解释器没装依赖"。
    """
    script = ("import sys; sys.path.insert(0, %r);"
              "import fontTools, subsetaudit;"
              "print(fontTools.version)" % os.path.join(REPO_ROOT, "src"))
    try:
        proc = subprocess.run([python, "-X", "utf8", "-c", script], cwd=REPO_ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return False, ""
    if proc.returncode != 0:
        return False, ""
    return True, (proc.stdout or "").strip()


def _other_python():
    """找一条**可用的**第二解释器（能导入 fontTools + 本包），排除当前这条。"""
    explicit = os.environ.get("SUBSETAUDIT_CROSS_PYTHON")
    if explicit:
        ok, version = _probe(explicit)
        assert ok, "SUBSETAUDIT_CROSS_PYTHON=%r 跑不起来（缺 fontTools 或本包？）" % explicit
        return [(explicit, version)]

    candidates = []
    for tag in ("-3.8", "-3.12"):
        try:
            proc = subprocess.run(["py", tag, "-c", "import sys; print(sys.executable)"],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  universal_newlines=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        path = (proc.stdout or "").strip()
        if proc.returncode == 0 and path and os.path.abspath(path) != os.path.abspath(sys.executable):
            candidates.append(path)
    # 本仓库自己的 .venv 也算一条候选（本地开发时的常规形态）
    for sub in (os.path.join("Scripts", "python.exe"), os.path.join("bin", "python")):
        venv_python = os.path.join(REPO_ROOT, ".venv", sub)
        if os.path.isfile(venv_python) and os.path.abspath(venv_python) != os.path.abspath(sys.executable):
            candidates.append(venv_python)

    found, seen = [], set()
    for path in candidates:
        real = os.path.abspath(path)
        if real in seen:
            continue
        seen.add(real)
        ok, version = _probe(path)
        if ok:
            found.append((path, version))
    return found


def test_second_interpreter_agrees_when_available(oracle):
    """本机同时有另一条**可用的**解释器时，真跑它并逐字节比对（跨通道直接证据）。

    只有一条可用解释器时跳过 —— 跳过不等于通过：那个格子的证明责任由
    `test_current_channel_matches_checked_in_oracle` 与另一格共比同一份 oracle 承担。
    """
    others = _other_python()
    if not others:
        pytest.skip("本机只有一条可用解释器（跨通道证明由 CI 两格共比同一份 oracle 承担）")
    problems = []
    ran = 0
    for python, ft_version in others[:1]:
        # 另一条解释器**未必装了本包**（CI 的 3.8 格子装的就是 editable，本机 py -3.8 未必），
        # 所以显式把 `src/` 放进路径 —— 与 `tests/conftest.py` 的做法一致。
        script = ("import sys; sys.path.insert(0, %r); sys.path.insert(0, %r);"
                  "import test_cross_channel as t;"
                  "print(t._dump(t.current_runs()))"
                  % (os.path.join(REPO_ROOT, "src"), os.path.join(REPO_ROOT, "tests")))
        proc = subprocess.run([python, "-X", "utf8", "-c", script], cwd=REPO_ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)
        assert proc.returncode == 0, "另一通道跑挂了: %s\n%s" % (python, proc.stderr[-2000:])
        other = json.loads(proc.stdout)
        ran += 1
        for want, got in zip(oracle["cases"], other["cases"]):
            if want["report"] != got["report"] or want["exit_code"] != got["exit_code"]:
                problems.append("%s 在 %s（fontTools %s）上与 oracle 不同\n%s"
                                % (want["name"], python, ft_version,
                                   "\n".join(_diff_lines(want["report"], got["report"]))))
    assert ran >= 1
    assert problems == [], "\n\n".join(problems)
