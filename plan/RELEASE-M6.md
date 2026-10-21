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
>
> **§二 的落笔本身是"tag 后提交"，但它不是"改交付面"**：交付面 = `src/` + `tests/` + `tools/` +
> `data/` + `docs/report-sample.json` + `LICENSE` + `pyproject.toml` + `README.md`。
> 本次 v0.1.0 是**第三次切 tag**（见下方"首推红与重切"）——每一次重切都对**同一条** `HEAD` 重打
> tag 并重建产物，所以 tag 与交付面始终一致；`plan/` 下的留档改动不改变任何被 tag 的字节。

### 交付面与远端

| 项 | 值 |
|---|---|
| tag | `v0.1.0`（annotated；tag 对象 `766876e`） |
| tag → 提交 | `a6bb715`（= `HEAD`，交付面冻结于此） |
| 仓库 | <https://github.com/yuluo554/subsetaudit>（**PUBLIC**） |
| Release | <https://github.com/yuluo554/subsetaudit/releases/tag/v0.1.0>（非草稿，**2 个产物**） |

### 产物与校验和

| 产物 | 字节 | sha256 |
|---|---|---|
| `subsetaudit-0.1.0.tar.gz` | 101,219 | `d55508818488a2dfeaf54fa026d5038a8bbda246db4b50948f8b6587a5c175ae` |
| `subsetaudit-0.1.0-py3-none-any.whl` | 47,823 | `b7db60c565e7e82677d92068a83609fead700130871d2eb9f6316014ed7fa84a` |

> **字节数是实测的**（`os.path.getsize`）。**对账做法**：`gh release download v0.1.0` 取回远端资产 →
> `sha256sum` 与本地 `dist/` 逐个比对 → **两者逐字节相同**（否则"Release 附产物"只证明了"传了个文件"）。
> 本文件这里**改过一次**：初稿把字节数写成了**凭记忆的数字**（100,072 / 47,979），与真实值
> （101,219 / 47,823）不符 —— 被上面这套对账抓出来并更正。**教训：留档里的数字必须当场量，
> 记忆不是证据。**

两个产物都用 `py -m build --no-isolation` 从**冻结提交**（`a6bb715`）现场构建；sdist 与 wheel 里
**零字体二进制**（`.ttf/.otf/.ttc/.woff/.woff2` 各 0 个），wheel 内含 `LICENSE` 与
`Requires-Dist: fonttools<5,>=4.40`（dev extra 另带 pytest / PyYAML）。

### CI 实跑（首推之后；`plan/05` 的"push 数 = run 数对账"）

| 事件 | run id | 触发 | 结论 |
|---|---|---|---|
| push `main` | `39523508174` | push | ✅ success |
| push `v0.1.0` | `39523529638` | push | ✅ success |

**对账口径**（`check_release.py --online` 的 `RELEASE.PUSH_RUN_PARITY`）：远端 ref = 2 个
（`refs/heads/main`、`refs/tags/v0.1.0`），**每个 ref 都有对应的 push 事件运行，且最近一次结论都是 success**。
矩阵为 `ubuntu-latest`/`windows-latest` × Python `3.8`/`3.12` 四格；每格依次跑布局门 → 脱敏门 →
install → 生成 fixture → 位级 `--check` → 变异验证 → 离线锁文件 → README 安装路径实测 → 测试 →
冒烟 → 发布门 `--pre-tag`。

### 干净环境实测（本机，Windows + Python 3.8）

| 步骤 | 结果 |
|---|---|
| 新 venv + 升级 pip + `pip install -e ".[dev]"` | 成功（editable wheel 构建通过 PEP 660） |
| `subsetaudit --version` | `subsetaudit 0.1.0` |
| 五子命令 `--help`（含 `report --help` 的六个数据源/格式参数） | 五个全 rc=0 |
| 三条 README 场景（`license-gate` / `coverage-diff --text "汉字abc"` / `layout-survival` + `metadata` + `report --format markdown`） | 全部真敲通过（`metadata`/`report` 在 F6 上 rc=1 = 有 error 级发现，符合预期） |
| 非字体文件（`does-not-exist.ttf`） | rc=2 且 stderr 指明文件 |
| **wheel 单独安装**（另一只干净 venv，只装 `dist/*.whl`） | 五子命令 + `report --help` 可用 → 附件自足 |

