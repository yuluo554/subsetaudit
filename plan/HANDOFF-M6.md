# HANDOFF-M6 · 发布（交接单）

> 上一棒：M5（元数据与报告：`metadata` 五组判定 + `report` 单一路径聚合 + §六.9 口径 + 82 项新测试），状态 ✅。
> 下一棒：**M6 发布**（GitHub 公开仓库 v0.1.0：tag + Release 附产物 + `plan/RELEASE-M6.md` 三件套）。
> **第一动作（硬约束③）**：先跑 `py tools/check_sprint_layout.py`，红了先修布局再动手。

## 一、当前进度与证据

| 项 | 状态 | 证据（命令 + 结果） |
|---|---|---|
| 方法论装订 + 计划套件 | ✅ | `py tools/check_sprint_layout.py` → 9 PASS / 0 FAIL |
| 布局门 / 脱敏门 / 变异门 | ✅ | `py tools/verify_gates.py` → **16 项全符合预期、0 SKIP**；脱敏门扫 73 个文本文件 0 命中 |
| 可运行骨架 + 退出码契约 | ✅ | 五子命令 exit 0；非字体文件 exit 2；`py tools/smoke_cli.py` **11 条 0 失败** |
| M1 数据先行 | ✅ | `gen_fixtures.py --check` → 22 个文件位级一致；`fetch_fonts.py --check` 离线 3 个 OK |
| M2 许可闸门 | ✅ | F1/F2/F3 golden 逐项；五元结论 + 六条违规码；560 face 真实池复跑 0 误报 |
| M3 覆盖差集 | ✅ | §六.2–§六.4；F4 golden 三方对齐；381 指纹 |
| M4 布局保真 | ✅ | §六.5.1–5.6；Type 7/9 解包；三条 finding；37 项测试 |
| **M5 元数据口径** | ✅ | `data/README.md` 新开 **§六.9（9.1–9.7）**：name 存活七 ID + 三分类 / 码页只判 bit0 / `ulUnicodeRange` **不对称判定**（只判过度 + 全零反例守护 + bit57 行为型位）/ `maxp` 独立量 / 首末码位单向判 / 四条失败路径 / report 单一路径 |
| **M5 `metadata` 实现** | ✅ | `evaluate(subset, source_path=None) -> (findings, skips, summary)`；finding 码**十条**（7 条 name + 码页 + unicode range + maxp + char index 共 11 个码名，`CHAR_INDEX_MISMATCH` 复用三处 key）；`summary["metadata"]` 不占 `conclusions`（K15） |
| **M5 F5 golden** | ✅ | 缺 13/14 → `default_stripped`（warn 两条）；缺 7/11/16/17 → `author_absent`（**0 条 finding**）；无 `--source` → `unclassified`（0 条） |
| **M5 F6 golden** | ✅ | `CODEPAGE_CLAIMS_LATIN1_WITHOUT_COVERAGE`（error）；`ulUnicodeRange1 = 0` **不报**（bit59 正确置位）；`maxp` 相等不报；首末码位恰好覆盖不报 |
| **M5 `report` 单一路径** | ✅ | `report.evaluate(source, subset, required)` 是**唯一**聚合点；`cli._run_report` 只做参数翻译（有测试钉住两者逐字节一致）；键冲突 → `SUMMARY_KEY_COLLISION`（error）；`summary.modules` 列实际跑过的模块 |
| **M5 测试** | ✅ | `tests/test_metadata.py` **54 项** + `tests/test_report.py` **28 项**；全量 **278 项**，3.8 与 3.12 **两通道全绿** |
| **M5 实测回填** | ✅ | `data/README.md` §四.1 **#15**（559 face 误报率校准）与 **#16**（Noto SC 只对 `汉字` 子集的同构复现） |
| M6 发布 | ⬜ | 未开始 |

## 二、当前事实·状态不变量（下一棒动手前必须知道，否则一定会踩）

1. **`metadata` / `report` 都不再是骨架**。`tests/test_cli.py::test_skeleton_modules_do_not_fabricate_findings`
   的断言面已清空为**空表**，并补了"包内不得再有任何模块走骨架出口"的反向扫描。
   → **M6 不要**为了"补骨架"去动 `_skeleton.py`；它只剩 `validate_inputs` 在用（那是真实现）。

2. **`data/README.md` §六.9 已被 M5 占满（9.1–9.7）**。M6 若要写数值口径，
   **新开到 §六.10 之后** —— 不要插进 §六.9 中间：`tests/test_metadata.py::test_spec_ref_matches_data_readme_section`
   逐字断言 9.1–9.7 七条小节标题存在，`tests/test_report.py` 另断言 9.7 的三个关键词。

