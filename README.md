> 方法论：`ai-tool-project-sprint`（装订 2026-10-21）｜布局门：`py tools/check_sprint_layout.py`｜脱敏门：`py tools/check_desensitized.py`｜新对话第一件事 = 跑这两条门

# SubsetAudit · 字体派生产物体检（子集正确性审计）

**审的是产物，不是字体项目。** 输入 = 原字体 + 子集字体 + 必须支持的字符集；
输出 = 子集是否真覆盖、GSUB/GPOS 是否被弄坏、许可是否允许子集、元数据是否被剥掉。

- **版本**：v0.1.0.dev0（M0 骨架）
- **交付形态**：纯本地 **Python CLI**（零网络、零模型、零商用字体）
- **运行期依赖**：`fonttools`（唯一）｜**Python** ≥ 3.8

## 护城河诚实说明（不得美化）

**技术护城河 ≈ 0。** 本工具是 **fontTools 之上的规则层**；解析能力全部来自上游。
真正资产是**规则集与 fixture 库**，不是代码。若上游（fontbakery / fontspector）补一个
subset profile，**三个月内可被复制**。唯一防守是**输入形状不同**：它们审字体项目（输入 =
一个字体仓库/一套源文件），我们审**产物 + 需求**。本题不宣称首创、不宣称无人做过。

## 安装

```bash
py -m venv .venv
# Windows（Git Bash / cmd 都是这个路径；venv 里没有 `py` 启动器，必须直接调 venv 的 python）
./.venv/Scripts/python.exe -m pip install --upgrade pip        # 必须：3.8 的 venv 自带 pip 20.2.3，不支持 PEP 660 可编辑安装
./.venv/Scripts/python.exe -m pip install -e ".[dev]"
# Linux / macOS
# ./.venv/bin/python -m pip install --upgrade pip
# ./.venv/bin/python -m pip install -e ".[dev]"

./.venv/Scripts/subsetaudit.exe --version     # Git Bash；cmd 用 .venv\Scripts\subsetaudit.exe
# 或者不装也行（源码树直接跑）：
# PYTHONPATH=src py -X utf8 -m subsetaudit --version
```

> **前置条件**：`pip install -e .` 需要 pip ≥ 21.3（PEP 660）。Python 3.8 的 `venv` 自带
> pip 20.2.3，**不先升级会报** `editable mode currently requires a setup.py based build`。

## 现状（M0 骨架）

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | 方法论装订 + 计划套件 + 可运行骨架 | ✅ |
| M1 | 数据先行：F1–F6 fixture 生成器 + `fonts.lock` | ⬜ |
| M2 | `license-gate` 许可闸门（`OS/2.version` 分流） | ⬜ |
| M3 | `coverage-diff` 覆盖差集（三分类 + 回退链） | ⬜ |
| M4 | `layout-survival` 布局保真（Type 7 解包） | ⬜ |
| M5 | `metadata` + `report`（cmap↔OS/2 交叉一致性） | ⬜ |
| M6 | 发布：GitHub 公开仓库 v0.1.0 | ⬜ |

> 状态语义：`✅` 已完成、`⬜` 未开始。**M0 的五个子命令能跑、退出码正确，但判定尚未实现**，
> 每个命令会输出 `SKIPPED(reason=module_not_implemented_in_m0)` —— 这是**显式跳过**，不是静默通过。

## 三个场景（最小复现命令）

> 以下命令在 **M2–M5 落地后**才产生真实判定；M0 阶段它们的退出码已正确，输出里带 `SKIPPED`。
> 未标注 `<...>` 的参数都是真实路径；尖括号是占位符，请替换。

### 场景一：许可闸门（能不能嵌、能不能子集）

```bash
subsetaudit license-gate <font.ttf>
subsetaudit license-gate <font.ttf> --markdown --out license.md
```

### 场景二：覆盖差集（子集是否真覆盖）

```bash
subsetaudit coverage-diff <source.ttf> --text "汉字abc"
subsetaudit coverage-diff <source.ttf> --corpus <chars.txt> --subset <subset.ttf>
```

### 场景三：布局与元数据（是否被弄坏）

```bash
subsetaudit layout-survival <source.ttf> <subset.ttf>
subsetaudit metadata <subset.ttf> --source <source.ttf>
subsetaudit report --source <source.ttf> --subset <subset.ttf> --text "abc" --format markdown --out audit.md
```

## 退出码

