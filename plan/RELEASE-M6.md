# RELEASE-M6 · v0.1.0 发布留档

> 两栏口径：**一** = tag 之前就已成立的事实（只落仓库内文件，零网络）；**二** = tag 之后才存在的事实
> （远端、产物哈希、CI run、对账）。**改这一份文件不构成"改交付面"**：交付面 = `src/` + `tests/` +
> `tools/` + `data/` + `docs/report-sample.json` + `LICENSE` + `pyproject.toml` + `README.md`；
> 本文件第二栏的设计目的就是"tag 后追加"。
> 发布终态门：`py tools/check_release.py --pre-tag` / 离线（默认）/ `--online`。

## 一、tag 前事实（tag 之前成立；零网络）

| 项 | 值 | 证据 |
|---|---|---|
| 版本 | `0.1.0`（三处一致） | `src/subsetaudit/__init__.py` / `pyproject.toml` / `README.md` 状态行；`tests/test_cli.py` 两条断言 + `check_release.py RELEASE.VERSION_TRIPLE` |
| 许可 | LICENSE = MIT License；`pyproject.toml` `license = { text = "MIT" }` | `check_release.py RELEASE.LICENSE_CONSISTENT` |
| 报告样例 | `docs/report-sample.json`（schema `subsetaudit/report@1`，`tool.version = 0.1.0`） | 用现行实现现跑：`report --source data/fixtures/codepage-mismatch/out/source.ttf --subset data/fixtures/codepage-mismatch/out/subset.ttf --text "汉字"`（退出码 1 = 有 `error` 级发现，符合预期） |
| 五子命令 | `license-gate` / `coverage-diff` / `layout-survival` / `metadata` / `report` | `check_release.py RELEASE.SUBCMDS`（含 `report` 的六个数据源参数） |
| 无字体二进制入库 | `git ls-files` 0 个 `.ttf/.otf/.ttc/.woff/.woff2` | `check_release.py RELEASE.NO_FONT_BINARIES`（先比对 git toplevel = 本项目根） |
| 布局门 | 全绿（9 判据） | `py tools/check_sprint_layout.py` → rc 0 |
| 脱敏门 | 0 命中 | `py tools/check_desensitized.py` → rc 0 |
| fixture 位级一致 | 22 个文件逐字节一致 | `py tools/gen_fixtures.py --check` → rc 0 |
| 变异验证 | 16 项全符合预期、0 SKIP（靶子已改为**不依赖下一个 ⬜ 里程碑**） | `py tools/verify_gates.py` → rc 0 |
| `PENDING_TOOLS` | 清空为 `{}`（`tools/check_release.py` 已落盘自清理） | `check_release.py RELEASE.PENDING_TOOLS_CLEARED` |
| 测试（双解释器） | 3.8 与 3.12 两通道全绿 | `py -X utf8 -m pytest -q` / `_scratch/v312` |
| 冒烟 | 11 条命令 0 失败 | `py tools/smoke_cli.py` |
| 干净环境安装 | 新 venv `pip install -e .` 后五子命令可用（含 `report --help`） | 见 §二「干净环境实测」 |

## 二、tag 后追加事实

> **本节在 tag 之后填写**（见文件头：这是本文件的唯一存在理由）。

（tag 后回填：tag 名与 commit sha / 远端仓库 URL / Release URL 与产物 sha256 / CI run id / push 数 = run 数对账 / 干净环境实测结论）

### 干净环境实测

（tag 后回填：`python -m venv` → 升级 pip → `pip install -e .` → 五子命令 + `report --help` 的逐条退出码）

## 三、阶段 7 覆盖对账

> 三态：**实现** = 交付物在位且有可复跑证据；**不适用** = 该形态在本仓库不成立；**待首推** = 需远端才成立。

| # | 交付物（`plan/01` §四） | 状态 | 证据 |
|---|---|---|---|
| 1 | 可安装 CLI（五子命令） | 实现 | `pyproject.toml` `[project.scripts]`；干净 venv `subsetaudit --version` |
| 2 | 源实现（五模块 + 共享层） | 实现 | `src/subsetaudit/`，`git ls-files src` 可核对 |
| 3 | 6 类合成破损 fixture | 实现 | `tools/gen_fixtures.py --check` → 22 文件位级一致 |
| 4 | OFL 字体回归套件 | 实现 | `data/fonts.lock` + `tools/fetch_fonts.py --check`（离线；缺文件报 `MISSING`） |
| 5 | 测试套件 | 实现 | `pytest -q` 双解释器全绿 |
| 6 | 报告样例 `docs/report-sample.json` | 实现 | 现跑落盘；`RELEASE.SAMPLE_JSON` 断言 schema/版本/inputs 同源 |
| 7 | README（安装 + 三场景 + 字段 + 边界 + 护城河） | 实现 | 干净 venv 里真敲三条场景命令 |
| 8 | 发布留档（本文件） | 实现 | 两栏 + 本表 + `LAYOUT.RELEASE` 逐条断言 |
| 9 | 手工源码包（sdist + wheel） | 待首推 | tag 后由 `py -m build --no-isolation` 产出，sha256 记入 §二 |
| 10 | `WRAPUP-M6.md` 形态替代 | 不适用 | 本仓库采用 `RELEASE-M6.md` 两栏形态（布局门两种形态二选一） |
| 11 | CI 矩阵实跑（ubuntu/windows × 3.8/3.12） | 待首推 | 首推后登记 run id（`check_release.py --online` 的 push 数 = run 数对账） |
