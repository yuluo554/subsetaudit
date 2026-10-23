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
> 本次 v0.1.0 一共切了 **4 次**（见下方"首推红与重切"）——每一次重切都对**最新** `HEAD` 重打
> tag 并重建产物，所以 tag 与交付面始终一致；`plan/` 下的留档改动不改变任何被 tag 的字节。

### 交付面与远端

| 项 | 值 |
|---|---|
| tag | `v0.1.0`（annotated；tag 对象 `aee4831`） |
| tag → 提交 | `beba2d3`（= `HEAD`，交付面冻结于此） |
| 仓库 | <https://github.com/yuluo554/subsetaudit>（**PUBLIC**） |
| Release | <https://github.com/yuluo554/subsetaudit/releases/tag/v0.1.0>（非草稿，**2 个产物**） |

### 产物与校验和

| 产物 | 字节 | sha256 |
|---|---|---|
| `subsetaudit-0.1.0.tar.gz` | 101,608 | `eb8efc641ad9ddf6a5ff7936e29c4bcc60f1ab75a8b4b12198b872758e4463ed` |
| `subsetaudit-0.1.0-py3-none-any.whl` | 48,041 | `7675696a57e96c89968a22a63f4aa58722b93ce4694f4615d14c6c1f96390c9d` |

> **字节数是实测的**（`os.path.getsize`）。**对账做法**：`gh release download v0.1.0` 取回远端资产 →
> `sha256sum` 与本地 `dist/` 逐个比对 → **两者逐字节相同**（否则"Release 附产物"只证明了"传了个文件"）。
> 本文件这里**改过一次**：初稿把字节数写成了**凭记忆的数字**（100,072 / 47,979），与当次的实测值
> （101,219 / 47,823）不符 —— 被上面这套对账抓出来并更正。**教训：留档里的数字必须当场量，记忆不是证据。**
> （上表的数字是**最终 tag** 的实测值；中间各次重切的产物字节不同，此处不逐个留。）

两个产物都用 `py -m build --no-isolation` 从**冻结提交**（`beba2d3`）现场构建；sdist 与 wheel 里
**零字体二进制**（`.ttf/.otf/.ttc/.woff/.woff2` 各 0 个），wheel 内含 `LICENSE` 与
`Requires-Dist: fonttools<5,>=4.40`（dev extra 另带 pytest / PyYAML）。

### CI 实跑（`plan/05` 的"push 数 = run 数对账"）

| 事件 | run id | 触发 | 结论 |
|---|---|---|---|
| push `main`（`beba2d3`） | `39524912868` | push | ✅ success |
| push `v0.1.0`（`beba2d3`） | `39524926846` | push | ✅ success |

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
| **从 Release 下载的 wheel 再装一次**（`gh release download v0.1.0` → 干净 venv） | 五子命令 + `report` 判定可用；下载件 sha256 与本地 `dist/` **逐字节一致** |

### 首推红与重切（**如实的负面记录**）

`v0.1.0` 一共切了 **4 次**（3 次重切）：前两次是因为**首推的 CI 是红的**（四格同红、随后 windows 单格红），
后一次是因为**交付面里有与现行实现不符的过期说法**。逐条记录如下（不删不留白）：

| 次序 | 红在哪 | 根因（实测） | 处置（提交） |
|---|---|---|---|
| 第 1 次 | 四格同红：`RELEASE.FIXTURES_BITWISE gen_fixtures --check rc=1 ｜ ModuleNotFoundError: No module named 'fontTools'` | 我把"变异验证"排在了 `pip install` **之前**，但它现在会连"发布门"一起跑，而发布门要复跑 `gen_fixtures.py --check`（要 fontTools，且要有产物） | 顺序改为 install → 生成 fixture → 位级 `--check` → 变异验证；新增 `test_ci_generates_fixtures_before_any_gate_that_checks_them` 钉死顺序，`test_ci_installs_dependencies_before_scripts_that_need_them` 纳入 `verify_gates.py`；dev extra 补 `PyYAML`（否则 `tests/test_ci_workflow.py` 在 CI 里被整模块跳过，"顺序写错"无人看守 —— 正是这次盲区） |
| （同轮发现） | 判据本身是错的 | `RELEASE.PUSH_RUN_PARITY` 用 `git rev-list --count HEAD` 当"推送数" —— 那是**提交数**（14），不是推送数 | 改为"远端每个 ref 都必须有对应的 push 运行，且最近一次为绿"；运行未完则显式 SKIP |
| 第 2 次 | 仅 `windows-latest / py3.12`：`RELEASE.DESENS_GATE … FAIL .venv-readme/Scripts/Activate.ps1:31: [absolute-session-path]` | `README 安装路径实测`步骤在仓库根建 `.venv-readme/`，而脱敏门的 `SKIP_DIRS` 没收它（M0 加那一步时漏了）。命中的是 **venv 自带文档示例**里的 `C:\Users\<user>\Common\.venv`，不是真泄露 | `SKIP_DIRS` 补 `.venv-readme`，`SKIP_SUFFIXES` 收 `.egg-info`/`.dist-info`（`pip install -e .` 现生成）；`verify_gates.py` 的逐字节复核同样跳过它；docstring 写明"新增本地产物目录必须同步收编" |
| 第 3 次 | —— | —— | ✅ 四格全绿（run `39523508174` / `39523529638`） |
| 第 4 次 | **不是** CI 红 | 重切前复查交付面文字，发现 `README.md` / `AGENTS.md` 里仍写着与现行实现不符的说法：`verify_gates.py` 注释"两道门的变异验证（16 组）"（实为三道门 / 24 组）、README 命令块缺 `check_release.py --pre-tag`、"push 数 = 工作流运行数"的旧口径描述。它们**属交付面** → 按纪律重切而不是"顺手改无所谓" | 一次提交更正三处（并顺带更正 `plan/00` 的组数标注）；重切后四格全绿（run `39524912868` / `39524926846`） |

