> 方法论：`ai-tool-project-sprint`（装订 2026-10-21）｜布局门：`py tools/check_sprint_layout.py`｜脱敏门：`py tools/check_desensitized.py`｜续接对话第一件事 = 跑这两条门

# 00 · README 总览 — 10-21-subset-audit（字体派生产物体检：子集正确性审计）

- 性质：不参赛项目题 · 发布 GitHub **公开仓库** · 署名 yuluo554
- 定位宣言："**生成器一片红海（fontmin 6220★ / font-spider 5140★ / subfont 1636★ / glyphhanger 1123★），校验器接近真空**。本工具**审的是产物，不是字体项目**：输入 = 原字体 + 子集字体 + 必须支持的字符集，输出 = 子集是否真覆盖、GSUB/GPOS 是否被弄坏、许可是否允许子集、元数据是否被剥掉。fontbakery 服务字体作者，我们服务下游。"
- 交付形态：**纯本地 Python CLI（零网络、零商用字体、无模型）**。单一形态，不设备选。
- 发布：GitHub 公开仓库，v0.1.0（tag + Release 附产物 + 发布留档 `plan/RELEASE-M6.md`）。
- 查证基准日：**2026-10-19**；检索实测窗口 **2026-10-19T18:35Z–19:05Z**，定稿前复核 **2026-10-19T19:23Z–19:45Z**；本机环境 Python 3.8.8 / fontTools **4.57.0**。

## 文档索引表

| 文档 | 内容 | 状态 |
|---|---|---|
| plan/00-README总览.md | 本文档：索引 / **决策记录** / 弃选项 / 承诺-证据台账 / 里程碑 | ✅ v1 |
| plan/01-题目文档.md | 十段式题目定稿（生态基线、覆盖度三层结论、子集实测七项、五模块、评分、锚点、边界） | ✅ v1 |
| data/README.md | 依据查证记录（三态 + URL + 检索窗口）/ `fsType` 规范台账 / 子集实测七项台账 / 560 字体分布 + 不可外推声明 / 数值口径 / **更正记录** / 未核实项 | ✅ v1 |
| .gitignore | 字体二进制与 fixture 产物不入仓 | ✅ v1 |
| plan/02-架构与技术选型.md | 分层架构、只读表访问层、确定性架构、退出码契约、选型与弃选 | ✅ v1（M0） |
| plan/03-模块详设.md | 五子命令 + 共享层的接口、数据结构、处理顺序、失败路径、测试点 | ✅ v1（M0） |
| plan/04-数据计划.md | fixture 生成器确定性纪律、6 类破损 fixture 设计、golden 纪律、`fonts.lock` | ✅ v1（M0） |
| plan/05-里程碑.md | 每周可演示物、出口门、环境事实、风险预案 | ✅ v1（M0） |
| plan/06-交付对标与决策.md | 评分对标、缺口表、验收门、风险登记、追加决策 | ✅ v1（M0） |
| AGENTS.md | 仓库锚点：方法论名 + 布局门命令 + 强制布局 + 环境禁忌 | ✅ v1（M0） |
| tools/check_sprint_layout.py | 布局门（9 判据） | ✅ v1（M0） |
| tools/check_desensitized.py | 脱敏门（4 条规则） | ✅ v1（M0） |
| tools/verify_gates.py | 两道门的变异验证常驻（16 组） | ✅ v1（M0，靶子随里程碑翻新） |
| tools/smoke_cli.py | 离线冒烟（10 条命令，含一条 exit 2 负向） | ✅ v1（M0） |
| tools/gen_fixtures.py | F1–F6 合成破损 fixture 生成器（`--only` / `--check` / 独立 oracle 自证） | ✅ v1（M1） |
| tools/fetch_fonts.py | OFL 字体锁文件校验（默认离线 `--check`）/ 下载（`--download`） | ✅ v1（M1） |
| data/fonts.lock | 3 个 OFL 字体的 URL + 字节数 + sha256（二进制不入仓） | ✅ v1（M1） |
| data/fixtures/ | F1–F6 的 `expect.json` + `README.md` + `manifest.json`（产物 gitignore） | ✅ v1（M1） |
| src/subsetaudit/ | 五子命令 + 共享层（sfnt / cmapset / canonical）；五个模块**全部**已实现判定 | ✅ v1（M5，无骨架模块） |
| plan/HANDOFF-M*.md | 各里程碑交接快照（M1–M5 已落盘；**HANDOFF-M6 已写**，等发布棒执行） | ✅ v1（M5） |
| plan/RELEASE-M6.md | 发布留档（tag 时点事实 / tag 后追加事实分栏） | ⏳ M6 |