3. **`metadata` 的判定是"不对称"的，这是承重设计，M6 不得"补齐"**：
   - `ulUnicodeRange` 只判**过度**声明；**欠声明不判**（实测欠声明率 91–254/559）；
   - 码页**只判 bit0**；其余位置位只进 `summary.metadata.codepage.detail`（`judged: false`）；
   - 首末码位只判"没覆盖住"方向，**留白不判**；
   - name 缺 13/14 只有拿到 `--source` 才分类，**无源一律 `unclassified` 且 0 条 finding**。
   任何一条被"改严"都会打挂 `tests/test_metadata.py` 的反例守护（F5 的 7/11/16/17、F6 的 `ur1:zero`、
   合成样本的留白/欠声明/非 bit0 码页）。

4. **`bit57`（`Non-Plane 0 *`）是行为型位**：`OS2_UNICODE_RANGES[57]` 写作 `U+D800–U+DFFF`（代理区），
   判定式是"存在 `> U+FFFF` 码位"。按区间比会把 26 个合法字体误判（§四.1 #15）。
   `metadata.is_behavioral_bit()` 是识别入口，有测试钉住（`test_behavioral_bit57_uses_non_bmp_rule...`）。

5. **`report` 聚合只有一条路径**：`report.evaluate` → `report.aggregate` → `report.merge_summaries`。
   `tests/test_report.py::test_there_is_exactly_one_aggregation_path` 会扫描 `_run_report` 的函数体，
   出现 `summary.update(` / 直接调某模块 `evaluate` 都算红。**M6 不要再加"顺便聚合一下"的代码**。

6. **`MODULE_ORDER` 是承重的**（不是注释）：`report.aggregate` 按它遍历并决定跑到哪些模块。
   `tests/test_report.py` 的两条变异测试会在改这张表时立刻反映到 `summary.modules`。