| 码 | 语义 |
|---|---|
| 0 | 通过（`warn` / `note` / `SKIPPED` 不影响） |
| 1 | 有发现（至少一条 `error` 级 finding） |
| 2 | 输入非法（文件不可读 / 非字体 / 缺必需参数 / 语料不可读） |

## 字段说明（规范 JSON）

```json
{
  "schema": "subsetaudit/report@1",
  "disclaimer": "技术判定，不是法律意见；每条结论可回指 spec_ref 或实测证据。",
  "tool": { "name": "subsetaudit", "version": "...", "fonttools_version": "..." },
  "inputs": { "source": "arial.ttf", "subset": "a.subset.ttf" },
  "summary": { "error": 0, "warn": 1, "note": 0, "skipped": 1 },
  "findings": [ { "module": "...", "code": "...", "severity": "error|warn|note",
                  "primary_key": "...", "message": "...", "evidence": {}, "spec_ref": "..." } ],
  "skipped": [ { "module": "...", "reason": "...", "detail": "..." } ]
}
```

- 排序键固定为 `(module, severity, primary_key)`；字符集按码位升序；三元组按 `(script, langsys, feature)`。
- 报告**不含**时间戳 / 绝对路径 / 主机名 / 用户名；同一输入两次运行**逐字节一致**。
- Markdown 只是渲染视图，**不参与** `digest`、**不参与**退出码。

## 已知边界与非目标

- **不做**可变字体轴 / STAT 审计（fontbakery 已有 11+ 项，重写 = 抄）。
- **不做**字体许可合规扫描（扫描项目/域名/PDF 的字体引用属合规审计，本工具只读单文件的 `fsType`）。
- **不做** PDF 内嵌字体检查、**不做**子集生成器、**不做**轮廓几何 / hinting / 渲染视觉比对。
- **绝不入库商用字体**：仓库不出现任何 `.ttf/.otf/.ttc`（`.gitignore` 强制）；fixture 与回归只用
  OFL 字体或程序合成的极小字体。需要复现某个商用字体的行为时，用**同构 OFL 字体替代并在文档标注**。
- **隐私红线**：运行期零网络；仅 `tools/fetch_fonts.py`（用户显式运行时）联网下载 OFL 字体，
  默认 `--check` 只校验已有文件。
- **结论纪律**：所有发现是"输入与产物之间的**可复算差异**"，不等于"这条字体不能上线"。
  `fsType` 判定是**技术性结论（规范怎么读）**，不是**法律意见**。

## 开发

```bash
# 门（每棒第一件事）
py tools/check_sprint_layout.py     # 布局门（方法论装订）
py tools/check_desensitized.py      # 脱敏门
py tools/verify_gates.py            # 两道门的变异验证（16 组必须全红）

# 测试（仓库根目录；tests/ 会自己把 src/ 放进路径）
PYTHONPATH=src py -X utf8 -m pytest -q
# 或装好之后：./.venv/Scripts/python.exe -m pytest -q
```

后续里程碑（M1 起）会用到这些脚本，**当前尚未实现**（见 `plan/05` 与 `plan/06` 缺口表）：

- `tools/gen_fixtures.py` — 生成 F1–F6 合成破损 fixture（含 `--check` 位级一致）
- `tools/fetch_fonts.py` — 校验 / 下载 `data/fonts.lock` 登记的 OFL 字体（默认 `--check` 离线）
- `tools/check_release.py` — 发布终态门（M6）

## 文档

| 文件 | 内容 |
|---|---|
| `plan/00-README总览.md` | 索引 / 决策记录 / 承诺-证据台账 / 里程碑 |
| `plan/01-题目文档.md` | 题目定稿：生态基线、覆盖度结论、实测七项、五模块、评分、锚点、边界 |
| `plan/02-架构与技术选型.md` | 分层、只读层、确定性架构、退出码契约、选型与弃选 |
| `plan/03-模块详设.md` | 五子命令接口、数据结构、处理顺序、失败路径、测试点 |
| `plan/04-数据计划.md` | fixture 设计、真值纪律、`fonts.lock` 口径 |
| `plan/05-里程碑.md` | 里程碑 DoD、环境事实、风险预案、已知未验证项 |
| `plan/06-交付对标与决策.md` | 评分对标、缺口表、验收门、风险登记 |
| `data/README.md` | **唯一数值口径来源**：规范台账、实测台账、字体池分布、更正记录 |
| `AGENTS.md` | 仓库锚点：方法论、门命令、强制布局、环境禁忌 |

## 许可

MIT（`LICENSE`）。