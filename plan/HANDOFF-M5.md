# HANDOFF-M5 · 元数据与报告（交接单）

> 上一棒：M4（布局保真：三元组 + Type 7/9 解包 + 连字规则差分 + 三条 finding + 两条 SKIPPED + 34 项测试），状态 ✅。
> 下一棒：**M5 元数据与报告 `metadata` + `report`**。用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M5.md 继续完成任务`。
> **第一动作（硬约束③）**：先跑 `py tools/check_sprint_layout.py`，红了先修布局再动手。

## 一、当前进度与证据

| 项 | 状态 | 证据（命令 + 结果） |
|---|---|---|
| 方法论装订 + 计划套件 | ✅ | `py tools/check_sprint_layout.py` → 9 PASS / 0 FAIL |
| 布局门 / 脱敏门 / 变异门 | ✅ | `py tools/verify_gates.py` → **16 项全符合预期、0 SKIP**；脱敏门扫 69 个文本文件 0 命中 |
| 可运行骨架 + 退出码契约 | ✅ | 五子命令 exit 0；非字体文件 exit 2；`py tools/smoke_cli.py` **11 条 0 失败** |
| M1 数据先行 | ✅ | `gen_fixtures.py --check` → 22 个文件位级一致；`fetch_fonts.py --check` 离线 3 个 OK |
| M2 许可闸门 | ✅ | F1/F2/F3 golden 逐项；五元结论 + 六条违规码；560 face 真实池复跑 0 误报 |
| M3 覆盖差集 | ✅ | §六.2–§六.4；F4 golden 三方对齐；381 指纹；`tests/test_coverage_diff.py` **31 项** |
| **M4 §六.5 口径写实** | ✅ | `data/README.md` §六.5 扩为 **5.1–5.6**：三元组枚举（GSUB/GPOS 分开成条、`all` 是附加聚合条、四元组去重）/ 子表与规则计数（`raw` vs `naive`）/ 三条判定式 / 连字规则按**输入码位序列** / 两条失败路径 / `primary_key` 形态 |
| **M4 只读访问器** | ✅ | `sfnt.layout_tables(font)` + `sfnt.iter_lookup_subtables(lookup, tag)`；`LAYOUT_TAGS = ("GSUB","GPOS")`；`EXTENSION_LOOKUP_TYPES = {"GSUB": 7, "GPOS": 9}`；**`sfnt.py` 仍无 `.save(`**（K6 测试未动仍绿） |
| **M4 Type 7/9 解包** | ✅ | 合成样本：GSUB `extension_lookups=2` → `subtables_naive=1 / raw=3`、`ligature_rules_naive=0 / raw=1`；GPOS Type 9 → `naive=0 / raw=1`、解包后 `subtable_types={2:1}` |
| **M4 三条 finding** | ✅ | `LAYOUT_FEATURE_LOST`（error，四元组差集）/ `LAYOUT_LIGATURE_LOST`（error）/ `LAYOUT_LIGATURE_RENAMED`（warn）；**只此三码**，测试逐字钉住 |
| **M4 改名判定** | ✅ | `_name_state`：`placeholder ⇔ 名字 == "glyph%05d" % gid`；`named → placeholder` 或两侧 named 但不同 → RENAMED；两侧都 placeholder **不算** |
| **M4 两条 SKIPPED** | ✅ | 两侧都无 → `no_layout_tables` + `summary == {}` + rc 0；只有一侧 → `layout_tables_missing_on_one_side` 且**照常判定**（`detail` 带 `source:`/`subset:`） |
| **M4 测试** | ✅ | `tests/test_layout_survival.py` **37 项**（三方对齐 / 三元组与去重 / 默认丢弃 / 全量丢失 / 改名与丢失互斥 / 两条 SKIPPED / rc 0 与 1 / 双跑 / 口径对账 / **5 组变异** / 真实 OFL 回归 / 反向骨架断言）；全量 **194 项**，3.8 与 3.12 **两通道全绿** |
| **M4 实测回填** | ✅ | `data/README.md` §四.1 **#12–#14**（OFL 无 Extension / 商用 Arial 784 只读观察 / 合成样本同构复现）、§七 **#12–#13**（`layout_features` 67 vs 68；GPOS Extension 是 **Type 9** 不是 7） |
| M5 `metadata` + `report` | ⬜ | 未开始：仍返回 `SKIPPED(reason=module_not_implemented_in_m0)` |

## 二、当前事实·状态不变量（下一棒动手前必须知道，否则一定会踩）

1. **`metadata.py` 里仍不能出现 `finding(`**，有一条测试钉住
   （`tests/test_cli.py::test_skeleton_modules_do_not_fabricate_findings`，M2 移除了 `license_gate`、
   M3 移除了 `coverage_diff`、M4 移除了 `layout_survival`，现在只剩 `metadata` 一项）。
   **写 M5 判定前先改该测试**（它当前 `for name in ("metadata",)`，翻 ✅ 后这一项要删掉，
   并补 `test_metadata_is_no_longer_a_skeleton` 反向断言，照 M2/M3/M4 的写法）。
   同时 `tests/test_cli.py::test_all_five_subcommands_exit_zero` 里的 `still_skeleton` 列表里
   **两条 `metadata` 行要删掉** —— 否则你自己的实现会被"必须输出 SKIPPED"的断言拦住。
   ⚠️ 注意：`report` 子命令的骨架在 `report.evaluate`（`_run_report` 当前**不走**它，而是自己聚合），
   `test_skeleton_modules_do_not_fabricate_findings` **没有**把 `report` 列进断言面 —— 这是既成事实，
   M5 若要动 `report.evaluate`，得自己补一条判据。

2. **`data/README.md` §六.5 已被 M4 占满（5.1–5.6）**。M5 的元数据口径**必须新开 §六.6 之后的位置**
   （当前 §六.6 是退出码、§六.7 是 fixture 名表、§六.8 是确定性）。**建议新开一个 §六.9「元数据与位域一致性」**
   或把现有 §六.6 起的编号整体后移 —— **不要**插在 §六.5 中间，`tests/test_layout_survival.py::test_spec_ref_matches_data_readme_section`
   断言 §六.5 的六条小节标题逐字存在。

3. **M5 的口径缺口（必须先补，禁第二套口径）**：
   - `name` 存活判据：**哪些 nameID 必查**（`plan/01` §三 M4 列了 0/7/11/13/14/16/17）、
     "默认剥离" vs "原作者没写"的分类判定式（需要 `--source` 差分）；
   - `ulCodePageRange ↔ cmap` 矛盾的**精确判定式**：哪些码页位对应哪些码位范围（**不能只比"是否为 0"**）；
     已实测的锚点：F6 产物 `ulCodePageRange1 = 0x1`（Latin-1 回退）而 cmap 无任何 `≤ U+00FF` 码位；
   - `ulUnicodeRange` **不得**因 `ulUnicodeRange1 = 0` 就报矛盾（**实测是正确重算**，`ulUnicodeRange2`
     bit59 已置位）—— 这条是 M1 更正的假阳性，必须写进口径；
   - `maxp.numGlyphs` vs 实际字形数、`usFirstCharIndex`/`usLastCharIndex` ↔ cmap 范围的判定式；
   - `report` 的聚合口径：多个模块的 `summary` 如何合并（`cli._run_report` 现在用 `summary.update(...)`，
     键冲突时会**静默覆盖** —— 若两个模块都用同名键就是真缺陷）。

4. **`summary["conclusions"]` 的键仍被 `license-gate` 独占**（K15，`canonical._render_conclusions`
   按 `{key: {value, spec_ref}}` 渲染布尔表）。`metadata` 的 summary 用别的键（建议 `summary["metadata"]`），
   **不要**占 `conclusions`。

5. **`evaluate` 的返回形状必须是 `(findings, skips, summary)`**；`metadata` 的签名是
   `evaluate(subset_path, source_path=None)`（`cli._run_metadata` 已按此调用，`--source` 可选）。

6. **`report` 子命令的聚合已在 `cli._run_report` 里实现**，且**已经接入 M4**（`if args.source and args.subset:
   layout_survival.evaluate(...)`）。M5 的 `report` 模块 `build()` 是真实实现（`canonical` 的薄封装）；
   `report.evaluate()` 仍是骨架但**无人调用**。翻 ✅ 时要明确：是把 `_run_report` 的聚合逻辑搬进 `report.evaluate`，
   还是把 `report.evaluate` 删掉/改写 —— **两种都要在 HANDOFF-M6 里写清**，别留"两条聚合路径"。

7. **状态副本 = 3 处 + 1 处台账**：`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态表，
   外加 `plan/00` 的承诺-证据台账。**翻状态必须四处一起翻**。

8. **变异靶子现在打在 M5 上**：`tools/verify_gates.py` 的 L4 / L9 用 `_mark_done(5)`
   （M4 收尾时已从 M4 翻新）；L6/L8/L10/L12 用 `_mark_done(6)`。
   **M5 翻 ✅ 之后 L4/L9 会 SKIP** → 收尾时改打 M6 —— ⚠️ 但 M6 是发布里程碑，
   `_mark_done(6)` 会让 LAYOUT.RELEASE 也红。届时 L4/L9 应改为"**靶子消失 → 显式 SKIP 并在 HANDOFF 里说明**"，
   或换一个不依赖"下一个 ⬜ 里程碑"的靶子（例如把 HANDOFF-M6 删节），**不要**硬凑。

9. **`tools/check_sprint_layout.py` 的 `PENDING_TOOLS`** 只剩 `tools/check_release.py: 6`。
   M5 若在文档里点名新脚本（`tools/*.py`），必须在该里程碑内落位并**从 `PENDING_TOOLS` 删除**，
   否则门会红（K10）—— 反过来说，**未落位的脚本连"举例"都不许写进文档**（M4 收尾时 HANDOFF-M5
   初稿拿一个尚不存在的 `check_report` 脚本作例子，被 DOC_TOOLS 门当场抓红）。

10. **`expect.json` 的 `fonttools_version` 是铸造版本常量**（`GOLDEN_FONTOOLS_VERSION = "4.57.0"`），
    不是运行时版本（K12）。M5 若新增 fixture，沿用。

11. **字体二进制永不入仓**：`git ls-files data/fixtures` 只有 `expect.json` / `README.md` /
    `manifest.json`（有测试钉住）。新 fixture 的产物同样落 `out/`（gitignore）。

12. **`sfnt.py` 只读纪律**：M4 已加 `layout_tables` / `iter_lookup_subtables` 等访问器，
    **仍然没有 `.save(`**（`tests/test_core.py::test_read_only_layer_never_saves` 未动仍绿）。M5 加
    `name`/`OS/2` 访问器时照此纪律。

13. **`layout-survival` 的 `summary.layout.ligature_scope` 恒为 `"all"`**：CLI 没有 `--text`，
    所以连字规则不过滤需求字符集。若 M5 的 `report` 想按 `--text` 收窄连字规则，
    **必须先改 §六.5.4 口径 + CLI 参数面 + 反射对账测试** —— 不要在 report 层偷偷过滤（那就是第二套口径）。

## 三、下一棒待办（M5 元数据与报告，按序）

1. **先补口径**：在 `data/README.md` 新开一节（建议 §六.9「元数据与位域一致性」），写实 §二.3 的五条缺口。
   补完再动手，禁第二套口径。
2. **先探明真实数据**：用 `TTFont` 读 `F5`/`F6` fixture 与 `NotoSansSC-Regular.otf` 的 `name` / `OS/2` / `cmap`，
   复核 `data/README.md` §四.1 #6–#7 与 §5.1 的已有数字，确认 API（`sfnt.name_records` / `sfnt.os2_info` 已就位）。
3. 实现 `metadata.evaluate(subset_path, source_path=None) -> (findings, skips, summary)`：
   - `name` 存活（0/7/11/13/14/16/17）+ "默认剥离" vs "原作者没写"（需 `source_path`）；
   - `ulCodePageRange ↔ cmap` 矛盾（**按位与 cmap 实测集合比对，不得只比"是否为 0"**）；
   - `ulUnicodeRange` 自洽（**`ulUnicodeRange1 = 0` 不是矛盾**，必须能过反例守护）；
   - `maxp.numGlyphs` vs 实际字形数；`usFirstCharIndex/usLastCharIndex` ↔ cmap 范围。
4. 失败路径：无 `OS/2` → `SKIPPED(reason=no_os2_table)`；无 `name` → `SKIPPED(reason=no_name_table)`；
   无 Unicode cmap 而口径需要它 → 复用 §六.3 的两条理由（**但 `detail` 要能区分是 metadata 的调用**）。
5. `report.evaluate`：把 `cli._run_report` 的聚合收进模块 **或** 明确删掉它 —— 二选一，别留两条路径。
6. 测试：`tests/test_metadata.py`（F5/F6 golden / 改名分类 / 码页矛盾 / `ulUnicodeRange1=0` 不误报 /
   `maxp` 相等不报 / 两条 SKIPPED / 双跑 / **改坏必红**）+ `tests/test_report.py`（聚合顺序 / 键冲突检测 /
   Markdown 渲染 / 退出码 0/1/2 三档）。
7. 收尾：翻 M5 ✅（四处）+ 处理变异靶子（见 §二.8）+ 写 `plan/HANDOFF-M6.md` + commit。

## 四、既定口径清单（K 编号，动了会打挂测试）

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
| K9 | 版本三处一致：`__init__.__version__` / `pyproject.toml` / README 状态行 | 两条测试 |
| K10 | 布局门 `PENDING_TOOLS` 登记项**随里程碑翻 ✅ 自清理** | `tools/check_sprint_layout.py` 顶部 |
| K11 | 门的变异验证常驻 `tools/verify_gates.py`，每棒收尾重跑；靶子随进度翻新 | CI step 3 |
| K12 | **golden 的 `fonttools_version` = 铸造版本常量**，不是运行时版本 | `tools/gen_fixtures.py::GOLDEN_FONTOOLS_VERSION` |
| K13 | **fixture 生成禁时钟**：`head.created/modified` 钉 `FIXED_EPOCH`；`TTFont(..., recalcTimestamp=False)` | `tools/gen_fixtures.py::_subset` |
| K14 | `data/README.md` §六.1 的五元判定式与六条违规码是 `license-gate` 唯一口径；`SPEC_REFS` / `CODE_SPEC_REFS` 是逐字副本 | `license_gate.py`，`tests/test_license_gate.py` |
| K15 | **`summary["conclusions"]` 的形状固定为 `{key: {"value": bool, "spec_ref": str}}`**；别的模块不要占用该键 | `canonical._render_conclusions` |
| K16 | **`data/README.md` §六.2–§六.4 是 `coverage-diff` 唯一口径**；`SPEC_REF = "data/README §6.2"` 是逐字副本 | `coverage_diff.py`，`tests/test_coverage_diff.py` |
| K17 | **分区是互斥分区且判定有序**：`ExtA → ExtB+ → BMP → other`；ExtA 先于 BMP | `cmapset.block_of`，`tests/test_core.py` |
| K18 | **闭包只计数、不产 finding、不回流进三分类**（三分类只用 `R0`） | `coverage_diff._closure_summary` |
| **K19** | **`data/README.md` §六.5.1–§六.5.6 是 `layout-survival` 唯一口径**；`SPEC_REF = "data/README §6.5"` 是逐字副本，测试解析该节六条小节标题做对账 | `layout_survival.py`，`tests/test_layout_survival.py::test_spec_ref_matches_data_readme_section` |
| **K20** | **Extension lookup 两张表类型号不同：GSUB = 7、GPOS = 9**，**必须都解包**；`naive` 只数**未包装**的子表（包装本身不计），且只作对照 | `sfnt.EXTENSION_LOOKUP_TYPES` / `iter_lookup_subtables`，`tests/test_layout_survival.py` |
| **K21** | **连字规则的同一性按「输入码位序列」判**，不按字形名、不按 GID 数值（子集后 post 降到 3.0，名字是 `glyph%05d` 占位名） | `layout_survival._ligature_index` / `_name_state` |
| **K22** | **`LAYOUT_LIGATURE_RENAMED` 是 `warn`、与 `LOST` 互斥（先判 LOST）**；两侧都 placeholder 不算改名 | `layout_survival._is_renamed` |

## 五、本机环境坑（只写实测过的）

- **`raw.githubusercontent.com` 会中途重置**（2026-10-21 实测）：单次 `curl` 只拿到 4.5–7.5 MB
  （目标 8,331,336 B）。`tools/fetch_fonts.py --download` 走**单次请求**，不稳时报 `DOWNLOAD_FAILED`
  （校验在写盘前，不会留半截文件）—— **已知未验证项**（`plan/05` §已知未验证项 #6）。
- **fontTools 读 cmap 时会先剔 gid 0**（M3 实测，`_c_m_a_p._make_map` 跳过 `gid == 0`）。
- **fontTools format 4/13 的 subtable 构造**：`CmapSubtable.newSubtable(13)`（不是 `newSubtableClass`），
  且写 format 13 时 gid 0 的条目也会被 `_make_map` 剔掉 → 造"gid 0 映射"样本要**裸写字节**。
- **三个 OFL 字体都没有 Extension lookup**（2026-10-21 实测）：GSUB Type 7 = 0、GPOS Type 9 = 0。
  → "784 vs 0" 对照必须靠**合成字体**（`conftest.build_layout_font(wrap_gsub_ext=...)`）。
- **商用字体 GPOS 的 Extension 是 Type 9**（Arial 134 个 GPOS lookup 全为 Type 9；Calibri 254 个同）。
  只解 GSUB 的 7 会让 GPOS 整段读不到 —— 这是 M4 实现在第一轮踩到的口径缺口（已补进 §七 #13）。
- **`pyftsubset` 默认 `glyph_names=False`** → 产物 post 表降到 **3.0**，字形名全丢；fontTools 读入时
  按 GID **合成** `glyph%05d` 占位名（实测：gid 3 → `glyph00003`）。**名字不是稳定标识**。
- **`FontBuilder` 默认把 `head.created/modified` 设为当前时钟**；`TTFont.save()` 默认
  `recalcTimestamp=True` 会在子集时再改一次。两处都必须钉死。
- **`os.path.relpath` 跨盘符抛 `ValueError`**（实测）：pytest 的 `tmp_path` 在 `C:`，仓库在 `D:`。
- **pip 走系统代理会失败**：一律 `NO_PROXY="*" no_proxy="*"` + 清华镜像。
- **`py` 是 Windows 启动器，ubuntu CI 上没有** → workflow 里一律 `python`。
- **`py -3.12` 通道默认没有 fontTools**：用 `_scratch/v312`（fontTools 4.67.0 / pytest 8.4.2 / PyYAML 6.0.3）。
- **`default layout_features` 随版本漂移**：4.57.0 = **67** 个、4.67.0 = **68** 个（差 `palt`）。
  → M5 若做"默认剥离"分类，**不要把标签数写死进判定**。
- **Git Bash 会把 `/xxx` 参数改写成 `D:/program/Git/xxx`**：测"不存在路径"时用相对路径。
- **capsys 只能消费一次**：一次接住三流（`tests/test_cli.py::Result`）。
- **Git Bash 下 `/tmp` 不映射到 Windows 临时目录**：临时产物一律写 `_scratch/`（已 gitignore）。
- 中文输出一律 `py -X utf8`；CI 侧靠 job 级 `PYTHONUTF8=1`。
- **`git ls-files` 会静默向上解析到父仓库**：断言前先比对 toplevel 与本项目根。

## 六、DoD 逐项 checklist（M5）

- [ ] `data/README.md` 新增元数据口径节（name 存活判据 / 码页↔cmap 判定式 / `ulUnicodeRange` 反例守护 / `maxp` / 首末码位 / report 聚合口径）
- [ ] `metadata.evaluate(subset_path, source_path=None)` 返回 `(findings, skips, summary)`
- [ ] F6：`ulCodePageRange1=0x1` 而 cmap 无 Latin-1 → 报矛盾
- [ ] `ulUnicodeRange1=0` 而 `ulUnicodeRange2` bit59 置位 → **不报**矛盾（F6 上的反例守护）
- [ ] F5：缺 nameID 13/14 分"默认剥离"与"原作者没写"两类（有 `--source` 才能分；无源时**不分**）
- [ ] `maxp.numGlyphs == 实际字形数` → 不报发现
- [ ] 无 `OS/2` / 无 `name` → 各自一条 `SKIPPED`，`summary` 为空、退出码 0
- [ ] `report` 聚合**只有一条路径**（`report.evaluate` 与 `cli._run_report` 不共存两套）
- [ ] 报告双跑 JSON 逐字节一致；不含时间戳/绝对路径
- [ ] 退出码 0/1/2 三档各有 fixture；输入夹非字体文件 → 2 且指明文件
- [ ] `tests/test_metadata.py` / `tests/test_report.py` 存在且全绿；**改坏实现至少一层测试必红**
- [ ] `tests/test_cli.py` 的骨架列表已删 `metadata` 并补反向断言
- [ ] 双解释器测试全绿（3.8 全局 / 3.12 venv）
- [ ] `py tools/check_sprint_layout.py` / `check_desensitized.py` 全绿
- [ ] `py tools/verify_gates.py` 16 项全符合预期、0 SKIP（靶子已按 §二.8 处理）
- [ ] `py tools/gen_fixtures.py --check` 位级一致
- [ ] `plan/HANDOFF-M6.md` 已落盘（七节）

## 七、关键命令速查

```bash
# 门（每棒第一件事）
py tools/check_sprint_layout.py
py tools/check_desensitized.py
py tools/verify_gates.py            # 变异验证；收尾必须重跑，靶子随进度翻新

# 数据层
py tools/gen_fixtures.py            # 全量生成 F1–F6
py tools/gen_fixtures.py --check    # 位级一致
py tools/gen_fixtures.py --only F5
py tools/fetch_fonts.py --check     # 离线校验（不联网）

# 覆盖差集（M3）
PYTHONPATH=src py -X utf8 -m subsetaudit coverage-diff data/fixtures/silent-drop/out/source.ttf \
    --text "汉字abc" --subset data/fixtures/silent-drop/out/subset.ttf

# 布局保真（M4）
PYTHONPATH=src py -X utf8 -m subsetaudit layout-survival <source.ttf> <subset.ttf>
PYTHONPATH=src py -X utf8 -m subsetaudit layout-survival data/fonts/NotoSansSC-Regular.otf \
    _scratch/sub_NotoSansSC-Regular.sub.otf

# 元数据（M5 起）
PYTHONPATH=src py -X utf8 -m subsetaudit metadata <subset.ttf> --source <source.ttf>
PYTHONPATH=src py -X utf8 -m subsetaudit metadata data/fixtures/codepage-mismatch/out/subset.ttf \
    --source data/fixtures/codepage-mismatch/out/source.ttf

# 测试（双解释器）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src py -X utf8 -m pytest -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHONUTF8=1 ./_scratch/v312/Scripts/python.exe -m pytest -q

# 离线冒烟
py tools/smoke_cli.py
```