**前两次红都不是"判据太严"，而是"接线写错"**：第一次是步骤顺序，第二次是门的扫描面没收新出现的本地目录。
两条现在都有测试/判据钉住：顺序由 `tests/test_ci_workflow.py` 三条断言管，扫描面由
脱敏门对 `.venv-readme/` 的处置管。第三次重切则说明另一件事：**"tag 不能撒谎"这条纪律要落到
"发布前把交付面通读一遍"** —— 过期文字和错代码一样会让 tag 失真。

> 被重切淘汰的提交（`1f85b5b` / `269c3f4` / `a6bb715`）及其红/绿 run 仍留在仓库历史里，
> 不做删除：它们是"接线错误怎么被抓出来"的现场记录。

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
| 11 | CI 矩阵实跑（ubuntu/windows × 3.8/3.12） | 实现 | 四格全绿，run id `39524912868`（main）/ `39524926846`（v0.1.0）；`--online` 的 push 数 = run 数对账通过 |

---

# 附：v0.1.1 发布留档（发布面修正版，2026-10-23）

> v0.1.0 的留档在上方 §一–§三，**一个字未改**（已发布版本的事实用过去时保留）。
> v0.1.1 是**发布面修正版**：判定逻辑（五个子命令的规则与退出码）零改动，
> 改的是「README 能不能照抄跑」「报告样例会不会随环境漂」「跨版本判定有没有门」
> 「文档数字对不对」「CI action 版本」这五件事。
>
> 发布终态门：`py tools/check_release.py --pre-tag`（tag 前）/ 离线（tag 后）/
> `--online`（唯一联网档）。**v0.1.1 起多一条判据 `RELEASE.SHA256SUMS`**（见 §一末）。

## 四、v0.1.1 · tag 前事实（tag 之前成立；零网络）

| 项 | 值 | 证据 |
|---|---|---|
| 版本 | `0.1.1`（三处一致） | `src/subsetaudit/__init__.py` / `pyproject.toml` / `README.md` 状态行；`RELEASE.VERSION_TRIPLE` |
| 为什么发新版而不是重切 v0.1.0 | 修的是**文字与样例**，不是代码缺陷；重切会让"已被用户下载过的 v0.1.0"语义失真 | 本仓 v0.1.0 已重切 4 次（见 §二），第 5 次没有正当理由 |
| 报告样例 | `docs/report-sample.json`（`tool` 现在只有 `name` + `version`） | 现跑落盘，与 oracle 门共用同一命令；`RELEASE.SAMPLE_JSON` 断言 schema/版本/inputs + **不得含环境字段** |
| 跨版本冻结点 | `docs/cross-channel-oracle.json`（5 条命令 × 完整报告体） | `tests/test_cross_channel.py`：当前通道逐字节比对；3.12(4.67.0) 与 3.8(4.57.0) 实测一致 |
| README 最小复现 | 7 条命令全是真实路径，且每条标注 `rc=N` | `tests/test_readme_scenarios.py` 真跑子进程，退出码与标注一致；变异自证（改坏路径 → 4 条红） |
| 测试数自证 | `plan/05` 的「全量 **N 项**」与实测对账 | `tests/test_self_counts.py`（动态取 `--collect-only` 真值，不硬编码） |
| CI action 版本 | `actions/checkout@v7` / `actions/setup-python@v7` | `tests/test_ci_workflow.py::test_ci_actions_are_on_v7_or_newer`（判 ≥v7，升 v8 不红） |
| 测试（双解释器） | 3.12 → **303 passed**；3.8 → 见 §五 | `pytest -o addopts=""`（`addopts="-q"` 下再加 `-q` 会吞掉汇总行）；计数由 `test_self_counts.py` 与实测对账 |
| 四道门 | 布局 / 脱敏 / 发布全绿，变异 **25 项 25 符合预期、0 SKIP** | `verify_gates.py`（R9 为本版新增：改错 SHA256SUMS 一条摘要 → `RELEASE.SHA256SUMS` 必红）；组数由 `tests/test_self_counts.py` 与实测对账 |
| `SHA256SUMS` | `dist/SHA256SUMS` 覆盖 sdist + wheel，逐条与文件摘要相符 | `RELEASE.SHA256SUMS`（v0.1.1 新增判据，决策 D-M7-2）|
| 无字体二进制入库 | `git ls-files` 0 个字体二进制 | `RELEASE.NO_FONT_BINARIES` |

