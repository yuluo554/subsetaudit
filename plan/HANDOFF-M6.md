# HANDOFF-M6 · 发布（交接单 · **M6 已收尾**）

> 上一棒：M5（元数据与报告：`metadata` 五组判定 + `report` 单一路径聚合 + §六.9 口径），状态 ✅。
> 本棒：**M6 发布**（GitHub 公开仓库 v0.1.0：tag + Release 附产物 + `plan/RELEASE-M6.md` 三件套），状态 ✅。
> **下一棒：无**（M6 是最后一个里程碑）。后续改动按 §二 的"发布后不变量"处理。
> **第一动作（硬约束③）**：先跑 `py tools/check_sprint_layout.py`，红了先修布局再动手。

## 一、当前进度与证据

| 项 | 状态 | 证据（命令 + 结果） |
|---|---|---|
| 方法论装订 + 计划套件 | ✅ | `py tools/check_sprint_layout.py` → **9 PASS / 0 FAIL**（含 LAYOUT.RELEASE 两栏 + 覆盖对账 12 行三态） |
| 布局门 / 脱敏门 / 发布门 | ✅ | `py tools/verify_gates.py` → **24 项全符合预期、0 SKIP**；脱敏门扫 71 个文本文件 0 命中 |
| 可运行骨架 + 退出码契约 | ✅ | 五子命令 exit 0；非字体文件 exit 2；`py tools/smoke_cli.py` **11 条 0 失败** |
| M1 数据先行 | ✅ | `gen_fixtures.py --check` → 22 个文件位级一致；`fetch_fonts.py --check` 离线报 3 个 MISSING |
| M2 许可闸门 | ✅ | F1/F2/F3 golden 逐项；五元结论 + 六条违规码；560 face 真实池复跑 0 误报 |
| M3 覆盖差集 | ✅ | §六.2–§六.4；F4 golden 三方对齐；381 指纹 |
| M4 布局保真 | ✅ | §六.5.1–5.6；Type 7/9 解包；三条 finding；37 项测试 |
| M5 元数据口径 | ✅ | `data/README.md` §六.9（9.1–9.7）：name 七 ID + 三分类 / 码页只判 bit0 / `ulUnicodeRange` 不对称判定 / `maxp` 独立量 / 首末码位单向 / 四条失败路径 / report 单一路径 |
| M5 `metadata` + `report` | ✅ | finding 码十条；`summary["metadata"]` 不占 `conclusions`（K15）；聚合单一路径（K26） |
| **M6 `tools/check_release.py`** | ✅ | 三档发布终态门：`--pre-tag`（10 判据）/ 离线（+tag+dist）/ `--online`（+远端 16 判据）；顶层只用标准库（AST 解析 `cli.py`）；`PENDING_TOOLS` 已清空（K10） |
| **M6 版本 / 许可** | ✅ | `0.1.0` 三处一致；`LICENSE`=MIT License 与 `pyproject.toml` 的 `license = { text = "MIT" }` 一致 |
| **M6 报告样例** | ✅ | `docs/report-sample.json` 用现行实现现跑（F6 源+产物+`--text "汉字"`，rc=1） |
| **M6 干净环境** | ✅ | 新 venv `pip install -e ".[dev]"` → `--version` + 五子命令 `--help` + 三条 README 场景真敲通过；**wheel 单独安装**亦可用 |
| **M6 tag / Release** | ✅ | tag `v0.1.0` → `a6bb715`；公开仓库 + Release（2 产物，sha256 记入 `plan/RELEASE-M6.md` §二） |
| **M6 CI 实跑** | ✅ | 四格全绿：`main` run `39523508174` / tag run `39523529638`；`--online` 的 push 数 = run 数对账通过 |
| **M6 发布留档** | ✅ | `plan/RELEASE-M6.md` 两栏 + 阶段 7 覆盖对账（11 行：实现/不适用）+ 首推红的如实记录 |

