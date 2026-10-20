# HANDOFF-M4 · 布局保真（交接单）

> 上一棒：M3（覆盖差集：三分类 + 闭包 + 分块 + 两条 SKIPPED 路径 + F4 golden + 381 指纹），状态 ✅。
> 下一棒：**M4 布局保真 `layout-survival`**。用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M4.md 继续完成任务`。
> **第一动作（硬约束③）**：先跑 `py tools/check_sprint_layout.py`，红了先修布局再动手。

## 一、当前进度与证据

| 项 | 状态 | 证据（命令 + 结果） |
|---|---|---|
| 方法论装订 + 计划套件 | ✅ | `py tools/check_sprint_layout.py` → 9 PASS / 0 FAIL |
| 布局门 / 脱敏门 / 变异门 | ✅ | `py tools/verify_gates.py` → **16 项全符合预期、0 SKIP**；脱敏门扫 68 个文本文件 0 命中 |
| 可运行骨架 + 退出码契约 | ✅ | 五子命令 exit 0；非字体文件 exit 2；`py tools/smoke_cli.py` 10 条 0 失败 |
| M1 数据先行 | ✅ | `gen_fixtures.py --check` → 22 个文件位级一致；`fetch_fonts.py --check` 离线 3 个 OK |
| M2 许可闸门 | ✅ | F1/F2/F3 golden 逐项；五元结论 + 六条违规码；560 face 真实池复跑 0 误报 |
| **M3 三分类口径** | ✅ | `data/README.md` §六.2：判定式 + 级别（`MISSING_IN_SOURCE` 默认 `warn`、`--strict-source` → `error`；`LOST_IN_SUBSET` 恒 `error`）+ 每码位一条 + `spec_ref = data/README §6.2` |
| **M3 闭包口径** | ✅ | §六.2.1：范围（只对 `R0` 单码位）/ 方向（NFD+NFC 双向）/ 深度（单层）/ `added = C \ R0` / **只计数不产 finding** / 三分类仍只用 `R0` |
| **M3 cmap 失败路径** | ✅ | §六.3：`no_cmap_table` 与 `no_unicode_cmap` **两条不合并**；任一侧命中 → `summary` 为空、退出码 0、`detail` 带 `source:`/`subset:` |
| **M3 分区口径** | ✅ | §六.4 改为**互斥分区 + 显式优先级**（ExtA 先于 BMP）—— 修掉"ExtA 恒为 0"的实现缺陷 |
| **M3 `coverage_diff.py`** | ✅ | `evaluate(source, required, subset_path=None, strict_source=False) -> (findings, skips, summary)`；编排 `sfnt.select_unicode_cmap` → `cmapset.codepoints` → `classify` → `block_counts` → `closure` → `fallback_hint` |
| **M3 F4 golden** | ✅ | `LOST_IN_SUBSET={U+5B57,U+6C49}`、`MISSING_IN_SOURCE=∅`、`OK={a,b,c}`；三方对齐（golden / `gen_fixtures.oracle_sfnt_cmap_mask` 独立复算 / 被测实现） |
| **M3 381 指纹** | ✅ | 合成 29 字 + 真实 `NotoSansSC-Regular.otf`：`OK=6`、`LOST=23`、`MISSING=0`、全 `error`；回填 `data/README.md` §5.2 |
| **M3 测试** | ✅ | `tests/test_coverage_diff.py` **31 项**（含 6 组进程内变异）；全量 **156 项**，3.8（fontTools 4.57.0/pytest 7.4.4）与 3.12（4.67.0/pytest 8.4.2）**两通道全绿** |
| M4 `layout-survival` | ⬜ | 未开始：仍返回 `SKIPPED(reason=module_not_implemented_in_m0)` |

## 二、当前事实·状态不变量（下一棒动手前必须知道，否则一定会踩）

1. **`layout_survival.py` / `metadata.py` 里仍不能出现 `finding(`**，有一条测试钉住
   （`tests/test_cli.py::test_skeleton_modules_do_not_fabricate_findings`，M2 移除了 `license_gate`、
   M3 移除了 `coverage_diff`）。**写 M4 判定前先删该测试里的 `layout_survival` 那一项**，
   再补一条 `test_layout_survival_is_no_longer_a_skeleton` 反向断言（照 M2/M3 的写法）。
   同时 `tests/test_cli.py::test_all_five_subcommands_exit_zero` 里的 `still_skeleton` 列表要删掉
   `layout-survival` 两行 —— **否则你自己的实现会被"必须输出 SKIPPED"的断言拦住**。

2. **`data/README.md` §六.5 只有一句口径**（布局三元组的定义 + `计数(LookupType 7)` 的算法 +
   `naive` 只作对照）。**M4 若要报"连字规则丢失"或"FeatureVariations 差异"，必须先把判定式补进
   §六.5**（禁第二套口径）。目前缺的口径至少有：
   - 三元组的**完整枚举规则**（`LangSysTag|"dflt"|"all"` 三者的优先级与去重）；
   - "涉及必需字符的连字规则"的**判定式**（规则涉及的字符如何与需求字符集求交）；
   - GSUB 与 GPOS **是否分开成条**（finding 的 `primary_key` 形态）；
   - `naive` 计数怎么算（"朴素遍历"= 不展开 Type 7 时的子表计数？必须写清）。

3. **`sfnt.py` 目前没有任何 GSUB/GPOS 读取函数**。M4 要新增只读访问器（如 `layout_tables(font)`），
   但**不得**在 `sfnt.py` 里出现 `.save(`（有测试钉住 K6），也不得写盘、不得读时钟。

4. **Type 7（Extension）解包是 M4 的核心**。本机实测（2026-10-21，三个 OFL 字体，`TTFont(lazy=True)`）：
   | 字体 | GSUB Lookup 数 / 类型分布 | GPOS Lookup 数 / 类型分布 |
   |---|---|---|
   | `NotoSansSC-Regular.otf` | 15（1×11, 3×1, 4×3） | 10（1×5, 2×2, 4×3） |
   | `NotoSans-Bold.ttf` | 46（1×34, 3×1, 4×7, 6×4） | 9（1×1, 2×1, 8×1, 9×6） |
   | `InterVariable.ttf` | 90（1×55, 3×1, 4×13, 5×2, 6×19） | 10（1×1, 2×2, 4×5, 6×1, 9×1） |
   **三个 OFL 字体都没有 LookupType 7**（Arial 的 92 个 Type 7 是商用字体，**不可入库、不可复现**）。
   → M4 的 "784 vs 0" 对照**必须靠程序合成一个带 Type 7 的极小字体**，或**如实标注为
   "本机只读观察，仓库内以合成字体同构复现"**。这条与 `plan/05` §已知未验证项 #3 同一纪律。

5. **`cmapset.fallback_hint` 只在 `coverage-diff` 用**。M4 不要复用它（语义不同）。

6. **`summary["conclusions"]` 的键已被 `license-gate` 占用**（形状 `{key: {value, spec_ref}}`，
   `canonical._render_conclusions` 会按布尔表渲染）。M4 的 summary 用别的键
   （建议 `summary["layout"] = {...}`），**不要**占 `conclusions`。

7. **`evaluate` 的返回形状必须是 `(findings, skips, summary)`**（`cli._run_layout_survival` 已按此调用，
   两个位置参数 `source` / `subset` 都已由 argparse 保证必填）。

8. **状态副本 = 3 处 + 1 处台账**：`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态表，
   外加 `plan/00` 的承诺-证据台账。**翻状态必须四处一起翻**。

9. **变异靶子现在打在 M4 上**：`tools/verify_gates.py` 的 L4 / L9 用 `_mark_done(4)`，
   L6/L8/L10/L12 用 `_mark_done(6)`。**M4 翻 ✅ 之后 L4/L9 会 SKIP** → 收尾时改打 M5。

10. **`expect.json` 的 `fonttools_version` 是铸造版本常量**（`GOLDEN_FONTOOLS_VERSION = "4.57.0"`），
    不是运行时版本（K12）。M4 若新增 fixture，沿用。

11. **字体二进制永不入仓**：`git ls-files data/fixtures` 只有 `expect.json` / `README.md` /
    `manifest.json`（有测试钉住）。新 fixture 的产物同样落 `out/`（gitignore）。

## 三、下一棒待办（M4 布局保真，按序）

1. **先补口径**：把 §六.5 写实（见 §二.2 的四条缺口）。补完再动手，禁第二套口径。
2. **先探明真实字体**：用 `TTFont` 读三个 OFL 字体的 GSUB/GPOS 结构，确认
   `ScriptList` / `FeatureList` / `LookupList` / `FeatureVariations` 的可用 API 与
   "Type 7 缺失"这一事实（本文件 §二.4 已给首轮实测，可复核）。
3. 实现 `layout_survival.evaluate(source_path, subset_path) -> (findings, skips, summary)`：
   枚举三元组 → **解包 Type 7** → 比对源/产物 → 连字规则按需求字符集过滤 → 计数（`raw` / `kept` / `naive`）。
4. 失败路径：两侧均无 GSUB/GPOS → `SKIPPED(reason=no_layout_tables)`；只有一侧有 → 全量丢失去重报。
5. 合成一个带 **Type 7 ExtSubTable** 的极小字体（`gen_fixtures.py` 加 F7 或测试内合成）：
   让"朴素遍历 0 条 / 解包后 N 条"的对照在**仓库内可复现**。若选择测试内合成，需在
   `data/README.md` §四.1 登记这条实测（含"商用 Arial 的 784 是只读观察，不入仓"的说明）。
6. 测试：`tests/test_layout_survival.py`（三元组 / Type 7 解包 / 默认丢弃标签 / 连字改名 /
   `--layout-features=''` 全量丢失 / 双跑逐字节 / **改坏必红**）。
7. 收尾：翻 M4 ✅（四处）+ 修变异靶子（L4/L9 → M5）+ 写 `plan/HANDOFF-M5.md` + commit。

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
| **K16** | **`data/README.md` §六.2–§六.4 是 `coverage-diff` 唯一口径**；代码里 `SPEC_REF = "data/README §6.2"` 是逐字副本，测试解析该表做对账 | `coverage_diff.py`，`tests/test_coverage_diff.py::test_spec_ref_matches_data_readme_section_62` |
| **K17** | **分区是互斥分区且判定有序**：`ExtA → ExtB+ → BMP → other`；ExtA 先于 BMP（否则 ExtA 恒为 0） | `cmapset.block_of`，`tests/test_core.py::test_block_of_exta_wins_over_bmp` |
| **K18** | **闭包只计数、不产 finding、不回流进三分类**（三分类只用 `R0`） | `coverage_diff._closure_summary`，`tests/test_coverage_diff.py::test_mutation_classifying_on_the_closure_is_caught` |

## 五、本机环境坑（只写实测过的）

- **`raw.githubusercontent.com` 会中途重置**（2026-10-21 实测）：单次 `curl` 只拿到 4.5–7.5 MB
  （目标 8,331,336 B）。`tools/fetch_fonts.py --download` 走**单次请求**，不稳时报 `DOWNLOAD_FAILED`
  （校验在写盘前，不会留半截文件）—— **已知未验证项**（`plan/05` §已知未验证项 #6）。
- **fontTools 读 cmap 时会先剔 gid 0**（M3 实测，`_c_m_a_p._make_map` 跳过 `gid == 0`）：
  "`.notdef` 映射不计覆盖"这条口径在真实字体上被上游"顺带"满足；要证明自己那层是承重的，
  必须把原始映射直接喂给实现（M3 的做法，`tests/test_coverage_diff.py` 两层验证）。
- **fontTools format 4/13 的 subtable 构造**：`CmapSubtable.newSubtable(13)`（不是 `newSubtableClass`），
  且写 format 13 时 gid 0 的条目也会被 `_make_map` 剔掉 → 造"gid 0 映射"样本要**裸写字节**。
- **三个 OFL 字体都没有 LookupType 7**（2026-10-21 实测，见 §二.4）→ "784 vs 0" 必须靠合成字体。
- **`FontBuilder` 默认把 `head.created/modified` 设为当前时钟**；`TTFont.save()` 默认
  `recalcTimestamp=True` 会在子集时再改一次。两处都必须钉死。
- **`os.path.relpath` 跨盘符抛 `ValueError`**（实测）：pytest 的 `tmp_path` 在 `C:`，仓库在 `D:`。
- **pip 走系统代理会失败**：一律 `NO_PROXY="*" no_proxy="*"` + 清华镜像。
- **`py` 是 Windows 启动器，ubuntu CI 上没有** → workflow 里一律 `python`；
  `tests/test_ci_workflow.py` 会拦住 `py ` 开头的行。
- **`py -3.12` 通道默认没有 fontTools**：用 `_scratch/v312`（fontTools 4.67.0 / pytest 8.4.2 / PyYAML 6.0.3）。
  **新开 venv 时必须三个都装**，否则"两条通道都绿"是假等价。
- **Git Bash 会把 `/xxx` 参数改写成 `D:/program/Git/xxx`**：测"不存在路径"时用相对路径。
- **capsys 只能消费一次**：一次接住三流（`tests/test_cli.py::Result`）。
- **Git Bash 下 `/tmp` 不映射到 Windows 临时目录**：临时产物一律写 `_scratch/`（已 gitignore）。
- 中文输出一律 `py -X utf8`；CI 侧靠 job 级 `PYTHONUTF8=1`。
- **`git ls-files` 会静默向上解析到父仓库**：断言前先比对 toplevel 与本项目根。

## 六、DoD 逐项 checklist（M4）

- [ ] `data/README.md` §六.5 布局口径写实（三元组枚举规则 / 连字规则判定式 / `naive` 定义 / GSUB-GPOS 是否分条）
- [ ] `layout_survival.evaluate` 返回 `(findings, skips, summary)`，枚举三元组并**解包 LookupType 7**
- [ ] Type 7 对照在**仓库内可复现**（合成字体；商用 Arial 的 784 只作只读观察登记）
- [ ] `raw` / `kept` / `naive` 三个计数分开报；`naive` 只作对照
- [ ] 默认丢弃标签（`ss01`–`ss08`、`case`、`tnum`、`zero`、`aalt`）在产物上被列出
- [ ] `liga` 存活但目标字形改名（`uniFB01 → glyph00003`）被认出（按 GID/规则比对）
- [ ] `--layout-features=''` 产物上三元组全量丢失被复现
- [ ] 两侧均无 GSUB/GPOS → `SKIPPED(reason=no_layout_tables)`；只有一侧有 → 全量丢失去重报
- [ ] 同输入双跑 JSON 逐字节一致；报告不含时间戳/绝对路径
- [ ] `tests/test_layout_survival.py` 存在且全绿；**改坏实现至少一层测试必红**
- [ ] `tests/test_cli.py` 的骨架列表已删 `layout_survival` 并补反向断言
- [ ] 双解释器测试全绿（3.8 全局 / 3.12 venv）
- [ ] `py tools/check_sprint_layout.py` / `check_desensitized.py` 全绿
- [ ] `py tools/verify_gates.py` 16 项全符合预期、0 SKIP（靶子已翻新到 M5）
- [ ] `py tools/gen_fixtures.py --check` 位级一致
- [ ] `plan/HANDOFF-M5.md` 已落盘（七节）

## 七、关键命令速查

```bash
# 门（每棒第一件事）
py tools/check_sprint_layout.py
py tools/check_desensitized.py
py tools/verify_gates.py            # 变异验证；收尾必须重跑，靶子随进度翻新

# 数据层
py tools/gen_fixtures.py            # 全量生成 F1–F6
py tools/gen_fixtures.py --check    # 位级一致
py tools/gen_fixtures.py --only F4
py tools/fetch_fonts.py --check     # 离线校验（不联网）
py tools/fetch_fonts.py --list

# 覆盖差集（M3 起，可直接对 fixture / OFL 字体跑）
PYTHONPATH=src py -X utf8 -m subsetaudit coverage-diff data/fixtures/silent-drop/out/source.ttf \
    --text "汉字abc" --subset data/fixtures/silent-drop/out/subset.ttf
PYTHONPATH=src py -X utf8 -m subsetaudit coverage-diff data/fonts/NotoSansSC-Regular.otf \
    --corpus _scratch/corpus.txt --subset _scratch/wordlist-subset.otf --strict-source

# 布局保真（M4 起）
PYTHONPATH=src py -X utf8 -m subsetaudit layout-survival <source.ttf> <subset.ttf>

# 测试（双解释器）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src py -X utf8 -m pytest -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHONUTF8=1 ./_scratch/v312/Scripts/python.exe -m pytest -q

# 离线冒烟
py tools/smoke_cli.py
```