7. **状态副本 = 3 处 + 1 处台账**：`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态表，
   外加 `plan/00` 的承诺-证据台账。**翻状态必须四处一起翻**。

8. **变异靶子现在打在 M6 上**：`tools/verify_gates.py` 的 L4 / L9 已从 M5 翻新到 **M6**
   （M5 已 ✅ → `_mark_done(5)` 会 SKIP；靶子必须打"当前是 ⬜ 的那个"）。
   ⚠️ M6 是发布里程碑：`_mark_done(6)` 会让 **LAYOUT.RELEASE 也红**，而 L4/L9 只认**自己那一条**
   （`failed_ids` 逐条比对），所以不影响判定；但**M6 收尾后 L4/L9 的靶子会整体消失**
   （没有下一个 ⬜ 里程碑了）→ 届时必须改成"不依赖下一个里程碑"的靶子，或**显式 SKIP 并在
   HANDOFF 里逐条说明**（`verify_gates.py` 已支持 SKIP 可见 + 计数）。**不要硬凑。**

9. **`tools/check_sprint_layout.py` 的 `PENDING_TOOLS`** 只剩 `tools/check_release.py: 6`。
   M6 落位该脚本后**必须从 `PENDING_TOOLS` 删除**，否则 DOC_TOOLS 变红（K10）。
   反过来说：**未落位的脚本连"举例"都不许写进文档**。

10. **`expect.json` 的 `fonttools_version` 是铸造版本常量**（`GOLDEN_FONTOOLS_VERSION = "4.57.0"`），
    不是运行时版本（K12）。M5 没有新增 fixture，F5/F6 的 `expect.json` 只**增量**加了
    `required_name_ids` / `default_stripped_name_ids` / `author_absent_name_ids` /
    `expected_absent_findings` / `unicode_range_declared_bits` —— 字体二进制**逐字节未变**
    （`--check` 22 个文件位级一致）。

11. **字体二进制永不入仓**：`git ls-files data/fixtures` 只有 `expect.json` / `README.md` /
    `manifest.json`（有测试钉住）。

12. **`sfnt.py` 只读纪律**：M5 新增 `measured_glyph_count` / `name_ids` / `name_language_ids` /
    `cmap_codepoints` / `os2_version`，**仍然没有 `.save(`**（`tests/test_core.py::test_read_only_layer_never_saves` 未动仍绿）。
    注意 `cmap_codepoints` **只并 Unicode 子表** —— 把 `(1,0)` 并进来会让 `no_unicode_cmap` 判不出来
    （M5 实现第一轮踩到，测试 `test_no_unicode_cmap_skips_with_its_own_reason` 抓住）。

13. **`fontTools` 的 `ulCodePageRange1/2` 在 `OS/2.version == 0` 上不存在**（`AttributeError`）：
    造"码页声明"样本必须 `version >= 1`。M5 的 `sfnt.os2_info` 用 `getattr(..., 0)` 兜住了，
    但**测试里**若不显式给 `version=1`，设的值会被静默丢弃（M5 实测踩到）。

14. **`NotoSansSC` / `NotoSans-Bold` 在 `metadata` 下 0 条 finding；`InterVariable` 恰好 4 条 warn**
    （`ur:bit11/62/64/69`，上游真实过度声明）。`tests/test_metadata.py::test_real_ofl_fonts_do_not_trip_the_metadata_rules`
    逐位钉住 —— **不得**为了"全绿"把判据调松。

## 三、下一棒待办（M6 发布，按序）

1. **先跑三条门**：`check_sprint_layout.py` / `check_desensitized.py` / `verify_gates.py`。
2. **写 `tools/check_release.py`**（`--pre-tag` / 离线 / `--online` 三档），落位后**从 `PENDING_TOOLS` 删除**。
3. **`LICENSE`（MIT）+ `pyproject.toml` 的 license 字段**（`plan/00` M6 的 DoD 明写"两者一致"）。
4. **README 收尾**：版本号三处一致（`__init__.__version__` / `pyproject.toml` / README 状态行）；
   `docs/report-sample.json`（`plan/01` §四 第 6 项交付物）—— 用 `metadata` + `report` 现跑一份。
5. **干净环境验证**：`pip install -e .` 后五子命令可用（含 `subsetaudit report --help`）。
6. **tag + Release**：`v0.1.0`，Release 附产物（sdist/wheel 的 sha256）。
7. **`plan/RELEASE-M6.md` 两栏**："一、tag 前事实" / "二、tag 后追加事实" + "覆盖对账"小节
   （三态：实现 / 不适用 / 待首推，至少 3 行）—— 布局门的 `LAYOUT.RELEASE` 逐条断言这三件事。
8. **收尾**：M6 翻 ✅（四处）+ 处理 L4/L9 靶子消失（见 §二.8）+ 更新 HANDOFF 体系 + commit。

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
| K19 | **`data/README.md` §六.5.1–§六.5.6 是 `layout-survival` 唯一口径**；`SPEC_REF = "data/README §6.5"` 是逐字副本 | `layout_survival.py`，`tests/test_layout_survival.py` |
| K20 | **Extension lookup 两张表类型号不同：GSUB = 7、GPOS = 9**，**必须都解包** | `sfnt.EXTENSION_LOOKUP_TYPES`，`tests/test_layout_survival.py` |
| K21 | **连字规则的同一性按「输入码位序列」判**，不按字形名、不按 GID 数值 | `layout_survival._ligature_index` |
| K22 | **`LAYOUT_LIGATURE_RENAMED` 是 `warn`、与 `LOST` 互斥（先判 LOST）** | `layout_survival._is_renamed` |
| **K23** | **`data/README.md` §六.9.1–§六.9.7 是 `metadata` / `report` 唯一口径**；`SPEC_REF = "data/README §6.9"` 是逐字副本，测试逐条解析小节标题做对账 | `metadata.py` / `report.py`，`tests/test_metadata.py` / `tests/test_report.py` |
| **K24** | **元数据判定是"不对称"的**：只判可证矛盾（`ulUnicodeRange` 只判过度 / 码页只判 bit0 / 首末码位只判单向 / name 无源不分类） | `metadata._judge`，两组反例守护 |
| **K25** | **`maxp` 的"实际字形数"必须独立于 `maxp`**（`loca.locations - 1` 或 CFF `CharStrings`），不得用 `getGlyphOrder()` 自证 | `sfnt.measured_glyph_count` |
| **K26** | **`report` 聚合只有一条路径**：`report.evaluate` → `aggregate` → `merge_summaries`；`MODULE_ORDER` 是承重表；键冲突产 `SUMMARY_KEY_COLLISION`（error），不静默覆盖 | `report.py`，`tests/test_report.py` |

## 五、本机环境坑（只写实测过的）

- **`ulCodePageRange1/2` 只在 `OS/2.version >= 1` 存在**：v0 上赋值会被静默丢弃、读取直接
  `AttributeError`（M5 实测）。造码页样本必须 `version=1`。
- **`fontTools` 的 `intersectUnicodeRanges` 对 `bit57` 给出的是"代理区"**：`OS2_UNICODE_RANGES[57]`
  = `(('Non-Plane 0 *', (0xD800, 0xDFFF)),)` —— 语义是"含非 BMP 码位"，**不能按区间比**。
- **`OS2_UNICODE_RANGES` 共 123 个块**（4.57.0 与 4.67.0 实测一致）；`bit57` 是唯一的 `*` 位。
- **`build_font(..., mac_only=True)` 的 `(1,0)/format 0` 子表不是 Unicode 子表**：
  `sub.isUnicode()` 为 `False` → 若 `cmap_codepoints` 把它并进来，`no_unicode_cmap` 判不出来。
- **`raw.githubusercontent.com` 会中途重置**（2026-10-21 实测）→ 已知未验证项。
- **fontTools 读 cmap 时会先剔 gid 0**（M3 实测）。
- **`pyftsubset` 默认 `glyph_names=False`** → 产物 post 表降到 3.0，字形名按 GID 合成 `glyph%05d`。
- **`FontBuilder` 默认把 `head.created/modified` 设为当前时钟**；`TTFont.save()` 默认
  `recalcTimestamp=True` 会再改一次。两处都必须钉死。
- **`os.path.relpath` 跨盘符抛 `ValueError`**（pytest 的 `tmp_path` 在 `C:`，仓库在 `D:`）。
- **pip 走系统代理会失败**：一律 `NO_PROXY="*"` + 清华镜像。
- **`py` 是 Windows 启动器，ubuntu CI 上没有** → workflow 里一律 `python`。
- **`py -3.12` 通道默认没有 fontTools**：用 `_scratch/v312`（4.67.0 / pytest 8.4.2 / PyYAML 6.0.3）。
- **`default layout_features` 随版本漂移**：4.57.0 = 67、4.67.0 = 68（差 `palt`）。
- **Git Bash 会把 `/xxx` 参数改写成 `D:/program/Git/xxx`**：测"不存在路径"时用相对路径。
- **capsys 只能消费一次**：一次接住三流。
- **Git Bash 下 `/tmp` 不映射到 Windows 临时目录**：临时产物一律写 `_scratch/`（已 gitignore）。
- 中文输出一律 `py -X utf8`；CI 侧靠 job 级 `PYTHONUTF8=1`。
- **`git ls-files` 会静默向上解析到父仓库**：断言前先比对 toplevel 与本项目根。

## 六、DoD 逐项 checklist（M6）

- [ ] `py tools/check_sprint_layout.py` / `check_desensitized.py` 全绿
- [ ] `py tools/verify_gates.py` 全部符合预期（L4/L9 靶子按 §二.8 处理，SKIP 必须有说明）
- [ ] `py tools/gen_fixtures.py --check` 位级一致（22 个文件）
- [ ] `py tools/smoke_cli.py` 11 条 0 失败
- [ ] 双解释器测试全绿（3.8 全局 / 3.12 venv）
- [ ] `tools/check_release.py` 落位并从 `PENDING_TOOLS` 删除
- [ ] `LICENSE`（MIT）与 `pyproject.toml` license 字段一致
- [ ] 版本三处一致（`__init__` / `pyproject.toml` / README 状态行）
- [ ] `docs/report-sample.json` 落盘（用现行实现现跑）
- [ ] 干净环境 `pip install -e .` 后五子命令可用（含 `report --help`）
- [ ] git tag `v0.1.0` + GitHub Release 附产物（含 sha256）
- [ ] `plan/RELEASE-M6.md` 两栏 + 覆盖对账小节（≥3 行三态）
- [ ] M6 翻 ✅ 四处（`plan/00` / `plan/05` / `README.md` / 承诺-证据台账）

## 七、关键命令速查

```bash
# 门（每棒第一件事）
py tools/check_sprint_layout.py
py tools/check_desensitized.py
py tools/verify_gates.py            # 变异验证；收尾必须重跑，靶子随进度翻新

# 数据层
py tools/gen_fixtures.py            # 全量生成 F1–F6
py tools/gen_fixtures.py --check    # 位级一致
py tools/fetch_fonts.py --check     # 离线校验（不联网）

# 覆盖差集（M3）
PYTHONPATH=src py -X utf8 -m subsetaudit coverage-diff data/fixtures/silent-drop/out/source.ttf \
    --text "汉字abc" --subset data/fixtures/silent-drop/out/subset.ttf

# 布局保真（M4）
PYTHONPATH=src py -X utf8 -m subsetaudit layout-survival <source.ttf> <subset.ttf>

# 元数据（M5）
PYTHONPATH=src py -X utf8 -m subsetaudit metadata <subset.ttf> --source <source.ttf>
PYTHONPATH=src py -X utf8 -m subsetaudit metadata data/fixtures/codepage-mismatch/out/subset.ttf \
    --source data/fixtures/codepage-mismatch/out/source.ttf

# 报告聚合（M5，唯一路径）
PYTHONPATH=src py -X utf8 -m subsetaudit report \
    --source data/fixtures/codepage-mismatch/out/source.ttf \
    --subset data/fixtures/codepage-mismatch/out/subset.ttf --text "汉字" --format markdown

# 测试（双解释器）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src py -X utf8 -m pytest -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHONUTF8=1 ./_scratch/v312/Scripts/python.exe -m pytest -q

# 离线冒烟
py tools/smoke_cli.py
```
