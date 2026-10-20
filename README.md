> 方法论：`ai-tool-project-sprint`（装订 2026-10-21）｜布局门：`py tools/check_sprint_layout.py`｜脱敏门：`py tools/check_desensitized.py`｜新对话第一件事 = 跑这两条门

# SubsetAudit · 字体派生产物体检（子集正确性审计）

**审的是产物，不是字体项目。** 输入 = 原字体 + 子集字体 + 必须支持的字符集；
输出 = 子集是否真覆盖、GSUB/GPOS 是否被弄坏、许可是否允许子集、元数据是否被剥掉。

- **版本**：v0.1.0.dev0（M4 布局保真完成；元数据/报告判定待 M5）
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

## 现状（M4 布局保真完成）

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | 方法论装订 + 计划套件 + 可运行骨架 | ✅ |
| M1 | 数据先行：F1–F6 fixture 生成器 + `fonts.lock` | ✅ |
| M2 | `license-gate` 许可闸门（`OS/2.version` 分流） | ✅ |
| M3 | `coverage-diff` 覆盖差集（三分类 + 回退链） | ✅ |
| M4 | `layout-survival` 布局保真（Type 7/9 解包） | ✅ |
| M5 | `metadata` + `report`（cmap↔OS/2 交叉一致性） | ⬜ |
| M6 | 发布：GitHub 公开仓库 v0.1.0 | ⬜ |

> 状态语义：`✅` 已完成、`⬜` 未开始。**`license-gate`、`coverage-diff` 与 `layout-survival`
> 已产出真实判定**；`metadata` / `report` 的判定部分仍输出
> `SKIPPED(reason=module_not_implemented_in_m0)` —— 这是**显式跳过**，不是静默通过。

### `license-gate` 输出形状

```json
"summary": {
  "fsType": "0x0108", "os2_version": 4,
  "permission_bits": "0x0008", "permission_name": "Editable",
  "permission_resolution": "direct",
  "conclusions": {
    "embed_pdf":  { "value": true,  "spec_ref": "MS-OS2 §fsType bits0-3 (0/4/8 allow document embedding)" },
    "embed_app":  { "value": false, "spec_ref": "MS-OS2 §fsType value 0 (permanent installation)" },
    "embed_web":  { "value": false, "spec_ref": "MS-OS2 §fsType bits0-3 + bit8 (temporary loading for viewing, no subsetting)" },
    "may_subset": { "value": false, "spec_ref": "MS-OS2 §fsType bit8 (No subsetting)" },
    "may_modify": { "value": true,  "spec_ref": "MS-OS2 §fsType bits0-3 (editing permitted / read-only)" }
  },
  "violations": ["FSTYPE_NO_SUBSET"]
}
```

判定式与六条违规码的**唯一来源**是 `data/README.md` §六.1；代码里的 `spec_ref` 是那张表的逐字副本
（有测试解析该表做对账，改一边不改另一边必红）。`may_modify` 只回答"`fsType` 是否禁止文档/产物被编辑"，
**不回答**"是否授予修改字体软件本身的权利"。

### `coverage-diff` 输出形状

```json
"summary": {
  "required": { "count": 5, "blocks": { "BMP": 5, "ExtA": 0, "ExtB+": 0, "other": 0 } },
  "coverage": {
    "OK": ["U+0061", "U+0062", "U+0063"],
    "MISSING_IN_SOURCE": [],
    "LOST_IN_SUBSET": ["U+5B57", "U+6C49"],
    "counts": { "OK": 3, "MISSING_IN_SOURCE": 0, "LOST_IN_SUBSET": 2 },
    "blocks": { "OK": { "BMP": 3, "ExtA": 0, "ExtB+": 0, "other": 0 }, "...": "..." }
  },
  "closure": { "added": [], "added_codepoints": 0, "missing_in_source": 0, "lost_in_subset": 0 },
  "fallback_hint": [ { "block": "BMP", "lost": 2, "subset_available_in_block": 3 } ],
  "cmap": { "source_chosen": [[3, 1, 4, 5]], "source_subtables": [[0, 3, 4, 5], [3, 1, 4, 5]] },
  "strict_source": false, "subset_present": true
}
```

