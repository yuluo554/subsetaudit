# HANDOFF-M2 · 许可闸门（交接单）

> 上一棒：M1（数据先行：F1–F6 生成器 + `fonts.lock` + `--check`），状态 ✅。
> 下一棒：**M2 许可闸门 `license-gate`**。用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M2.md 继续完成任务`。
> **第一动作（硬约束③）**：先跑 `py tools/check_sprint_layout.py`，红了先修布局再动手。

## 一、当前进度与证据

| 项 | 状态 | 证据（命令 + 结果） |
|---|---|---|
| 方法论装订 + 计划套件 | ✅ | `py tools/check_sprint_layout.py` → 9 PASS / 0 FAIL |
| 布局门 / 脱敏门 | ✅ | 9 条判据 + 4 条规则；`py tools/verify_gates.py` → **16 项全符合预期，0 SKIP** |
| 可运行骨架 + 退出码契约 | ✅ | 五子命令 exit 0 且输出含 `SKIPPED`；非字体文件 exit 2；`py tools/smoke_cli.py` 10 条 0 失败 |
| **M1 `data/fonts.lock`** | ✅ | 3 个 OFL 字体实测哈希：Inter 879,708 B / Noto Sans SC 8,331,336 B / Noto Sans Bold 575,740 B |
| **M1 `tools/fetch_fonts.py`** | ✅ | `--check` 离线：3 个 OK，exit 0；空目录 → 逐条 `MISSING` + exit 1（**不崩**）；`--list` 只读锁文件 |
| **M1 `tools/gen_fixtures.py`** | ✅ | 全量生成 F1–F6，逐项打印字节数 + sha256，exit 0；生成期自证（独立 oracle）全过 |
| **M1 `--check` 位级一致** | ✅ | 22 个文件逐字节一致；改一字节 / 删一产物都变红（两条测试钉住） |
| **M1 golden** | ✅ | 6 份 `expect.json`（无 `observed_*`）+ 6 份 `README.md` + `manifest.json`；产物 `out/` 已 gitignore |
| **M1 测试** | ✅ | `tests/test_fixtures.py` 34 项；全量 **86 项**，3.8 与 3.12 两条通道全绿 |
| **M1 CI 接线** | ✅ **本地等价校验（未接远端）** | 12 步；新增 3 步（生成 / `--check` / 离线锁校验）；两条顺序判据有测试钉住 |
| M2 `license-gate` | ⬜ | 未开始：`license_gate.py` 仍返回 `SKIPPED(reason=module_not_implemented_in_m0)` |

## 二、当前事实·状态不变量（下一棒动手前必须知道，否则一定会踩）

1. **五元结论里只有 `may_subset` 有口径**。`data/README.md` §六.1 目前只定义了
   `may_subset = (fsType & 0x0100) == 0` 与保留位掩码 `0xFCF1`。`embed_pdf` / `embed_app` /
   `embed_web` / `may_modify` **四条没有任何口径**。F1–F3 的 `expect.json` 里以
   `pending_conclusions` 显式登记了这件事。
   → **M2 的第一件事**：把这四条判定式写进 `data/README.md` §六.1 的**同一张表**，
   再改 `expect.json` 去掉 `pending_conclusions`，最后才写实现。直接在代码里现编 = 第二套口径。

2. **`license_gate.py` 里现在不能出现 `finding(`**，有一条测试钉住
   （`tests/test_cli.py::test_skeleton_modules_do_not_fabricate_findings`）。
   **写判定前先删该测试里 `license_gate` 那一项**（或改成"只对未实现的模块断言"），
   否则你的实现会被自己的守门拦住。删的时候确认 M2 真的开始了。

3. **F1/F2/F3 的 golden 已经在仓里**，直接可用：
   - F1 `0x0108` v4 → `may_subset=false`、`permission_bits=0x0008`、`mutual_exclusion_violation=false`；
   - F2 `0x000E` v0 → `permission_bits=0x000E`、`permission_name=Editable`、
     `permission_resolution=least_restrictive`、`may_subset=true`、**无互斥违规**（反例守护）；
   - F3 `0x000E` v3 → 同 F2 的位值，但 `mutual_exclusion_violation=true`。
   - F2 与 F3 的差别**只有两处**：`OS/2.version`（0 vs 3）+ 由版本决定的 OS/2 表长
     （**78 B vs 96 B**，`ulCodePageRange` 自 v0 起才有）。**不是"只差一个字节"** ——
     M1 初稿这么写，已实测更正（`data/README.md` §七 #10）。

4. **`_skeleton.py` 的 `skeleton_result()` 是唯一骨架出口**。`report` 子命令同时调
   `license_gate.evaluate()` 与 `metadata.evaluate()`；改 `license_gate` 的返回签名会连带影响
   `cli._run_report`。返回形状必须是 `(findings, skips, summary)`。

5. **状态副本 = 3 处 + 1 处台账**：`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态表，
   外加 `plan/00` 的承诺-证据台账。**翻状态必须四处一起翻**。

6. **变异靶子现在打在 M2 上**：`tools/verify_gates.py` 的 L4 / L9 用 `_mark_done(2)`，
   L12 用 `_mark_done(6)`。**M2 翻 ✅ 之后这三条会 SKIP** → 收尾时按同样思路改打 M3
   （L12 打 M6 不变，因为 `PENDING_TOOLS` 只剩 `check_release.py: 6`）。
   判别 = "这个靶子，在我把该做的事做完之后还存在吗？"

7. **`expect.json` 的 `fonttools_version` 是铸造版本常量**（`GOLDEN_FONTOOLS_VERSION = "4.57.0"`），
   不是运行时版本。实测 4.57.0 与 4.67.0 生成的 6 组 fixture **二进制逐字节相同**；
   写成运行时版本会让两条 CI 通道互相判红。M2 加 golden 时沿用这个常量。

8. **字体二进制永不入仓**：`.gitignore` 阻断 `*.ttf/*.otf/*.ttc/*.woff*`；`data/fonts/` 与
   `data/fixtures/**/out/` 都已 ignore。`git ls-files data/fixtures` 只有 `expect.json` /
   `README.md` / `manifest.json`（有测试钉住）。

9. **`_scratch/` 已 gitignore**：3.12 venv 在 `_scratch/v312`（fontTools 4.67.0 / pytest 8.4.2），
   OFL 字体原件在 `_scratch/fonts-dl/`，已复制进 `data/fonts/`（也被 ignore）。别提交、别引用绝对路径。

## 三、下一棒待办（M2 许可闸门，按序）

1. **先写口径**：把 `embed_pdf` / `embed_app` / `embed_web` / `may_modify` 四条判定式
   写进 `data/README.md` §六.1 的同一张表（每条带 MS-OS2 规范依据）。
2. 改 `data/fixtures/*/expect.json`：去掉 `pending_conclusions`，按新口径填四元期望
   （F1/F2/F3 各一份）。改完 `py tools/gen_fixtures.py` 重生成 + `--check` 必须仍绿。
3. 删/改 `tests/test_cli.py::test_skeleton_modules_do_not_fabricate_findings` 里
   `license_gate` 那一项。
4. 实现 `license_gate.evaluate(font_path) -> (findings, skips, summary)`：
   读 `OS/2.version` → `bits = fsType & 0x000F` → 版本分流（v0–v2 最宽松 / v3+ 互斥违规）
   → bit8 / bit9 → 保留位 `0xFCF1` → 五元结论，每条带 `spec_ref`。
5. 失败路径：无 OS/2 表 → `SKIPPED(reason=no_os2_table)` + exit 0；文件不可读 → exit 2（已由 `sfnt.open_font` 保证）。
6. 报告固定一句"技术判定，不是法律意见"（`canonical.DISCLAIMER` 已有，确认出现在输出里）。
7. 测试：`tests/test_license_gate.py` —— F1/F2/F3 golden 逐项、bit0 单列（`0x0001`/`0x0003`）、
   无 OS/2 → SKIPPED、五元每条带 `spec_ref`、**改坏实现必红**。
8. 收尾：翻 M2 ✅（四处）+ 修变异靶子（L4/L9 → M3）+ 写 `plan/HANDOFF-M3.md` + commit。

## 四、既定口径清单（K 编号，动了会打挂测试）

| K | 口径 | 落点 |
|---|---|---|
| K1 | 数值口径**单点**在 `data/README.md` §六；代码与文案不得另立 | `plan/01` §三，`plan/04` §5 |
| K2 | 退出码 0/1/2 只在 `cli.main` 收口；argparse 用法错误天然是 2 | `cli.py`，`plan/02` §3 |
| K3 | `SKIPPED(reason=...)` 恒 note、恒进输出、恒不影响退出码 | `canonical.skipped` |
| K4 | 排序键 `(module, severity, primary_key)`；JSON 键序在构造处固定，不用 `sort_keys` | `canonical.sort_findings` / `build_report` |
| K5 | 报告不含时间戳/绝对路径/主机名/用户名；`inputs` 只存 basename | `canonical.input_ref` |
| K6 | 共享层只读：`sfnt.py` 不得出现 `.save(`（有测试钉住） | `tests/test_core.py::test_read_only_layer_never_saves` |
| K7 | 零网络零模型：**包内**（`src/subsetaudit/`）不得 import `urllib/requests/socket/...`、模型库 | `tests/test_cli.py::test_no_runtime_network_or_model_imports` |
| K8 | 代码底线 Python 3.8（无 `tomllib`、无 3.9+ 语法、无 `Path.write_text(newline=)`） | `pyproject.toml` requires-python |
| K9 | 版本三处一致：`__init__.__version__` / `pyproject.toml` / README 状态行 | 两条测试 |
| K10 | 布局门 `PENDING_TOOLS` 登记项**随里程碑翻 ✅ 自清理** | `tools/check_sprint_layout.py` 顶部 |
| K11 | 门的变异验证常驻 `tools/verify_gates.py`，每棒收尾重跑；靶子随进度翻新 | CI step 5 |
| K12 | **golden 的 `fonttools_version` = 铸造版本常量**，不是运行时版本 | `tools/gen_fixtures.py::GOLDEN_FONTOOLS_VERSION` |
| K13 | **fixture 生成禁时钟**：`head.created/modified` 钉 `FIXED_EPOCH`；`TTFont(..., recalcTimestamp=False)` | `tools/gen_fixtures.py::_subset` |

## 五、本机环境坑（只写实测过的）

- **`raw.githubusercontent.com` 会中途重置**（2026-10-21 实测）：单次 `curl` 只拿到 4.5–7.5 MB
  （目标 8,331,336 B）。可靠做法 = HTTP Range 断点续传 + 字节数收敛判定。
  `tools/fetch_fonts.py --download` 走**单次请求**，不稳时报 `DOWNLOAD_FAILED`（校验在写盘前，
  不会留半截文件）—— 这是**已知未验证项**（`plan/05` §已知未验证项 #6），别写成"下载可用"。
- **`FontBuilder` 默认把 `head.created/modified` 设为当前时钟**（实测：间隔 1.2 s 两次生成 → 字节不同）；
  `TTFont.save()` 默认 `recalcTimestamp=True` 会在子集时再改一次。两处都必须钉死。
- **`os.path.relpath` 跨盘符抛 `ValueError`**（2026-10-21 实测）：pytest 的 `tmp_path` 在 `C:`，
  仓库在 `D:`。任何"打印相对路径"的地方都要兜底（`_display_path`）。
- **pip 走系统代理会失败**：一律 `NO_PROXY="*" no_proxy="*"` + 清华镜像。
- **`py` 是 Windows 启动器，ubuntu CI 上没有** → workflow 里一律 `python`；
  `tests/test_ci_workflow.py` 会拦住 `py ` 开头的行。
- **CI 里步骤顺序有依赖**：三个门（布局/脱敏/变异）**只用标准库**，可在 install 前跑；
  `gen_fixtures.py` / `fetch_fonts.py` 需要 fontTools，**必须在 `pip install -e ".[dev]"` 之后**
  （两条顺序判据有测试钉住：`test_ci_installs_dependencies_before_scripts_that_need_them`、
  `test_gates_are_stdlib_only_so_they_run_before_install`）。
- **`py -3.12` 通道默认没有 fontTools**：`py -3.12 -m venv _scratch/v312` + 镜像装依赖
  （现有 venv：fontTools 4.67.0 / pytest 8.4.2）。
- **Git Bash 会把 `/xxx` 参数改写成 `D:/program/Git/xxx`**：测"不存在路径"时用相对路径或 `$(pwd)/...`。
- **capsys 只能消费一次**：一次接住三流（`tests/test_cli.py::Result`）。
- 中文输出一律 `py -X utf8`；CI 侧靠 job 级 `PYTHONUTF8=1`。
- **`git ls-files` 会静默向上解析到父仓库**：断言前先比对 toplevel 与本项目根，不一致就显式 skip。

## 六、DoD 逐项 checklist（M2）

- [ ] `data/README.md` §六.1 新增四条判定式（`embed_pdf` / `embed_app` / `embed_web` / `may_modify`），每条带 MS-OS2 依据
- [ ] F1/F2/F3 的 `expect.json` 去掉 `pending_conclusions` 并填全五元结论；`--check` 仍位级一致
- [ ] `tests/test_cli.py::test_skeleton_modules_do_not_fabricate_findings` 已按 M2 调整（只对未实现模块断言）
- [ ] F1 `0x0108` → `may_subset=false` 且 finding 引 `MS-OS2 bit8`（`spec_ref` 非空）
- [ ] F2 `0x000E`+v0 → 无互斥违规、解析为 Editable、`may_subset=true`（**不得误报**）
- [ ] F3 `0x000E`+v3 → 互斥违规 `error`；最宽松解析仍是 Editable，两者独立成条
- [ ] bit0 保留位置位单列（`0x0001`、`0x0003` 两类样本各一条）
- [ ] 五元结论每条带 `spec_ref`；输出固定含"技术判定，不是法律意见"
- [ ] 无 OS/2 表 → `SKIPPED(reason=no_os2_table)`，退出码 0
- [ ] `tests/test_license_gate.py` 存在且全绿；**改坏实现至少一层测试必红**（变异验证）
- [ ] 双解释器测试全绿（3.8 全局 / 3.12 venv）
- [ ] `py tools/check_sprint_layout.py` / `check_desensitized.py` 全绿
- [ ] `py tools/verify_gates.py` 16 项全符合预期、0 SKIP（靶子已翻新到 M3）
- [ ] `py tools/gen_fixtures.py --check` 位级一致
- [ ] `plan/HANDOFF-M3.md` 已落盘（七节）

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
py tools/fetch_fonts.py --download  # 联网补齐（用户显式触发；不稳见 §五）
py tools/fetch_fonts.py --list

# 测试（双解释器）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src py -X utf8 -m pytest -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHONUTF8=1 ./_scratch/v312/Scripts/python.exe -m pytest -q

# 离线冒烟 / 安装验证
py tools/smoke_cli.py
py -3.12 -m venv _scratch/vinst && ./_scratch/vinst/Scripts/python.exe -m pip install -e ".[dev]"
./_scratch/vinst/Scripts/subsetaudit.exe --version
```