**v0.1.1 相对 v0.1.0 的交付面改动**（`src/` + `tests/` + `tools/` + `docs/` + `README.md`）：

| 文件 | 改动 | 判据落在哪 |
|---|---|---|
| `README.md` | 三段「最小复现」改真实路径 + 每条 `rc=N` + 安装段补 fixture 前置；`tool` 字段说明去 `fonttools_version`；发布节改 v0.1.1 | `test_readme_scenarios.py` |
| `src/subsetaudit/canonical.py` / `report.py` | `tool` 去掉 `fonttools_version`（Markdown 版本行同步） | `test_core.py::test_report_carries_no_environment_varying_field` + `RELEASE.SAMPLE_JSON` |
| `docs/report-sample.json` | 按 v0.1.1 重生成（`tool` 只剩两个键） | 门禁 2 的逐键 assert |
| `docs/cross-channel-oracle.json` | **新增**（跨版本冻结点，5 条命令） | `test_cross_channel.py` |
| `tests/test_readme_scenarios.py` | **新增**（6 条：解析/静态/真跑/三条变异自证） | 自身即判据 |
| `tests/test_cross_channel.py` | **新增**（7 条：比对/oracle 覆盖/无环境字段/入库/两条变异/第二解释器） | 自身即判据 |
| `tests/test_self_counts.py` | **新增**（5 条：声明唯一/与实测一致/变异/新门在位） | 自身即判据 |
| `tests/test_ci_workflow.py` | 新增一条 `≥v7` 判据 | 变异自证：改回 v4 → 红 |
| `tools/check_release.py` | `SAMPLE_JSON` 加"禁环境字段"否定断言；新增 `RELEASE.SHA256SUMS` | `verify_gates.py` R3/R9 |
| `tools/check_desensitized.py` | `SKIP_DIRS` 收编 `update/` | 脱敏门自身（扫 75 文件 0 命中） |
| `tools/verify_gates.py` | R1/R3 靶子改 `current_version()` 动态取值；新增 R9 | 自身（25 项全符合预期；组数由 `tests/test_self_counts.py` 与实测对账） |
| `.github/workflows/ci.yml` | `checkout@v4→v7`、`setup-python@v5→v7`（步骤名/次序未动） | `test_ci_workflow.py` 12 条原有断言仍绿 |
| `.gitignore` | 加 `update/` | 第 0 批卫生 |

## 五、v0.1.1 · tag 后追加事实

> **本节在 tag 之后填写**。以下数值全部**当场量**（`git rev-parse` / `stat` / `sha256sum` / `gh api`）。
> 状态：**已发布**。⚠ 这是**用户明确决定跳过独立人工终态复验**（2026-10-23）之后按已发布收尾，
> **不是执行方自宣完成** —— 证据链是执行方提供的实测记录（本节 + `update/03-执行记录.md`），
> 独立复核这一环被用户显式免除。执行方自己登记的**未做/未验证事项**见 `update/03-执行记录.md` §六。