- 判定式、级别与 `spec_ref` 的唯一来源是 `data/README.md` §六.2；闭包口径 §六.2.1；编码优先级与失败路径
  §六.3；分区计数 §六.4（**互斥分区，ExtA 先于 BMP 判**）。
- **`--strict-source`** 只把 `MISSING_IN_SOURCE` 由默认 `warn` 提到 `error`（默认不判红：原文缺字是
  语料/源字体的问题，本工具审的是产物）。
- **取不到 Unicode cmap**（无 cmap 表 / 仅有 `(1,0)`）→ `SKIPPED(reason=no_cmap_table|no_unicode_cmap)`，
  `summary` 为空、退出码 0：**不会**给出"覆盖为空 = 通过"的假结论。

### `layout-survival` 输出形状

```json
"summary": {
  "layout": {
    "spec_ref": "data/README §6.5",
    "ligature_scope": "all",
    "source": {
      "gsub": { "present": true, "lookups": 15, "subtables_raw": 15, "subtables_naive": 15,
                "extension_lookups": 0, "subtable_types": { "1": 11, "3": 1, "4": 3 },
                "ligature_rules_raw": 340, "ligature_rules_naive": 340, "feature_variations": 0 },
      "gpos": { "present": true, "...": "..." },
      "triples": { "GSUB": { "present": true, "count": 198 }, "GPOS": { "present": true, "count": 136 } }
    },
    "subset": { "gsub": { "...": "..." }, "gpos": { "...": "..." }, "triples": { "...": "..." } },
    "lost": { "triples": 310, "ligature_rules": 333, "ligature_renamed": 0 }
  }
}
```

- 三元组、判定式与 `spec_ref` 的唯一来源是 `data/README.md` §六.5（枚举规则 5.1 / 扩展解包 5.2 /
  判定式 5.3 / 连字规则 5.4 / 失败路径 5.5 / 落地约束 5.6）。
- **`LookupType 7`（GSUB）与 `LookupType 9`（GPOS）都解包** —— 只解 7 会让 GPOS 整段读不到
  （商用字体只读观察：Arial 134 个 GPOS lookup 全为 Type 9）。
- `subtables_naive` / `ligature_rules_naive` 是**不展开 Extension** 时可见的计数，**只作对照、不作结论**；
  三个 OFL 字体没有 Extension → `naive == raw`。
- 连字规则按**输入码位序列**比对（子集后字形名会变成 `glyph00003` 这类占位名，不可比）：
  规则消失 → `LAYOUT_LIGATURE_LOST`（`error`）；规则仍在但目标字形失去稳定名字 →
  `LAYOUT_LIGATURE_RENAMED`（`warn`，退出码不变）。
- 两侧都没有 `GSUB`/`GPOS` → `SKIPPED(reason=no_layout_tables)`、`summary` 为空、退出码 0；
  只有一侧有 → 照常判定 + `SKIPPED(reason=layout_tables_missing_on_one_side)`（**不整份放弃**）。

## 三个场景（最小复现命令）

> 以下命令中，`license-gate`（M2）、`coverage-diff`（M3）与 `layout-survival`（M4）已产出真实判定；
> `metadata` 在 M5 落地前退出码已正确、输出里带 `SKIPPED`。
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
| 1 | 有发现（至少一条 `error` 级 finding，如 `LOST_IN_SUBSET`、`FSTYPE_*`、`LAYOUT_FEATURE_LOST`、`LAYOUT_LIGATURE_LOST`；`coverage-diff` 默认的 `MISSING_IN_SOURCE` 是 `warn`，加 `--strict-source` 才到 1；`LAYOUT_LIGATURE_RENAMED` 也只是 `warn`） |
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

# 测试（仓库根目录直接跑；tests/conftest.py 会把 src/ 放进路径，无需先安装）
py -X utf8 -m pytest -q
```

后续里程碑（M2 起）会用到这些脚本，**当前尚未实现**（见 `plan/05` 与 `plan/06` 缺口表）：

- `tools/check_release.py` — 发布终态门（M6）

数据层（M1，已落地）：

- `tools/gen_fixtures.py` — 生成 F1–F6 合成破损 fixture（`--check` 位级一致、`--only` 部分运行）
- `tools/fetch_fonts.py` — 校验 / 下载 `data/fonts.lock` 登记的 OFL 字体（默认 `--check` 离线）

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