### 首推红与重切（**如实的负面记录**）

首次推送的 CI **是红的**，四矩阵格子同红；重切 tag 共两次。逐条记录如下（不删不留白）：

| 次序 | 红在哪 | 根因（实测） | 处置（提交） |
|---|---|---|---|
| 第 1 次 | 四格同红：`RELEASE.FIXTURES_BITWISE gen_fixtures --check rc=1 ｜ ModuleNotFoundError: No module named 'fontTools'` | 我把"变异验证"排在了 `pip install` **之前**，但它现在会连"发布门"一起跑，而发布门要复跑 `gen_fixtures.py --check`（要 fontTools，且要有产物） | 顺序改为 install → 生成 fixture → 位级 `--check` → 变异验证；新增 `test_ci_generates_fixtures_before_any_gate_that_checks_them` 钉死顺序，`test_ci_installs_dependencies_before_scripts_that_need_them` 纳入 `verify_gates.py`；dev extra 补 `PyYAML`（否则 `tests/test_ci_workflow.py` 在 CI 里被整模块跳过，"顺序写错"无人看守 —— 正是这次盲区） |
| （同轮发现） | 判据本身是错的 | `RELEASE.PUSH_RUN_PARITY` 用 `git rev-list --count HEAD` 当"推送数" —— 那是**提交数**（14），不是推送数 | 改为"远端每个 ref 都必须有对应的 push 运行，且最近一次为绿"；运行未完则显式 SKIP |
| 第 2 次 | 仅 `windows-latest / py3.12`：`RELEASE.DESENS_GATE … FAIL .venv-readme/Scripts/Activate.ps1:31: [absolute-session-path]` | `README 安装路径实测`步骤在仓库根建 `.venv-readme/`，而脱敏门的 `SKIP_DIRS` 没收它（M0 加那一步时漏了）。命中的是 **venv 自带文档示例**里的 `C:\Users\<user>\Common\.venv`，不是真泄露 | `SKIP_DIRS` 补 `.venv-readme`，`SKIP_SUFFIXES` 收 `.egg-info`/`.dist-info`（`pip install -e .` 现生成）；`verify_gates.py` 的逐字节复核同样跳过它；docstring 写明"新增本地产物目录必须同步收编" |
| 第 3 次 | —— | —— | ✅ 四格全绿（见上表 run id） |

**两次红都不是"判据太严"，而是"接线写错"**：第一次是步骤顺序，第二次是门的扫描面没收新出现的本地目录。
两条现在都有测试/判据钉住：顺序由 `tests/test_ci_workflow.py` 三条断言管，扫描面由
脱敏门对 `.venv-readme/` 的处置管。

**留档自身也被门抓过一次（如实记）**：写本节时把 venv 文档示例的路径**逐字**抄进了 `plan/`，
下一次跑脱敏门就报 `absolute-session-path`（3 处命中）。处置 = 改成占位符形式
（`C:\Users\<user>\…`，脱敏门的规则对 `<` 开头的占位符放行）。⇒ **写留档也会踩脱敏门，
每次改文档都要跑它**（`plan/06` G2 也是这么要求的）。

### 已知未验证项（发布时点）

- `tools/fetch_fonts.py --download` 的**端到端稳定性**仍未验证：本机实测
  `raw.githubusercontent.com` 会在传输中重置；脚本走单次请求、校验在写盘前（不稳时报
  `DOWNLOAD_FAILED` 而不写半截文件），但"一次跑通"未复现 → **不宣称 `--download` 可用**。
  因此 CI 与本地测试里 **6 个 OFL 真实字体用例会 SKIP**（`data/fonts/` 未下载），这是**如实标注**，
  不是"测试全绿"。

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
| 9 | 手工源码包（sdist + wheel） | 实现 | `py -m build --no-isolation` 从冻结提交产出；两个 sha256 记入 §二；wheel 单独装在干净 venv 里可用 |
| 10 | `WRAPUP-M6.md` 形态替代 | 不适用 | 本仓库采用 `RELEASE-M6.md` 两栏形态（布局门两种形态二选一） |
| 11 | CI 矩阵实跑（ubuntu/windows × 3.8/3.12） | 实现 | 四格全绿，run id `39523508174`（main）/ `39523529638`（v0.1.0）；`--online` 的 push 数 = run 数对账通过 |