## 决策记录表

> 本表同时登记已定案决策与**弃选项**（含弃选理由），后续里程碑不再重复论证。

| 日期 | 决策 | 结论与理由 |
|---|---|---|
| 2026-10-19 | **① 技术护城河 ≈ 0，必须写在题面第一屏** | 本工具是 **fontTools 之上的规则层**（预估 2000–3000 行胶水），解析能力全部来自上游。**真正资产是规则集与 fixture 库，不是代码。** 题面、README、Release 说明一律不得暗示"技术壁垒"。 |
| 2026-10-19 | **② fontbakery 若加 subset profile，三个月内可被复制** | Rust 版 **fontspector 已具备全部解析与检查框架能力**（本机实测：`profile-universal` 77 个检查模块，`fs_type` 0 命中，但现在补一个 profile 的成本远低于本题的开发成本）。**唯一防守是输入形状不同**：他们审**字体项目**（输入 = 一个字体仓库/一套源文件），我们审**产物 + 需求**（原字体 + 子集字体 + 必须支持的字符集），退出码语义与 CI 集成点也不同。据此定案：本题**不做**"更全的字体 QA"，只做"产物侧闸门 + 回归套件"。 |
| 2026-10-19 | **③ E1（许可闸门）单独做 → 否决，降为 M1** | 单点许可闸门已有 6 个**0★**前任（`font license checker` 5 个结果头部 0★、`font license audit` 头部 fontsentry 2★、FontGuard 0★、fontcheck 0★）——**证明"有人想、没人用"**；单做无法形成可演示面。降为 M1 模块，与产物审计共享一个输入形状与一份报告。 |
| 2026-10-19 | **④ E2（覆盖差集）单独做 → 否决，降为 M2** | `nripankadas07/font-coverage-plan` **0★，2026-10-16 建仓当天停更**，已与"字符覆盖规划"同构；另 `font coverage checker` 检索为 0、`glyph coverage tool` 头部 0★ → 单做即撞同构死仓。降为 M2 模块，价值来自与 M1/M3/M4 共用同一份产物输入与同一套退出码。 |
| 2026-10-19 | **`fsType` 判定必须先读 `OS/2.version`** | 规范（✅ 原文核实）：**v0–v2** 多位并存时"least-restrictive permission indicated take precedence"；**v3+** 互斥为强制。本机 560 字体池中 **40 个 `0x000E` 全部落在 v0/v1**，另有 1 个 `0x0003` 在 v0 → **不做版本分流会把 41 个合法老字体误报为违规**（其中 40 个应解析为 Editable）。 |
| 2026-10-19 | **M4 的"位域矛盾"判定改为 cmap↔码页交叉比对（推翻初稿）** | 初稿把"`ulUnicodeRange1` 归零"当矛盾；**实测该归零是正确重算**（`ulUnicodeRange2` bit59 已置位），照初稿实现会产出**假阳性**。真实矛盾点是 `recalcCodePageRanges` 在无码页可用时**回退置 bit0 (Latin 1)**（fontTools 源码注释："so that the font works in MS Word"）→ 仅含 CJK 的产物声称支持 Latin-1。见 `data/README.md` §七 #3。 |
| 2026-10-19 | **`fsType` 结论是技术判定，不是法律意见** | 报告只回答"规范怎么读"，并在每条结论附**规范条款引用**；不得输出"这个字体你可以用/不能用"的法律结论。 |
| 2026-10-19 | **绝不入库商用字体** | 实测对象（Arial / Calibri / Microsoft YaHei / Segoe UI Emoji）**只读引用**，不复制不分发；`.gitignore` 阻断 `*.ttf/*.otf/*.ttc`；fixture 与回归只用 OFL 字体或程序合成的极小字体；需要复现商用字体行为时用"同构 OFL 字体 + 文档标注替代关系"。 |
| 2026-10-19 | **数据源只取 OFL，且二进制不入仓** | `data/fonts.lock` 记录 URL + 字节数 + sha256；`tools/fetch_fonts.py --check` 可离线校验哈希。已实测哈希：Inter 4.1 `InterVariable.ttf` 879,708 B / `sha256:4989b125…`。 |
| 2026-10-19 | **退出码契约：0 / 1 / 2** | `0` 通过、`1` 有发现（`error` 级）、`2` 输入非法。`SKIPPED(reason=...)` 恒为不影响退出码的 `note`（显式输出，不写日志了事）。 |
| 2026-10-19 | **首期不做子集生成器** | subfont 1636★ / glyphhanger 1123★ / fontmin 6220★ / font-spider 5140★ 红海；且生成器与校验器共用实现会丧失"独立判据"这一唯一价值。 |
| 2026-10-19 | **隐私与网络边界** | 纯本地零网络；仅 `tools/fetch_fonts.py`（用户显式运行时）联网下载 OFL 字体，默认 `--check` 不联网。 |