## 二、当前事实·状态不变量（发布之后；动任何东西前必须知道）

1. **`v0.1.0` 已冻结在提交 `a6bb715`**。交付面 = `src/` + `tests/` + `tools/` + `data/` +
   `docs/report-sample.json` + `LICENSE` + `pyproject.toml` + `README.md`。
   **改交付面 = 让 tag 撒谎**：要么不动，要么**重切 tag**（删远端 Release/tag → 重打 → 重建产物 →
   sha256 同步进 `plan/RELEASE-M6.md` §二），并把重切原因如实写进留档。
   `plan/` 下的留档改动（含 `plan/RELEASE-M6.md` §二 本身）**不算**改交付面。

2. **`PENDING_TOOLS` 现在是 `{}`，且这是正确形态。** 不再有"文档点名但未落位"的工具；
   文档里写一个新脚本名而实物不存在 → `LAYOUT.DOC_TOOLS` **立刻红**，没有登记表兜底（K10）。
   新增工具时**先落实物、再写进文档**。

3. **`verify_gates.py` 覆盖三道门 24 组**（布局 12 / 脱敏 4 / **发布 8**）。发布门那 8 组跑在
   `--pre-tag` 档（离线零网络）。**Online 档的判据不在变异面内**（需要网络与远端事实，
   而 CI 与变异验证必须离线）—— 其可证伪性靠"用不存在的 tag/未推的 ref 跑一次负向探针"，
   发布棒手工做、结果记留档。

4. **"下一个 ⬜ 里程碑"机制已退役**（M6 是最后一个）。`verify_gates.py` 里的
   `_create` / `RELEASE_STUB` / `HANDOFF_STUB_INCOMPLETE` / `_mark_done` 四个 helper 已删除；
   所有靶子打在**既有真实交付面**上（M5 的交接单、`plan/RELEASE-M6.md`、台账行、`PENDING_TOOLS`、
   `cli.py` 参数面、git 索引）。**不要**再把靶子写成"先把某里程碑翻 ✅、再改坏它的收尾件"。

5. **`metadata` / `report` 的"不对称判定"是承重设计，不得"补齐"**（K24）：`ulUnicodeRange` 只判
   过度声明、码页只判 bit0、首末码位只判单向、name 无源不分类。任一条改严都会打挂
   `tests/test_metadata.py` 的反例守护。

6. **`bit57`（`Non-Plane 0 *`）是行为型位**（判定式 = 存在 `> U+FFFF` 码位，不按区间比）；
   `metadata.is_behavioral_bit()` 是识别入口，有测试钉住。

7. **`report` 聚合只有一条路径**：`report.evaluate` → `aggregate` → `merge_summaries`；
   `MODULE_ORDER` 是承重表；键冲突 → `SUMMARY_KEY_COLLISION`（`error`）。**不要再加"顺便聚合一下"的代码**。

