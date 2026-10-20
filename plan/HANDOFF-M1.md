# HANDOFF-M1 · 数据先行（交接单）

> 上一棒：M0（方法论装订 + 计划套件 + 可运行骨架），状态 ✅。
> 下一棒：**M1 数据先行**。用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M1.md 继续完成任务`。
> **第一动作（硬约束③）**：先跑 `py tools/check_sprint_layout.py`，红了先修布局再动手。

## 一、当前进度与证据

| 项 | 状态 | 证据（命令 + 结果） |
|---|---|---|
| 方法论装订三件 | ✅ | `AGENTS.md`；`py tools/check_sprint_layout.py` → 9 PASS / 0 FAIL；`plan/00` 顶部装订行 |
| 布局门 | ✅ | 9 条判据；12 组变异（L1–L12）全部按预期变红；还原后 30 个文件逐字节一致、门复绿 |
| 脱敏门 | ✅ | 4 条规则（V1–V4 全红）；扫 35 个文本文件 0 命中；豁免面 = 1 份（门自身） |
| 计划套件 | ✅ | `plan/00`–`06` + `data/README.md`；布局门 LAYOUT.SECTIONS 8 份小节齐备 |
| 可运行骨架 | ✅ | `pip install -e ".[dev]"` 成功；`subsetaudit --version` → `subsetaudit 0.1.0.dev0`；五子命令 exit 0 且输出含 `SKIPPED` |
| 退出码契约 | ✅ | 五子命令对非字体文件一律 exit 2；缺 `--text/--corpus` 是 argparse exit 2；`SKIPPED` 不影响退出码（exit 0） |
| 测试 | ✅ | 42 项，`py -3.8`（fontTools 4.57.0 / pytest 7.4.4）与 `py -3.12`（fontTools 4.67.0 / pytest 8.4.2）**两条通道都全绿** |
| 离线冒烟 | ✅ | `py tools/smoke_cli.py` 10 条命令 0 失败（含一条 exit 2 负向） |
| CI 接线 | ✅ **本地等价校验（未接远端，CI 待首推验证）** | `.github/workflows/ci.yml` 本地 `yaml.safe_load` 通过：1 job / 8 steps；`tests/test_ci_workflow.py` 断言门步骤、`python` 而非 `py`、`PYTHONUTF8=1`、step name 无裸 `: ` |
| 版本一致 | ✅ | `__init__.__version__` == `pyproject.toml` == README 状态行（两条测试断言） |
| 无字体二进制 | ✅ | `tests/test_cli.py::test_no_font_binaries_tracked_by_git`（git 索引过滤为空） |
| **M1 数据层** | ⬜ | 未开始：`tools/gen_fixtures.py`、`tools/fetch_fonts.py`、`data/fonts.lock` 均不存在（布局门以 `PENDING_TOOLS` 显式登记，属预期） |

## 二、当前事实·状态不变量（下一棒动手前必须知道，否则一定会踩）

1. **M0 的五个模块是"输入校验 + 显式 SKIPPED"，不是判定**。`license_gate.py` / `coverage_diff.py` /
   `layout_survival.py` / `metadata.py` 里**不许出现 `finding(` 调用**——有一条测试
   （`test_skeleton_modules_do_not_fabricate_findings`）钉住这一点。M2–M5 填实判定时，
   **先删该测试再写判定**（否则你的实现会被自己的守门拦住），且删的时候要确认对应里程碑真的开始了。
2. **五元结论的判定式还没定义**。`plan/03` §2 只写了"`{embed_pdf, embed_app, embed_web, may_subset,
   may_modify}`"这个形状；`data/README.md` §六.1 只定义了 `may_subset = (fsType & 0x0100) == 0` 与
   保留位掩码，**其余四条没有口径**。M2 的第一件事是**把这四条判定式写进 `data/README.md` §六.1 的同一张表**，
   再实现——直接在代码里现编 = 制造第二套口径（`plan/01` §三 明令禁止）。
3. **布局门的 `PENDING_TOOLS` 是自清理登记表**（`tools/check_sprint_layout.py` 顶部）：
   `tools/gen_fixtures.py: 1`、`tools/fetch_fonts.py: 1`、`tools/check_release.py: 6`。
   **M1 收尾把 M1 翻 ✅ 的同时必须删掉前两条**，否则 LAYOUT.DOC_TOOLS 变红（变异 L12 正是这条）。
4. **变异靶子随进度过期**：`tools/verify_gates.py` 的 L2/L4/L9/L10/L12 都依赖"M1 仍是 ⬜"。
   M1 翻 ✅ 之后，这些靶子会崩或失效 → **收尾时先跑 `py tools/verify_gates.py`，按报错改靶子**
   （建议改打 M2 或"哨兵里程碑行"），**并保证 16 组仍全红**。
   **本轮已实测一次靶子过期**：M0 收尾时写下这份 HANDOFF，`plan/HANDOFF-M1.md` 从"不存在"变成
   "存在"，L4 原来用 `_create` 造临时件的写法当场崩（`临时文件已存在`）。已改成两态：
   文件不存在 → 造缺节临时件；文件存在 → 改真实文件里的某一节标题。同时给验证器加了
   **显式 SKIP 语义**（构造不出靶子 → 打印 `SKIP` + 计数，既不算 FAIL 也不算 PASS）——
   判别 = **"这个靶子，在我把该做的事做完之后还存在吗？"**
5. **状态副本 = 3 处 + 1 处台账**：`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态表，
   外加 `plan/00` 的承诺-证据台账（门单独判据 `LAYOUT.LEDGER`）。**翻状态必须四处一起翻**。
6. **`_scratch/` 是临时目录且已 gitignore**：本轮的 3.12 venv 在 `_scratch/v312`、
   安装验证 venv 在 `_scratch/vinst`。**别把它们提交，也别引用里面的绝对路径**。
7. **报告里 `inputs` 只存 basename**（`canonical.input_ref`）。M1 起若要在报告里加"字体来源 URL"，
   **不许**放本机路径；URL 只出现在 `data/fonts.lock`。
8. **字体二进制永不入仓**：`.gitignore` 已阻断 `*.ttf/*.otf/*.ttc/*.woff*`；`fixtures` 产物落
   `data/fixtures/**/out/`（也已 gitignore）。M1 的生成器**必须**把产物写到被 ignore 的目录，
   只把 `expect.json` 与脚本入仓。

## 三、下一棒待办（M1 数据先行，按序）

1. `data/fonts.lock`（JSON，版本 1）：至少 Inter 4.1 `InterVariable.ttf`（879,708 B /
   `4989b125…` 已有实测值，见 `data/README.md` §八）+ 2 个 Noto 字体（sha256 待首次下载写入）。
2. `tools/fetch_fonts.py`：默认 `--check` **不联网**，只校验 `data/fonts/` 已有文件；
   缺文件报 `MISSING` 并 exit 1（不崩）；`--download` 才联网。
3. `tools/gen_fixtures.py`：F1–F6（`plan/04` §2 表），`fontBuilder` 程序合成，**禁时钟/禁随机/禁 set 迭代序**；
   `--only F1,F3` 部分运行；`--check` 重生成到临时目录逐字节 `cmp`。
4. 每个 fixture 落 `expect.json`（**只存输入与期望**，不得出现 `observed_*`）+ `README.md` 说明。
5. 生成期自证：独立 oracle（纯位运算 / 独立 cmap 读取）复算计数与分类，不符即失败。
6. 测试：`tests/test_fixtures.py`（生成器确定性、`--check`、golden 逐项、**生成器被改坏必红**）。
7. 收尾：翻 M1 ✅（四处）+ 删 `PENDING_TOOLS` 前两条 + 修变异靶子 + 写 `plan/HANDOFF-M2.md` + commit。

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
| K11 | 门的变异验证常驻 `tools/verify_gates.py`，每棒收尾重跑 | CI step 3 |

## 五、本机环境坑（只写实测过的）

- **`py -3.12` 通道默认没有 fontTools**（2026-10-21 实测）：要跑 3.12 必须建 venv 装依赖；
  本次做法 = `py -3.12 -m venv _scratch/v312` + `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple`。
  **本机 3.12 现在仍没有全局 fontTools**（依赖只装在 `_scratch/v312`）。
- **pip 走系统代理会失败**：一律 `NO_PROXY="*" no_proxy="*"` + 清华镜像。
- **`py` 是 Windows 启动器，ubuntu CI 上没有** → workflow 里一律 `python`；
  `tests/test_ci_workflow.py` 会拦住 `py ` 开头的行。
- **Git Bash 会把 `/xxx` 参数改写成 `D:/program/Git/xxx`**（实测：`subsetaudit license-gate /nonexistent.ttf`
  报的是 `D:/program/Git/nonexistent.ttf`）。测"不存在路径"时用**相对路径**或 `$(pwd)/...`。
- **capsys 只能消费一次**（M0 实测踩到两次）：`readouterr()` 二次调用返回空串，
  看起来像"错误信息没打印"。测试里一次接住三流（见 `tests/test_cli.py::Result`）。
- **`python -m subsetaudit` 需要 `__main__.py`**（M0 冒烟实测：没有它报
  `No module named subsetaudit.__main__`）。已补 `src/subsetaudit/__main__.py`。
- 中文输出一律 `py -X utf8`；CI 侧靠 job 级 `PYTHONUTF8=1`（两条通路都要加固）。

## 六、DoD 逐项 checklist（M1）

- [ ] `data/fonts.lock` 入仓，含 Inter 实测字节数与 sha256
- [ ] `tools/fetch_fonts.py --check` 在无网络下可跑，缺文件报 `MISSING`（exit 1，不崩）
- [ ] `tools/gen_fixtures.py` 无参数全量生成 F1–F6，exit 0，打印每个 fixture 的字节数与 sha256
- [ ] `tools/gen_fixtures.py --check` 位级一致（重生成到临时目录 → 逐字节 `cmp`）
- [ ] 每个 fixture 有 `expect.json`（无 `observed_*`）与 `README.md`
- [ ] 生成期自证：独立 oracle 复算，不符即失败
- [ ] `tests/test_fixtures.py` 存在且全绿；**把生成器改坏 → 至少一层测试必红**（变异验证）
- [ ] `py tools/check_sprint_layout.py` 全绿（M1 翻 ✅、`PENDING_TOOLS` 清理后）
- [ ] `py tools/check_desensitized.py` 0 命中
- [ ] `py tools/verify_gates.py` 全组符合预期（靶子已随 M1 翻 ✅ 翻新）
- [ ] 双解释器测试全绿（3.8 全局 / 3.12 venv）
- [ ] `git ls-files` 无字体二进制
- [ ] `plan/HANDOFF-M2.md` 已落盘（七节）

## 七、关键命令速查

```bash
# 门（每棒第一件事）
py tools/check_sprint_layout.py
py tools/check_desensitized.py
py tools/verify_gates.py            # 变异验证；收尾必须重跑

# 测试（双解释器）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src py -X utf8 -m pytest -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHONUTF8=1 ./_scratch/v312/Scripts/python.exe -m pytest -q

# 离线冒烟 / 安装验证
py tools/smoke_cli.py
py -3.12 -m venv _scratch/vinst && ./_scratch/vinst/Scripts/python.exe -m pip install -e ".[dev]"
./_scratch/vinst/Scripts/subsetaudit.exe --version

# M1 将新增（当前不存在）
py tools/gen_fixtures.py            # 全量生成 F1–F6
py tools/gen_fixtures.py --check    # 位级一致
py tools/fetch_fonts.py --check     # 离线校验 data/fonts.lock
```