## 弃选项（否决理由）

| 弃选项 | 结论 | 理由 |
|---|---|---|
| E1 独立"字体许可闸门"产品 | **否决**（降为 M1） | 6 个 0★ 前任证明"有人想、没人用"；单点无法形成可演示面（见决策记录③） |
| E2 独立"字符覆盖差集"产品 | **否决**（降为 M2） | `font-coverage-plan` 0★（2026-10-16 建仓当天停更）已同构；单做撞死仓（见决策记录④） |
| E4 可变字体轴 / STAT 审计 | **否决** | fontbakery 已有 11+ 项（`fvar/axis_ranges_correct`、`inconsistencies_between_fvar_STAT`、`mandatory_avar_table`、`STAT_axis_record_for_each_axis`、`layout_valid_feature_tags` 等），fontspector 再叠数项；本机实测 fontTools 子集对 `fvar/STAT/avar/MVAR/HVAR/gvar` **保留正确**，无发现面 → **重写 = 抄** |
| 字体许可合规扫描器（扫描项目/域名/PDF 的字体引用） | **否决** | 属合规审计类禁区（需联网、需判"使用是否合规"），且 fontsentry(2★)/FontGuard(0★)/fontcheck(0★) 已有 |
| PDF 内嵌字体检查器 | **否决** | 与"PDF 解析 + 许可证判断"邻域重叠；输入形状不是"原字体 + 产物 + 需求" |
| 子集生成器 | **否决** | 生成器红海（14.3k★ 四个项目，两个已停更） |
| 轮廓几何 / hinting 审计 | **否决** | fontbakery/fontspector 的 `outline_*`、`hinting_impact` 已占 |
| 渲染视觉比对 | **否决** | 需引入渲染器与阈值，破坏"零模型、纯复算"的确定性纪律 |
| 引入 `uharfbuzz` 作 shaping 判据 | **缓议（不进首期）** | 会把"表级复算"变成"依赖特定 shaping 版本"，与确定性纪律冲突；首期只用 GSUB/GPOS 表级结构比对 |

## 承诺-证据台账

| 承诺（题面要求） | 落位 | 证据/状态 |
|---|---|---|
| 定位宣言含"审产物不审项目" | plan/01 §头部、README | ✅ 已写 |
| 护城河诚实说明（≈0 / 三个月可被复制 / 唯一防守是输入形状） | plan/01 §头部 + §八 | ✅ 已写 |
| 生态基线表（12 项 star + 最近推送） | plan/01 §2.1、data §一 | ✅ `gh api` 实测 2026-10-19 |
| fontbakery 三层覆盖结论 | plan/01 §2.2、data §二 | ✅ 源码 tarball 实测（`@check` 320 / vendorspecific 157 / subset 相关 5 个元数据检查） |
| 子集实测七项 | plan/01 §2.3、data §四 | ✅ 本机 fontTools 4.57.0，每项含命令 + 退出码 + 观察 |
| 需求原话（逐条 URL + 状态） | plan/01 §一 | ✅ 8 条元数据核对；#7 来源不可定位（降级）、#8 状态更正为 closed |
| 开源空白三行（禁写首创） | plan/01 §六 | ✅ 措辞为"生成器红海、校验器真空"并标 ⬜ 软论据 |
| M1 `license-gate`（版本分流 + 三类闸门） | plan/01 §三 M1 | ✅ 含 5 条验收；**M2 里程碑已实现**（五元结论口径入 §六.1.3） |
| M2 `coverage-diff`（三分类 + 编码优先级 + 回退链） | plan/01 §三 M2 | ✅ 含 3 条验收；**M3 里程碑已实现**（三分类/闭包/分块口径入 §六.2–§六.4） |
| M3 `layout-survival`（LookupType 7/9 解包） | plan/01 §三 M3 | ✅ 含 3 条验收（含 784 vs 0 对照）；**M4 里程碑已实现**（三元组/计数/连字规则口径入 §六.5.1–§六.5.6） |
| M4 `metadata`（cmap↔OS/2 一致性） | plan/01 §三 M4 | ✅ 含 4 条验收（**已按实测更正**）；**M5 里程碑已实现**（口径入 §六.9.1–§六.9.6） |
| M5 `report`（JSON + 退出码 0/1/2） | plan/01 §三 M5 | ✅ 含 4 条验收；**M5 里程碑已实现**（聚合单一路径入 §六.9.7） |
| 扩展项明确不设（可变字体轴/STAT） | plan/01 §三扩展项表 + §七 | ✅ 附 fontbakery 11+ 项名称 |
| 6 类合成破损 fixture | plan/01 §四 3、data §六 7 | ✅ F1–F6 命名与口径已定 |
| 数值口径一处定义 | data §六 | ✅ 9 条口径（§六.1 五元结论判定式 + 六条违规码 + `spec_ref` 字面量；§六.2 三分类级别 + §六.2.1 闭包；§六.3 两条失败路径；§六.4 互斥分区优先级；§六.5.1–§六.5.6 布局三元组 / 计数 / 判定式 / 连字规则 / 失败路径 / 落地约束；§六.9.1–§六.9.7 元数据 name/码页/Unicode 位域/maxp/首末码位/失败路径/report 聚合） |
| 560 字体分布 + 不可外推声明 | data §五 | ✅ 只读实测 + 声明 |
| 未核实项与更正记录 | data §七、§九 | ✅ 9 条更正 + 6 条未核实 |