8. **状态副本 = 3 处 + 1 处台账**：`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态表，
   外加 `plan/00` 的承诺-证据台账。**翻状态必须四处一起翻**（当前 M0–M6 全 ✅）。

9. **发布门的三档语义别搞混**：`--pre-tag` **只落仓库内文件、零网络**；离线档才查本地 tag 与
   `dist/`；**只有 `--online` 联网**。CI 里只跑 `--pre-tag`（`--online` 需要 token 与远端事实）。

10. **`RELEASE.SAMPLE_JSON` 绑版本**：`docs/report-sample.json` 的 `tool.version` 必须等于现行
    `__version__` —— **改版本号后必须重新生成该样例**，否则发布门红（这是设计，不是误报）。

11. **报告不含时间戳/绝对路径/主机名/用户名**；`inputs` 只存 basename（K5）。新增任何"样例/留档"
    文本前先想一遍脱敏门（4 条规则在 `tools/check_desensitized.py` 顶部）。

12. **`sfnt.py` 只读纪律**：仍然没有 `.save(`（`tests/test_core.py::test_read_only_layer_never_saves`）；
    `cmap_codepoints` **只并 Unicode 子表**（并进 `(1,0)` 会让 `no_unicode_cmap` 判不出来）。

13. **字体二进制永不入仓**：`git ls-files` 里 0 个 `.ttf/.otf/.ttc/.woff/.woff2`（发布门 + 测试各钉一遍）。

14. **`expect.json` 的 `fonttools_version` 是铸造版本常量**（`GOLDEN_FONTOOLS_VERSION = "4.57.0"`），
    不是运行时版本（K12）；fixture 生成禁时钟（K13）。

15. **`report-sample.json` 与 `data/fonts.lock` 一类"记录型"产物**：前者入仓（`docs/`），
    后者入仓（只有 URL+字节数+sha256）；**字体本体、fixture 产物、`dist/` 全不入仓**。

## 三、待办（M6 收尾后：**没有下一棒**）

本棒已把 M6 的六条 DoD 全部关闭（见 §六）。**没有排队的下一棒**。若后续要动，按下列顺序：

1. **先跑三道门 + 全量测试**（§七 命令速查第一条）。红了先修门再改东西。
2. **改交付面 → 必须重切 tag**（§二.1）。改 `plan/` 留档则不必。
3. **改版本号 → 三处一起改 + 重新生成 `docs/report-sample.json`**（§二.10）。
4. **改 `tools/check_desensitized.py` 的扫描面时**：`.gitignore` 里每一条"本地产物/环境"目录
   都必须在 `SKIP_DIRS`（或 `SKIP_SUFFIXES`）里有对应项 —— 否则 CI 上会出现**假红**（K27）。
5. **动 CI 的 `steps` 顺序时**：需要 fontTools 或需要 fixture 产物的步骤，必须排在
   `pip install` 与"生成 fixture"**之后**（K28）。
6. 若要让 `tools/fetch_fonts.py --download` 变成"可用"的宣称：先补一次端到端实测，
   否则保持 ⬜（当前 6 个 OFL 真实字体用例在 CI/本机是 **SKIP**，如实标注）。

## 四、既定口径清单（K 编号，动了会打挂测试）

> 本棒把 K1–K26 原样带过来（K1–K22 见 `plan/HANDOFF-M5.md` §四，K23–K26 由 M5 棒新增），
> 并新增 K27 / K28（全部来自 M6 首推的**实测**）。**论证处只在 `plan/00` 决策记录**，此处只列口径与落点。

| K | 口径 | 落点 |
|---|---|---|
| K1 | 数值口径**单点**在 `data/README.md` §六；代码与文案不得另立 | `plan/01` §三，`plan/04` §5 |
| K2 | 退出码 0/1/2 只在 `cli.main` 收口；argparse 用法错误天然是 2 | `cli.py`，`plan/02` §3 |
| K3 | `SKIPPED(reason=...)` 恒 note、恒进输出、恒不影响退出码 | `canonical.skipped` |
| K4 | 排序键 `(module, severity, primary_key)`；JSON 键序在构造处固定，不用 `sort_keys` | `canonical.sort_findings` / `build_report` |
| K5 | 报告不含时间戳/绝对路径/主机名/用户名；`inputs` 只存 basename | `canonical.input_ref` |
| K6 | 共享层只读：`sfnt.py` 不得出现 `.save(`（有测试钉住） | `tests/test_core.py::test_read_only_layer_never_saves` |
| K7 | 零网络零模型：包内不得 import `urllib/requests/socket/...`、模型库 | `tests/test_cli.py::test_no_runtime_network_or_model_imports` |
| K8 | 代码底线 Python 3.8（无 `tomllib`、无 3.9+ 语法、无 `Path.write_text(newline=)`） | `pyproject.toml` requires-python |
| K9 | 版本三处一致：`__init__.__version__` / `pyproject.toml` / README 状态行 | 两条测试 + `RELEASE.VERSION_TRIPLE` |
| K10 | 布局门 `PENDING_TOOLS` 登记项**随里程碑翻 ✅ 自清理**（现在为 `{}` = 无未落位工具） | `tools/check_sprint_layout.py` 顶部 |
| K11 | 门的变异验证常驻 `tools/verify_gates.py`，每棒收尾重跑；靶子随进度翻新 | CI step（现 24 组：布局 12 / 脱敏 4 / 发布 8） |
| K12 | **golden 的 `fonttools_version` = 铸造版本常量**，不是运行时版本 | `tools/gen_fixtures.py::GOLDEN_FONTOOLS_VERSION` |
| K13 | **fixture 生成禁时钟**：`head.created/modified` 钉 `FIXED_EPOCH`；`TTFont(..., recalcTimestamp=False)` | `tools/gen_fixtures.py::_subset` |
| K14 | `data/README.md` §六.1 的五元判定式与六条违规码是 `license-gate` 唯一口径；`SPEC_REFS` / `CODE_SPEC_REFS` 是逐字副本 | `license_gate.py`，`tests/test_license_gate.py` |
| K15 | **`summary["conclusions"]` 的形状固定为 `{key: {"value": bool, "spec_ref": str}}`**；别的模块不要占用该键 | `canonical._render_conclusions` |
| K16 | **`data/README.md` §六.2–§六.4 是 `coverage-diff` 唯一口径**；`SPEC_REF = "data/README §6.2"` 是逐字副本 | `coverage_diff.py`，`tests/test_coverage_diff.py` |
| K17 | **分区是互斥分区且判定有序**：`ExtA → ExtB+ → BMP → other`；ExtA 先于 BMP | `cmapset.block_of`，`tests/test_core.py` |
| K18 | **闭包只计数、不产 finding、不回流进三分类**（三分类只用 `R0`） | `coverage_diff._closure_summary` |
| K19 | **`data/README.md` §六.5.1–§六.5.6 是 `layout-survival` 唯一口径**；`SPEC_REF = "data/README §6.5"` 是逐字副本 | `layout_survival.py`，`tests/test_layout_survival.py` |
| K20 | **Extension lookup 两张表类型号不同：GSUB = 7、GPOS = 9**，**必须都解包**；`naive` 只数未包装子表、只作对照 | `sfnt.EXTENSION_LOOKUP_TYPES`，`tests/test_layout_survival.py` |
| K21 | **连字规则的同一性按「输入码位序列」判**，不按字形名、不按 GID 数值 | `layout_survival._ligature_index` |
| K22 | **`LAYOUT_LIGATURE_RENAMED` 是 `warn`、与 `LOST` 互斥（先判 LOST）** | `layout_survival._is_renamed` |
| **K23** | **`data/README.md` §六.9.1–§六.9.7 是 `metadata` / `report` 唯一口径**；`SPEC_REF = "data/README §6.9"` 是逐字副本，测试逐条解析小节标题做对账 | `metadata.py` / `report.py`，`tests/test_metadata.py` / `tests/test_report.py` |
| **K24** | **元数据判定是"不对称"的**：只判可证矛盾（`ulUnicodeRange` 只判过度 / 码页只判 bit0 / 首末码位只判单向 / name 无源不分类） | `metadata._judge`，两组反例守护 |
| **K25** | **`maxp` 的"实际字形数"必须独立于 `maxp`**（`loca.locations - 1` 或 CFF `CharStrings`），不得用 `getGlyphOrder()` 自证 | `sfnt.measured_glyph_count` |
| **K26** | **`report` 聚合只有一条路径**：`report.evaluate` → `aggregate` → `merge_summaries`；`MODULE_ORDER` 是承重表；键冲突产 `SUMMARY_KEY_COLLISION`（`error`），不静默覆盖 | `report.py`，`tests/test_report.py` |
| **K27** | **脱敏门的扫描面 = "仓库内容"，不是"本地环境"**：`.gitignore` 里每一条本地产物/环境目录都必须在 `SKIP_DIRS`（或后缀规则 `SKIP_SUFFIXES`）里有对应项；漏收 = 假红（不是"判据太严"） | `tools/check_desensitized.py` 顶部 `SKIP_DIRS` / `SKIP_SUFFIXES` |
| **K28** | **CI 步骤顺序**：需要 fontTools、或需要 fixture 产物的步骤（`gen_fixtures.py` / `fetch_fonts.py` / `verify_gates.py` / `check_release.py`）必须排在 `pip install` **与**"生成 fixture"之后 | `.github/workflows/ci.yml`；`tests/test_ci_workflow.py` 三条顺序断言 |

## 五、本机环境坑（只写实测过的）

**M5 及之前已记的坑**（见 `plan/HANDOFF-M5.md` §五）依旧有效，其中与发布直接相关的：
`ulCodePageRange1/2` 只在 `OS/2.version >= 1` 存在；`OS2_UNICODE_RANGES[57]` 是代理区；
`pyftsubset` 默认 `glyph_names=False`；`FontBuilder`/`TTFont.save` 默认写时钟；
`os.path.relpath` 跨盘符抛 `ValueError`；pip 走系统代理会失败（用 `NO_PROXY="*"` + 镜像）；
CI 里一律 `python` 不用 `py`；Git Bash 会把 `/xxx` 改写成 `D:/program/Git/xxx`；
`git ls-files` 会静默向上解析到父仓库。

**M6 新增（全部是实测）**：

- **`py` 是本机启动器，CI 里必须 `python`** —— 与上一条同源，这次在真实 CI 上验证过四格。
- **git 的 HTTPS 通道会整个连不上，而 `gh` 的 API 通道照常可用**：本次发布中途
  `git push` 报 `Failed to connect to github.com port 443`（直连与 17xxx 代理都试过），
  但 `gh api` / `gh release` 一直好使。**处置 = 按"HTTPS 直连 → 本地代理 → 裸 SSH"顺序探测**，
  最终走**一次性 SSH URL**（`git push git@github.com:<owner>/<repo>.git <ref>`，**不改全局配置**）。
  ⇒ **发布门的远端判据一律走 `gh api`，不走 `git ls-remote`**（否则会把"网络抖动"报成"发布事实不对"）。
- **GitHub 的 `events` / `activity` API 对新仓库返回空/滞后**（实测：只回 1 条 `ReleaseEvent`，
  0 条 `PushEvent`）→ **不能**用它当"推送数"的独立源。`git rev-list --count HEAD` 更不行（那是提交数）。
  可用的口径 = `repos/{o}/{r}/branches` + `repos/{o}/{r}/tags`（**tags 已剥开注解 tag，给的就是提交 sha**）
  + `gh run list --commit <sha>`。
- **`gh api --paginate --slurp` 会把每页再包一层数组**（单页也得到 `[[...]]`）→ 解析时要拍平。
- **Windows 的 venv `Scripts/Activate.ps1` 里有本机路径**（文档示例 `C:\Users\<user>\Common\.venv`）：
  仓库根一旦存在 `.venv-readme/`，脱敏门就会命中 —— 见到这种红先问"它是不是 gitignore 的本地环境"。
- **Python 3.8 的 `venv` 自带 pip 20.2.3**：不先 `--upgrade pip` 会报
  `editable mode currently requires a setup.py based build`（PEP 660 需要 pip ≥ 21.3）。
- **`py -m build --no-isolation`** 可用（3.8 通道有 `build` 1.2.2 + `wheel` 0.45.1 + setuptools 75.3.4）；
  3.12 通道没有 `build`/`wheel`/`setuptools` → 打包用 3.8 通道。
- **CI 上 6 个 OFL 真实字体用例是 SKIP**（`data/fonts/` 未下载）：`-rs` 显示的跳过原因是
  "data/fonts 未下载（离线环境）"。**不要把"278/280 passed"读成"全部验过"**。
- **留档里的数字必须当场量，记忆不是证据**：发布留档初稿把产物字节数写成凭记忆的
  `100,072 / 47,979`，真实值是 `101,219 / 47,823`（sha256 一直是对的，所以只有"当场 `getsize`
  回取对账"能抓出来）。⇒ 写"字节数 / run id / sha256"前，**先跑一次命令把回显贴进去**。

## 六、DoD 逐项 checklist（M6）

- [x] `py tools/check_sprint_layout.py` / `check_desensitized.py` 全绿
- [x] `py tools/verify_gates.py` 全部符合预期（**24 项、0 SKIP**；L4/L9 靶子已按 §二.4 处理）
- [x] `py tools/gen_fixtures.py --check` 位级一致（22 个文件）
- [x] `py tools/smoke_cli.py` 11 条 0 失败
- [x] 双解释器测试全绿（3.8 全局 / 3.12 venv，**280 项**；各 6 项 OFL 用例 SKIP，如实标注）
- [x] `tools/check_release.py` 落位并从 `PENDING_TOOLS` 删除（`PENDING_TOOLS` 现为 `{}`）
- [x] `LICENSE`（MIT）与 `pyproject.toml` license 字段一致
- [x] 版本三处一致（`__init__` / `pyproject.toml` / README 状态行 = `0.1.0`）
- [x] `docs/report-sample.json` 落盘（用现行实现现跑）
- [x] 干净环境 `pip install -e .` 后五子命令可用（含 `report --help`）；wheel 单独安装亦可用
- [x] git tag `v0.1.0` + GitHub Release 附产物（含 sha256）；CI 四格全绿
- [x] `plan/RELEASE-M6.md` 两栏 + 覆盖对账小节（11 行三态）
- [x] M6 翻 ✅ 四处（`plan/00` 里程碑表 + 承诺-证据台账 / `plan/05` 状态表 / `README.md` 状态表）

## 七、关键命令速查

```bash
# 门（每棒第一件事）
py tools/check_sprint_layout.py
py tools/check_desensitized.py
py tools/verify_gates.py            # 三道门 24 组；收尾必须重跑
py tools/check_release.py --pre-tag # tag 前（零网络，只落仓库内文件）
py tools/check_release.py           # tag 后离线（+本地 tag + dist/）
py tools/check_release.py --online  # 唯一联网档（+GitHub 远端事实）

# 数据层
py tools/gen_fixtures.py            # 全量生成 F1–F6（必须先跑，门要用产物）
py tools/gen_fixtures.py --check    # 位级一致（22 个文件）
py tools/fetch_fonts.py --check     # 离线校验（不联网；缺文件报 MISSING，rc=1）

# 报告样例重新生成（**改版本号后必须重跑**）
PYTHONPATH=src py -X utf8 -m subsetaudit report \
    --source data/fixtures/codepage-mismatch/out/source.ttf \
    --subset data/fixtures/codepage-mismatch/out/subset.ttf --text "汉字" \
    --out docs/report-sample.json

# 测试（双解释器）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src py -X utf8 -m pytest -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHONUTF8=1 ./_scratch/v312/Scripts/python.exe -m pytest -q

# 离线冒烟
py tools/smoke_cli.py

# 打包（3.8 通道；产物不入仓）
py -m build --no-isolation

# 发布（远端只走 gh api / 一次性 SSH URL；git https 可能连不上）
git push git@github.com:yuluo554/subsetaudit.git main
git tag -a v0.1.0 -m "…" && git push git@github.com:yuluo554/subsetaudit.git v0.1.0
gh release create v0.1.0 dist/*.tar.gz dist/*.whl --title "…" --notes-file <notes.md>
```