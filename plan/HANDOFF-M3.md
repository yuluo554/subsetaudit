# HANDOFF-M3 · 覆盖差集（交接单）

> 上一棒：M2（许可闸门：五元结论口径 + 六条违规码 + F1/F2/F3 golden），状态 ✅。
> 下一棒：**M3 覆盖差集 `coverage-diff`**。用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M3.md 继续完成任务`。
> **第一动作（硬约束③）**：先跑 `py tools/check_sprint_layout.py`，红了先修布局再动手。

## 一、当前进度与证据

| 项 | 状态 | 证据（命令 + 结果） |
|---|---|---|
| 方法论装订 + 计划套件 | ✅ | `py tools/check_sprint_layout.py` → 9 PASS / 0 FAIL |
| 布局门 / 脱敏门 / 变异门 | ✅ | `py tools/verify_gates.py` → **16 项全符合预期、0 SKIP**；脱敏门扫 66 个文本文件 0 命中 |
| 可运行骨架 + 退出码契约 | ✅ | 五子命令 exit 0；非字体文件 exit 2；`py tools/smoke_cli.py` 10 条 0 失败 |
| M1 `data/fonts.lock` + `fetch_fonts.py` | ✅ | 3 个 OFL 字体实测哈希；`--check` 离线：3 个 OK；空目录 → `MISSING` + exit 1（不崩） |
| M1 `gen_fixtures.py`（F1–F6） | ✅ | 全量生成 exit 0，逐项打印字节数 + sha256；生成期自证（独立 oracle）全过 |
| M1 `--check` 位级一致 | ✅ | 22 个文件逐字节一致；改一字节 / 删一产物都变红（两条测试钉住） |
| **M2 五元结论口径** | ✅ | `data/README.md` §六.1.1–§六.1.6：解析顺序、`perm` 表、五元判定式 + `spec_ref` 字面量、六条违规码、完备性可证、保留位版本分级 |
| **M2 `license_gate.py`** | ✅ | 真实判定：`resolve_permission` / `conclusions_for` / `_violations`；`SPEC_REFS` / `CODE_SPEC_REFS` 是 §六.1.3/§六.1.4 的**逐字副本** |
| **M2 F1/F2/F3 golden** | ✅ | `pending_conclusions` 已删除，五元填全；生成期 `_oracle_conclusions()` **独立复算**（不复用被测实现）；`--check` 位级一致 |
| **M2 测试** | ✅ | `tests/test_license_gate.py` **32 项**（golden 逐项 / bit0 两类样本 / bit9 / 保留位分级 / 无 OS/2 / 口径单点对账 / 5 组变异） |
| **M2 真实字体池复跑** | ✅ | 560 face 逐个判定（`mstmc.ttf` → `not_an_sfnt_font`，不猜）：44 个多位并存 **0 条互斥误报**、40 个 Editable；`BIT0_RESERVED` 103 / `RESTRICTED` 4；与 `data/README.md` §五 独立吻合（回填见 §5.1） |
| **M2 双解释器** | ✅ | 3.8（fontTools 4.57.0 / pytest 7.4.4）与 3.12（4.67.0 / pytest 8.4.2）**各 123 项全绿**（3.12 venv 本次补装 PyYAML 6.0.3，`test_ci_workflow.py` 不再 skip） |
| M3 `coverage-diff` | ⬜ | 未开始：仍返回 `SKIPPED(reason=module_not_implemented_in_m0)` |

## 二、当前事实·状态不变量（下一棒动手前必须知道，否则一定会踩）

1. **`coverage_diff.py` / `layout_survival.py` / `metadata.py` 里仍不能出现 `finding(`**，
   有一条测试钉住（`tests/test_cli.py::test_skeleton_modules_do_not_fabricate_findings`，
   M2 已把 `license_gate` 从该列表移除）。**写 M3 判定前先删该测试里的 `coverage_diff` 那一项**
   （或按 M2 的做法：把已实现模块移出列表 + 补一条"不再是骨架"的反向断言）。
2. **`data/README.md` §六.2 / §六.3 / §六.4 已有 M3 需要的全部口径**：覆盖三分类、
   `(3,10) → (0,4) → (3,1) → (0,3)` 编码优先级、glyph0 不计覆盖、BMP/ExtA/ExtB+ 分区计数。
   **§六.5 的闭包（NFC/NFD）口径只有一句"`closure` 返回 `(closed, added)`"** —— M3 若要报
   闭包新增计数，需先把**闭包的字符集范围与判定**补进 §六.5，再实现（禁第二套口径）。
3. **`cmapset.py` 已经实现好了三分类与闭包**：`classify` / `codepoints` / `block_counts` /
   `closure` / `from_text` / `from_corpus_file`。M3 的活主要是**编排 + 失败路径 + golden 逐项**，
   不是重写集合运算。`sfnt.select_unicode_cmap` 已按优先级选表并给 `stats`（含 `chosen` 子表清单）。
4. **`_skeleton.py` 的 `skeleton_result()` 仍是骨架模块的唯一出口**；`coverage_diff.evaluate`
   的返回形状必须是 `(findings, skips, summary)`（`cli._run_coverage_diff` 已按此调用）。
5. **`cli._run_coverage_diff` 已实现 `--corpus` 读失败 → `InputError` → 退出码 2**；
   `--text` / `--corpus` 的互斥由 argparse `required=True` 保证。别在模块里再收一遍。
6. **状态副本 = 3 处 + 1 处台账**：`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态表，
   外加 `plan/00` 的承诺-证据台账。**翻状态必须四处一起翻**。
7. **变异靶子现在打在 M3 上**：`tools/verify_gates.py` 的 L4 / L9 用 `_mark_done(3)`，
   L12 用 `_mark_done(6)`。**M3 翻 ✅ 之后 L4/L9 会 SKIP** → 收尾时按同样思路改打 M4。
   判别 = "这个靶子，在我把该做的事做完之后还存在吗？"
8. **`expect.json` 的 `fonttools_version` 是铸造版本常量**（`GOLDEN_FONTOOLS_VERSION = "4.57.0"`），
   不是运行时版本（K12）。M3 加 golden 时沿用。
9. **`summary["conclusions"]` 会被 `canonical.render_markdown` 渲染成「## 结论」小节**。
   形状固定为 `{key: {"value": bool, "spec_ref": str}}`。M3 若要用 summary 放别的东西，
   **不要用 `conclusions` 这个键**（否则 Markdown 会按布尔表渲染）。
10. **字体二进制永不入仓**：`git ls-files data/fixtures` 只有 `expect.json` / `README.md` /
    `manifest.json`（有测试钉住）。F4 的产物在 `data/fixtures/silent-drop/out/`（gitignore）。

## 三、下一棒待办（M3 覆盖差集，按序）

1. **先补口径**：把 `data/README.md` §六.5 的闭包口径写实（范围、NFC/NFD 方向、`added` 的定义），
   以及 §六.2 里 `MISSING_IN_SOURCE` 的级别随 `--strict-source` 的变化（默认 `error` 已写，补 `--strict-source` 后是什么）。
2. 实现 `coverage_diff.evaluate(source, required, subset_path=None, strict_source=False) -> (findings, skips, summary)`：
   需求集已在 CLI 侧构建（`--text` / `--corpus`）；本模块负责 `sfnt.select_unicode_cmap` →
   `cmapset.classify` → 分块计数 → 闭包 → 回退链建议。
3. 失败路径：无 Unicode cmap → `SKIPPED(reason=no_unicode_cmap)`（**不得**输出"覆盖为空"的 OK 结论）；
   无 cmap 表 → `SKIPPED(reason=no_cmap_table)`（两条理由不得合并）。
4. F4 golden 逐项：`LOST_IN_SUBSET = {U+5B57, U+6C49}`、`MISSING_IN_SOURCE = ∅`；
   `tests/test_coverage_diff.py` 里用**独立复算**（不经被测实现）钉住。
5. pdfcraft#381 字组指纹：`plan/01` §三 M2 验收② 的 29 个汉字，构造"按词表切"的子集，
   复现"高频在、中频缺"。
6. 测试：`tests/test_coverage_diff.py`（golden / glyph0 / 非 Unicode cmap / 闭包新增 / 双跑逐字节 / **改坏必红**）。
7. 收尾：翻 M3 ✅（四处）+ 修变异靶子（L4/L9 → M4）+ 写 `plan/HANDOFF-M4.md` + commit。

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
| **K14** | **M2 起：`data/README.md` §六.1 的五元判定式与六条违规码是唯一口径**；代码里的 `SPEC_REFS` / `CODE_SPEC_REFS` 是该表的逐字副本，测试会解析表做对账 | `license_gate.py`，`tests/test_license_gate.py` |
| **K15** | **`summary["conclusions"]` 的形状固定为 `{key: {"value": bool, "spec_ref": str}}`**（Markdown 按此渲染）；别的模块要用 summary 时不要占用该键 | `canonical._render_conclusions` |

## 五、本机环境坑（只写实测过的）

- **`raw.githubusercontent.com` 会中途重置**（2026-10-21 实测）：单次 `curl` 只拿到 4.5–7.5 MB
  （目标 8,331,336 B）。`tools/fetch_fonts.py --download` 走**单次请求**，不稳时报 `DOWNLOAD_FAILED`
  （校验在写盘前，不会留半截文件）—— 这是**已知未验证项**（`plan/05` §已知未验证项 #6）。
- **`FontBuilder` 默认把 `head.created/modified` 设为当前时钟**；`TTFont.save()` 默认
  `recalcTimestamp=True` 会在子集时再改一次。两处都必须钉死。
- **`os.path.relpath` 跨盘符抛 `ValueError`**（实测）：pytest 的 `tmp_path` 在 `C:`，仓库在 `D:`。
  任何"打印相对路径"的地方都要兜底（`_display_path`）。
- **pip 走系统代理会失败**：一律 `NO_PROXY="*" no_proxy="*"` + 清华镜像。
- **`py` 是 Windows 启动器，ubuntu CI 上没有** → workflow 里一律 `python`；
  `tests/test_ci_workflow.py` 会拦住 `py ` 开头的行。
- **CI 里步骤顺序有依赖**：三个门（布局/脱敏/变异）**只用标准库**，可在 install 前跑；
  `gen_fixtures.py` / `fetch_fonts.py` 需要 fontTools，**必须在 `pip install -e ".[dev]"` 之后**。
- **`py -3.12` 通道默认没有 fontTools**：用 `_scratch/v312`（fontTools 4.67.0 / pytest 8.4.2）。
  **该 venv 也没有 PyYAML**（M2 实测：不装 `test_ci_workflow.py` 整份 skip → 3.12 通道只跑 113 项）。
  已补装 `pyyaml 6.0.3`；**新开 venv 时必须一起装**，否则"两条通道都绿"是假等价。
- **Git Bash 会把 `/xxx` 参数改写成 `D:/program/Git/xxx`**：测"不存在路径"时用相对路径或 `$(pwd)/...`。
- **capsys 只能消费一次**：一次接住三流（`tests/test_cli.py::Result`）。
- **Git Bash 下 `/tmp` 不映射到 Windows 临时目录**（M2 实测）：重定向到 `/tmp/x.json` 后
  Windows 侧的 Python 读不到。临时产物一律写 `_scratch/`（已 gitignore）。
- 中文输出一律 `py -X utf8`；CI 侧靠 job 级 `PYTHONUTF8=1`。
- **`git ls-files` 会静默向上解析到父仓库**：断言前先比对 toplevel 与本项目根，不一致就显式 skip。

## 六、DoD 逐项 checklist（M3）

- [ ] `data/README.md` §六.5 闭包口径写实（范围 / 方向 / `added` 定义），§六.2 补 `--strict-source` 语义
- [ ] `coverage_diff.evaluate` 返回 `(findings, skips, summary)`，编排 `sfnt.select_unicode_cmap` + `cmapset.classify`
- [ ] F4 golden：`LOST_IN_SUBSET={U+5B57,U+6C49}`、`MISSING_IN_SOURCE=∅`、`OK={a,b,c}`，逐项一致
- [ ] pdfcraft#381 29 字字组"按词表切"可复现"高频在、中频缺"指纹
- [ ] 仅 `(1,0)`/format 0 的字体 → `SKIPPED(reason=no_unicode_cmap)`；无 cmap 表 → `no_cmap_table`（两条不合并）
- [ ] glyph0 命中不计入覆盖（`.notdef` 映射样本）
- [ ] 闭包新增字符单列计数
- [ ] 同输入双跑 JSON 逐字节一致
- [ ] `tests/test_coverage_diff.py` 存在且全绿；**改坏实现至少一层测试必红**（变异验证）
- [ ] `tests/test_cli.py::test_skeleton_modules_do_not_fabricate_findings` 已按 M3 调整
- [ ] 双解释器测试全绿（3.8 全局 / 3.12 venv）
- [ ] `py tools/check_sprint_layout.py` / `check_desensitized.py` 全绿
- [ ] `py tools/verify_gates.py` 16 项全符合预期、0 SKIP（靶子已翻新到 M4）
- [ ] `py tools/gen_fixtures.py --check` 位级一致
- [ ] `plan/HANDOFF-M4.md` 已落盘（七节）

## 七、关键命令速查

```bash
# 门（每棒第一件事）
py tools/check_sprint_layout.py
py tools/check_desensitized.py
py tools/verify_gates.py            # 变异验证；收尾必须重跑，靶子随进度翻新

# 数据层（M1 起）
py tools/gen_fixtures.py            # 全量生成 F1–F6
py tools/gen_fixtures.py --check    # 位级一致
py tools/gen_fixtures.py --only F1,F3
py tools/fetch_fonts.py --check     # 离线校验（不联网）
py tools/fetch_fonts.py --list

# 许可闸门（M2 起，可直接对 fixture 跑）
PYTHONPATH=src py -X utf8 -m subsetaudit license-gate data/fixtures/fstype-nosubset/out/fstype-nosubset.ttf
PYTHONPATH=src py -X utf8 -m subsetaudit license-gate data/fixtures/fstype-multibit-v0/out/fstype-multibit-v0.ttf

# 测试（双解释器）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src py -X utf8 -m pytest -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHONUTF8=1 ./_scratch/v312/Scripts/python.exe -m pytest -q

# 离线冒烟 / 安装验证
py tools/smoke_cli.py
py -3.12 -m venv _scratch/vinst && ./_scratch/vinst/Scripts/python.exe -m pip install -e ".[dev]"
./_scratch/vinst/Scripts/subsetaudit.exe --version
```