## 里程碑

| 里程碑 | 目标 | DoD（出口门） | 状态 |
|---|---|---|---|
| **M0 装订与骨架** | `AGENTS.md` + 两道门 + `plan/00–06` + 可运行五子命令骨架 | `py tools/check_sprint_layout.py` 全绿（16 组变异已验证）；`subsetaudit --help` 与五子命令可跑；`pip install -e .` 可用 | ✅ |
| **M1 数据先行** | 6 类合成破损 fixture（F1–F6）+ OFL 字体回归套件 | `tools/gen_fixtures.py` 可重建全部 fixture；`tools/fetch_fonts.py --check` 校验 `fonts.lock` 哈希；每条 fixture 有 `expect.json` 与说明；**生成期自证**（用独立 oracle 复算计数与分类，不符即失败）；仓库内无任何字体二进制 | ✅ |
| **M2 许可闸门** | `license-gate` | `0x000E`+v0 不误报、`0x0108` 判禁子集、v3 多位并存必报；每条结论带规范条款引用；F1/F2/F3 golden 逐项一致 | ✅ |
| **M3 覆盖差集** | `coverage-diff` | 复现 `--text="汉字abc"` 静默丢字并判 `LOST_IN_SUBSET`；pdfcraft#381 字组"高频在、中频缺"指纹可复现；非 Unicode cmap 走 `SKIPPED`；F4 golden 一致 | ✅ |
| **M4 布局保真** | `layout-survival` | Type 7/9 解包后规则数正确（朴素遍历作对照）；默认丢弃标签被列出；`uniFB01 → glyph00003` 改名被认出 | ✅ |
| **M5 元数据与报告** | `metadata` + `report` | msyh 码页矛盾被抓住而 `ulUnicodeRange1=0` **不**误报（以 OFL 同构样本复现）；F5/F6 golden 一致；退出码 0/1/2 三档 fixture；报告逐字节确定 | ✅ |
| **M6 发布** | GitHub **公开仓库** v0.1.0 | **DoD = git tag + GitHub Release 附产物 + 发布留档三件套**（`plan/RELEASE-M6.md` 记 tag 时点事实与 tag 后追加事实）；干净环境 `pip install -e .` 后五子命令可用；`LICENSE`（MIT）与 `pyproject.toml` license 字段一致 | ⬜ |

**环境事实（口径随行）**：本机 Python **3.8.8**（因此不依赖 `tomllib`，所有锁文件/基线走 JSON 或受限 TOML 子集）；fontTools 4.57.0（`pyftsubset` 行为随版本漂移：`layout_features` 默认集、`prune_*` 默认值、`recalcCodePageRanges` 回退均在 4.x 内变动过）→ **报告必须写 `fonttools_version`；fixture golden 与 fontTools 版本绑定，升级需重跑 `tools/gen_fixtures.py --check`**。

**风险预案**：
1. **上游补齐**（fontbakery 加 subset profile / fontspector 加检查）→ 转为"下游闸门 + 回归套件"定位，不做正面竞争（见决策记录②）。
2. **fontTools 版本漂移导致 golden 失效** → golden 一律由生成器现场复算对账，不手写；版本升级视为 fixture 迁移事件。
3. **无法取得 OFL 字体**（离线环境）→ 全部 fixture 均可用 `fontTools.fontBuilder` 程序合成的极小字体构建，OFL 字体只用于"真实字体回归"层，可跳过并如实标注。
4. **许可结论被误当法律意见** → 报告头固定声明"技术判定，非法律意见"，每条结论必带条款引用。