| 项 | 值 |
|---|---|
| tag / 提交 | annotated `v0.1.1`（对象 `6a7e502512bea1edd44c7ebb24433aa256a0d679`）→ 冻结提交 `bc2a839e4d50c7a07d640005fc80a3136a6c0283`（= `main` HEAD，远端 `refs/tags/v0.1.1` 同值） |
| 仓库 / Release | `https://github.com/yuluo554/subsetaudit`（PUBLIC）；Release `v0.1.1`（`draft=false` / `prerelease=false` / Latest），附 **3** 个产物：sdist / wheel / `SHA256SUMS` |
| 产物字节数与 sha256 | `subsetaudit-0.1.1-py3-none-any.whl` **49,646 B** `e200070549df1233b7de4bcaa131f4c4639ca84953d60fb43d14d6848a3167aa`；`subsetaudit-0.1.1.tar.gz` **117,391 B** `d71a82f6a40bff85fe22ed1ccc27c1cc70c0a2ea1612300763a2f47a7a689bec`；`SHA256SUMS` **192 B** `30ebd95d8be7e9cf44087ca3f4f84f8e38f4184e8b9f135e8b5f35b586102fef`。**四方一致**（本地 `dist/` / Release 元数据 / GitHub asset `digest` / 匿名下载重算） |
| CI run id（main / tag） | `main` push **39905828447**（`bc2a839`，2026-10-23T05:27:11Z）；tag `v0.1.1` push **39906418656**（`bc2a839`，2026-10-23T05:33:30Z）。**两次均 4 格全 success**（ubuntu/windows × 3.8/3.12） |
| Node20 弃用注解 | **0 条**（两次 run 的各 job 逐条查过；只剩 2 条 `ubuntu-latest → Ubuntu 26` 迁移 notice，属外部信号、非本仓可修） |
| 匿名验收 | **不带 token**：`api.github.com/.../releases/latest` → `tag_name=v0.1.1`、`draft=False`、3 附件；三件经**匿名** API（`Accept: application/octet-stream`）真下载，字节数全对、sha256 与 GitHub `digest` 逐字符一致、`SHA256SUMS` 自洽（`sha256sum -c` 通过）。⚠ **直链 200 未测**：本机 `github.com:443` 当刻不通（`curl` 000，同时刻 `api.github.com` 200）—— 故走匿名 API 通道，**不谎称测过直链** |
| 干净环境装 wheel 后跑真场景 | 新建 py3.12 venv → `pip install` **匿名下载的** wheel → `--version` = `subsetaudit 0.1.1`；五子命令 `--help` 全 rc=0；真场景 `license-gate data/fixtures/fstype-nosubset/out/fstype-nosubset.ttf` → **rc=1**（如 README 所标）；装态 `report` 与 `docs/report-sample.json` **逐键一致**、`tool` 无 `fonttools_version` |
| tag 后发布门 | 离线档 rc=0；`--online` 档 **17 PASS / 0 FAIL / rc=0**（含 `REMOTE_TAG` / `REMOTE_RELEASE assets=3` / `PUSH_RUN_PARITY` —— **远端每个 ref 的最近 push 运行均为 success**，具体 ref 数随分支增删变化，故不写死） |
| tag 后的留档提交 | `bb7b665`（本节回填 + §六第 11 项转「实现」）。**只改 `plan/`，交付面自 tag 起零改动**（`git diff v0.1.1 -- src tests tools data docs LICENSE pyproject.toml README.md` 为空）；`RELEASE.TAG_EXISTS` 仍 PASS（tag 是 HEAD 的祖先）。本仓惯例同 v0.1.0（tag 后另有 1 个文档提交）。`main` 上该提交的 run **39906907915** 亦 4 格全 success |

## 六、v0.1.1 · 覆盖对账

| # | 交付物 | 状态 | 证据 |
|---|---|---|---|
| 1 | 可安装 CLI（五子命令） | 实现 | `RELEASE.SUBCMDS`；干净 venv 真装后 `--version` + 真场景 rc=1 |
| 2 | 源实现（五模块 + 共享层） | 实现 | `src/subsetaudit/`（判定逻辑本版零改动） |
| 3 | 6 类合成破损 fixture | 实现 | `gen_fixtures.py --check` 位级一致 |
| 4 | OFL 字体回归套件 | 实现 | `data/fonts.lock` + `fetch_fonts.py --check`（离线；CI 上 6 条 SKIP，如实标注） |
| 5 | 测试套件 | 实现 | `pytest -o addopts=""` 双解释器全绿（计数由 `test_self_counts.py` 与实测对账） |
| 6 | 报告样例 | 实现 | 现跑落盘；`RELEASE.SAMPLE_JSON`（含"禁环境字段"否定断言） |
| 7 | README（安装 + 三场景 + 字段 + 边界 + 护城河） | 实现 | **本版起由 `test_readme_scenarios.py` 真跑**，不只是参数面反驳 |
| 8 | 发布留档（本文件 §四–§六） | 实现 | 两栏 + 本表 + `LAYOUT.RELEASE` |
| 9 | 手工源码包 + 校验附件 | 实现 | `py -m build --no-isolation` 从冻结提交产出；`SHA256SUMS` 由 `RELEASE.SHA256SUMS` 逐条校验 |
| 10 | `WRAPUP-M6.md` 形态替代 | 不适用 | 本仓库采用 `RELEASE-M6.md` 两栏形态（布局门两种形态二选一） |
| 11 | CI 矩阵实跑（ubuntu/windows × 3.8/3.12） | 实现 | `main` run **39905828447** + tag `v0.1.1` run **39906418656**，两次均 4 格全 success、Node20 注解 0（见 §五） |
| 12 | 跨版本判定一致性 | 实现 | `docs/cross-channel-oracle.json` + `test_cross_channel.py`（两格共比同一份 oracle） |
