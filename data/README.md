# data/ · 查证记录、规范台账、实测台账与数值口径（v1）

> 本文件是 `10-21-subset-audit` 的**唯一数值口径来源**。`plan/*.md`、代码与文案中出现的任何结论，都必须能回指到本文件的某一节；不得另立第二套口径。
>
> - **三态标注**：✅ 实测 / 原文核实；⬜ 软论据或未复现；**无标注 = 不得使用**。
> - **环境**：Windows（`C:\Windows\Fonts` 只读）；Python **3.8.8**；fontTools **4.57.0**；git 2.54.0.windows.1；`gh` 2.93.0。
> - **检索窗口**：生态与 issue 元数据 —— 原始查证 **2026-10-19T18:35Z–19:05Z**，定稿前复核 **2026-10-19T19:23Z–19:45Z**；本机字体/子集实测 —— **2026-10-19T19:23Z–19:45Z**（文件定稿日 2026-10-20 本地）。
> - **字体二进制不入仓**：本目录只放文本与锁文件；`.ttf/.otf/.ttc` 由 `.gitignore` 排除。

## 一、生态基线台账（✅ `gh api` 实测，2026-10-19）

| 仓库 | ★ | 最近推送 | 备注 |
|---|---|---|---|
| fonttools/fonttools | 5294 | 2026-10-19 | — |
| fonttools/fontbakery | 705 | 2025-11-04 | 近 1 年无提交 |
| fonttools/fontspector | 116 | 2026-10-19 | 活跃 |
| harfbuzz/harfbuzz | 6162 | 2026-10-19 | 含 hb-subset |
| opentypejs/opentype.js | 5034 | 2026-08-08 | — |
| googlefonts/fontmake | 895 | 2026-10-09 | 构建器 |
| ecomfe/fontmin | 6220 | 2025-08-13 | 生成器 |
| aui/font-spider | 5140 | 2022-12-30 | 生成器，已停更 |
| Munter/subfont | 1636 | 2026-09-20 | 生成器 |
| filamentgroup/glyphhanger | 1123 | 2021-07-01 | 生成器，已停更 |
| microsoft/Font-Validator | 128 | — | 源端校验 |
| khaledhosny/ots | 313 | 2026-10-16 | 沙箱化解析器 |

**计数口径**：`gh api repos/<owner>/<repo> --jq .stargazers_count` / `.pushed_at`。仓库名以 `gh` 实际解析结果为准（`aclh/font-spider`、`filipelinhares/glyphhanger` 为错误名，实测 404；正确名为 `aui/font-spider`、`filamentgroup/glyphhanger`）。

## 二、fontbakery / fontspector 覆盖度台账（✅ tarball 源码实测）

| 项目 | 口径 | 实测值 |
|---|---|---|
| fontbakery `Lib/fontbakery/checks/` 下 `.py` 总数 | 文件计数 | **373**（其中 `__init__.py` 45 个） |
| fontbakery `@check` 装饰器数 | `grep -rn "@check(" Lib/fontbakery/checks/` | **320** |
| fontbakery `vendorspecific/` 的 `@check` 数 | 同上，限该目录 | **157** |
| fontbakery `checks/` 下 `subset` 命中的 `.py` | 文件路径含 `subset` | **5 个 Google Fonts 元数据检查**（`metadata/includes_production_subsets`、`single_cjk_subset`、`subsets_order`、`unreachable_subsetting`、`unsupported_subsets`）+ 1 个测试字体（`data/test/...subset.ttf`） |
| fontbakery `fsType` 相关检查 | 路径含 `fstype` | **2 个**：`vendorspecific/googlefonts/fstype.py`（`if value != 0: yield FAIL`）、`vendorspecific/microsoft/fstype.py`（`required_value = 8`） |
| fontbakery 保留位掩码 | 源码字面量 | `0b1111110011110001` = **0xFCF1**（bit0 + bits4–7 + bits10–15） |
| fontbakery name 许可检查 | 源码 rationale | `googlefonts/name/license` 只接受 **OFL 1.1 / Apache 2.0 / Ubuntu Font Licence 1.0** 三种字符串片段；`microsoft/license_description.py` 只校验是否含特定 MS 许可文本 |
| fontspector `profile-universal/src/checks/` 下 `.rs` | 文件计数 | **79**（含 2 个 `mod.rs`）→ **77 个检查模块** |
| fontspector universal 中 `fs_type` 命中 | 内容 grep | **0** |
| fontspector universal 中检查文件名 `licen\|fstype\|embed\|subset` | 文件名 grep | **0** |
| fontspector 其它 profile 的 fsType 检查 | 内容 grep | `profile-fontwerk`（要求 Print & Preview = 4）、`profile-microsoft`、`profile-monotype`（与期望值比对）；**均无比对之外的语义解释** |

> ⬜ 上游记录（**本次窗口未复现，仅登记**）：fontbakery "323 个真检查 / 190 个厂商专属"、fontspector universal "74 个检查文件" —— 与本次实测不符，**以本表为准**（见 §七 更正记录）。

## 三、`fsType` 规范台账（✅ MS 规范原文核实：OpenType 1.9.1 `/typography/opentype/spec/os2` 与 `/spec/name`）

### 3.1 `fsType` 位定义（逐条对应规范原文）

| 位 | 掩码 | 规范原文要点 |
|---|---|---|
| 0–3 | `0x000F` | 用法权限位。合法值只有 **0 / 2 / 4 / 8**；原文 "Valid fonts must set at most one of bits 1, 2 or 3; **bit 0 is permanently reserved and must be zero**" |
| — | — | **0 = Installable**；**2 = Restricted License**；**4 = Preview & Print**（"Documents containing Preview & Print fonts must be opened 'read-only'"）；**8 = Editable** |
| — | — | **Restricted 生效条件（原文）**："For Restricted License embedding to take effect, the Embedding permissions sub-field must have the value **2** (that is, only bit 1 is set)." |
| 4–7 | `0x00F0` | "Reserved, must be zero." |
| 8 | `0x0100` | "No subsetting: When this bit is set, the font must not be subsetted prior to embedding. Other embedding restrictions specified in bits 0 – 3 and bit 9 also apply." |
| 9 | `0x0200` | "Bitmap embedding only: … only bitmaps contained in the font may be embedded. No outline data may be embedded." |
| 10–15 | `0xFC00` | "Reserved, must be zero." |

### 3.2 版本分流（**必须先读 `OS/2.version` 再判**）

| 版本 | 规范原文要点 | 判定口径 |
|---|---|---|
| **v0–v2** | "The specification for versions 0 to 2 did not specify that bits 0 to 3 must be mutually exclusive. Rather, those specifications stated that, in the event that more than one of bits 0 to 3 are set in a given font, then the **least-restrictive permission indicated take precedence**." | 多位并存 → **取最宽松者**；**不得报互斥违规** |
| **v3 及以后**（OpenType 1.4 起） | "The specification for version 3, added in OpenType 1.4, introduced the explicit requirement that bits 0 to 3 must be **mutually exclusive**." | 多位并存 → **必须报互斥违规** |
| 另（v0–1 附加） | "Applications must ignore bits 4 to 15 when reading a version 0 or version 1 table." | 保留位判定按版本分档 |

### 3.3 name ID 表（✅ `/spec/name` 原文）

| ID | 含义 | 与本题的关系 |
|---|---|---|
| 0 | Copyright notice | 元数据存活 |
| 7 | Trademark（原文强调 "distinctly separate from the copyright"） | 元数据存活 |
| 11 | URL of Vendor | 可追溯性 |
| **13** | **License Description**（"Description of the license or licenses under which the font is provided"） | **许可元数据闸门** |
| **14** | **License Info URL** | **许可元数据闸门** |
| 15 | Reserved | 保留标记 |
| 16 / 17 | Typographic Family / Typographic Subfamily（若缺失则回落 1 / 2） | 本地化家族名存活 |
| 21 / 22 | WWS Family / WWS Subfamily（与 `fsSelection` bit8 互为反相关） | 命名体系完整性 |
| 25 | Variations PostScript Name Prefix | 变量字体命名 |

### 3.4 PDF/UA-2 引文（**未核实**）

- ⬜ 曾有主张引用 **PDF/UA-2 §8.4.5.5.1 "legally embeddable"**；本次尝试访问 `pdfa.org` 返回 **403**，**未能独立核实原文**。→ 本仓库不得引用该条款文字，只可写"依 issue 报告（未核实）"。

## 四、子集实测七项台账（✅ 本机 fontTools 4.57.0；每项：命令 / 退出码 / 观察）

工作目录：临时目录（不写仓库）。输入取自只读系统字体或本机合成字体。

| # | 命令（节选） | 退出码 | 观察 |
|---|---|---|---|
| 1 | `pyftsubset C:\Windows\Fonts\arial.ttf --text="汉字abc" --output-file=a.ttf` | **0** | 输出 cmap = `{0x61, 0x62, 0x63}`；`U+6C49`(汉)、`U+5B57`(字) **静默消失**；日志仅 `WARNING: meta NOT subset; … dropped` |
| 2 | 同上 + `--no-ignore-missing-unicodes` | **1** | `fontTools.subset.MissingUnicodesSubsettingError: ['U+5B57', 'U+6C49']`；堆栈经 `fontTools/subset/__init__.py:3371`；**不产出输出文件** |
| 3 | 用 `TTFont` 读入 arial，置 `OS/2.fsType = 0x0108` 另存，再 `pyftsubset fs108.ttf --text="abc"` | **0** | 输出字体 `fsType = 0x0108` **原样保留**，子集照常完成 → **工具链默认违反 No-subsetting 声明** |
| 4 | `pyftsubset arial.ttf --text="abc" --layout-features='liga,kern'`；另跑默认与 `--layout-features='*'` 于 Calibri | 0 | Arial 原 **138 条 FeatureRecord / 25 个不同标签**；指定 `liga,kern` 后 **0 条**。**默认白名单实测 67 个标签**（`fontTools.subset.Options().layout_features`）。Calibri（原 276 条 / 34 个标签）默认子集保留 **4 个标签**（`dnom, frac, liga, numr`）+ GPOS `kern`；`--layout-features='*'` 保留 **18 个标签**。`ss01–ss08`、`cv01–cv14`、`case`、`aalt`、`tnum`、`zero` **不在默认集合内** |
| 5 | `pyftsubset calibri.ttf --text="fi"`；再用 `TTFont` 遍历 GSUB | 0 | `f+i` 连字**规则存活**且目标字形存在，但字形名由 `uniFB01` 变为 `glyph00003`（post 3.0，名称不保留）。**LookupType 7 解包验证**：Arial GSUB **92 个 Lookup 全为 Type 7**；朴素遍历连字规则 **0 条**，解包 `ExtSubTable` 后 **784 条**（`Arial`）、`Calibri` 原字体 **10119 条** |
| 6 | `pyftsubset C:\Windows\Fonts\msyh.ttc --font-number=0 --text="abc"`；对比原字体 `name` 表 | 0 | 原 nameID 集合 = `{0..14}`、**26 个 languageID**（1027–3084 等）→ 子集后 `{0,1,2,3,4,5,6}`、仅 `{1033}`。**nameID 13 / 14 被剥掉**；`Arial` 原含 13（无 14）→ 子集后仅 0–6 |
| 7 | `pyftsubset msyh.ttc --font-number=0 --text="汉字"`；读 OS/2 | 0 | 原 `ulUnicodeRange = [0x80000287, 0x2ACF3C50, 0x16, 0x0]`、`ulCodePageRange1 = 0x4001F` → 子集后 `ulUnicodeRange = [0x0, 0x8000000, 0x0, 0x0]`（**bit59 CJK Unified Ideographs 正确置位**）、`ulCodePageRange1 = **0x1** (Latin 1)`、`ulCodePageRange2 = 0x0`。→ **码页位声称 Latin-1，而 cmap 只含汉字 = 真实自相矛盾**；`usFirstCharIndex/usLastCharIndex = 0x5B57/0x6C49`；`maxp.numGlyphs = 3` = 实际字形数 |
| 7b | 对照：`pyftsubset InterVariable.ttf --text="Hello 汉字"`；读变化表 | 0 | `fvar`（**2 轴** opsz/wght、**9 个 instance**）、`STAT`（**3 轴**、**12 个 AxisValue**）、`avar`、`MVAR`、`HVAR`、`gvar` **全部保留** → fontTools 这块正确，**不构成本工具的发现面** |
| 7c | 合成：把某字体 `ulCodePageRange1/2` 置 0，再子集 `--unicodes=U+0061,U+0062` | 0 | `ulCodePageRange1` 由 0 变为 **0x1**（回退置 Latin-1）→ 回退逻辑在 `fontTools/ttLib/tables/O_S_2f_2.py::recalcCodePageRanges`，注释原文 "when no codepage ranges can be enabled, fall back to enabling bit 0 (Latin 1) so that the font works in MS Word" |

**默认值实测快照**（`fontTools.subset.Options()`）：`ignore_missing_unicodes=True`、`name_IDs=[0,1,2,3,4,5,6]`、`name_languages=[1033]`、`prune_unicode_ranges=True`、`prune_codepage_ranges=True`、`notdef_glyph=True`、`recalc_bounds=False`、`layout_features` 共 **67** 个标签。

**站点包 grep**：`site-packages/fontTools/subset/` 全树 `.py` 含 `fsType` 的文件数 = **0**（✅ 实测）→ 子集路径不读嵌入许可。

### 4.1 合成 fixture 实测（✅ 2026-10-21，fontTools 4.57.0 / 4.67.0 双通道）

| # | 事实 | 数值 | 验证方式 |
|---|---|---|---|
| 1 | F1 `0x0108` | `may_subset = (0x0108 & 0x0100) == 0` → **false**；`bits = 0x0008` → Editable | `tools/gen_fixtures.py` 生成期自证（独立 OS/2 解析，不经 fontTools 高层 API） |
| 2 | F2 `0x000E` + v0 | `bits = 0x000E`（3 位并存），`version = 0 ≤ 2` → 最宽松 = **8 Editable**；`may_subset = true`；**无互斥违规** | 同上 |
| 3 | F3 `0x000E` + v3 | 同上位值，`version = 3 ≥ 3` → **互斥违规**；最宽松仍是 Editable，两者独立成条 | 同上 |
| 4 | F2 vs F3 的真实差异 | **不是"只差一个字节"**：`OS/2.version`（0 vs 3）**加上** OS/2 表长（**78 B vs 96 B** —— `ulCodePageRange1/2` 自 v0 起才有，v0 表本身 78 B 已含）；`cmap` 与其余表逐字节一致 | `tests/test_fixtures.py::test_f2_and_f3_differ_only_in_os2_version_and_table_length` |
| 5 | F4 静默丢字 | 源 cmap = `{U+0061,U+0062,U+0063,U+5B57,U+6C49}`；只对 `abc` 子集后产物 cmap = `{U+0061,U+0062,U+0063}` → `LOST_IN_SUBSET = {U+5B57,U+6C49}`，`MISSING_IN_SOURCE = ∅` | 独立 cmap 位解析（format 4 手解）复算 |
| 6 | F5 元数据剥离 | 源 nameID = `{0..6,13,14}`、语言 = `{0,1033,1041}` → 产物 nameID = `{0..6}`、语言 = `{1033}` | 独立 name 表记录解析 |
| 7 | F6 码页矛盾 | 源 `ulCodePageRange1 = 0x4001F` → 仅 CJK 子集后产物 = **`0x1`**（Latin-1 回退）；产物 `ulUnicodeRange1 = 0x0` 而 `ulUnicodeRange2` bit59 置位（**正确重算，不构成矛盾**）；产物 cmap 无任何 `≤ U+00FF` 码位 | 独立 OS/2 + cmap 解析 |
| 8 | 跨 fontTools 版本产物一致性 | **4.57.0 与 4.67.0 生成的 6 组 fixture 二进制逐字节相同**（唯一差异是 `expect.json` 里记录的版本串） | `py tools/gen_fixtures.py --check` 在两条通道各跑一次 |
| 9 | 确定性（禁时钟） | `FontBuilder` 默认把 `head.created/modified` 设为**当前时钟**（实测：间隔 1.2 s 两次生成 → 字节不同）；`subset` 的 `TTFont.save` 默认 `recalcTimestamp=True` 会再改一次 | 实测对照：钉死 `FIXED_EPOCH = 3155673600` 后两次生成逐字节一致 |
| 10 | 五元结论（M2） | F1/F2/F3 各五条结论与 §六.1.3 的判定式逐项一致：F1 `{pdf:T, app:F, web:F, subset:F, modify:T}`；F2/F3 均为 `{T, F, T, T, T}`（**F2 与 F3 的五元结论完全相同**，差别只在违规条） | `tools/gen_fixtures.py::_oracle_conclusions` 独立复算（不复用被测实现）+ `tests/test_license_gate.py` 逐项 |
| 11 | 违规码覆盖完备性 | `bits ∉ {0,2,4,8}` 的**全部**取值都被现有两条码覆盖：含 bit0 的由 `FSTYPE_BIT0_RESERVED` 抓；不含 bit0 的其 bits1–3 必 ≥2 位（`0x0006/0x000A/0x000C/0x000E`）→ v3+ 由互斥码抓、v0–v2 由"取最宽松"吸收 | §六.1.5 的可证推导；`tests/test_license_gate.py::test_permission_names_cover_exactly_the_four_legal_values` |
| **12** | **三个 OFL 字体都没有 Extension lookup（GSUB 无 Type 7，GPOS 无 Type 9）** | GSUB：`NotoSansSC` 15 / `NotoSans-Bold` 46 / `InterVariable` 90 个 lookup，**Type 7 = 0**；GPOS：10 / 9 / 10 个 lookup，**Type 9 = 0**。故这 3 个字体上 `naive == raw`（见 §六.5.2） | `TTFont(lazy=True)` 只读遍历；`tests/test_layout_survival.py` 的真实字体回归 |
| **13** | **商用字体的 Extension 只作只读观察**（Arial / Calibri，**不复制、不入库、不可复现**） | `arial.ttf` GSUB：**92 个 lookup 全为 Type 7**、解包后 **196** 个子表、连字规则 **naive=0 / 解包后=784**；GPOS：134 个 lookup **全为 Type 9**、332 子表。`calibri.ttf` GSUB：296 个 Type 7、538 子表、规则 **naive=0 / 解包后=10119**；GPOS：254 个 Type 9、560 子表 | 本机只读 `TTFont(lazy=True)` 一次遍历（`_scratch` 原型，不入仓）；**仓库内以合成字体同构复现**（表 14） |
| **14** | **合成字体上 `naive=0 / 解包后=1` 可复现**（替代商用字体那组对照） | `_scratch/src_ext.ttf`（程序合成，3 lookup / 3 字形）：把 `liga` 与 `ss01` 两条 lookup 包成 Type 7 → GSUB 外层 `{7:2, 1:1}`、`ExtensionLookupType` 解包出 `{1:1, 4:1}`；连字规则 **naive = 0、解包后 = 1**；`layout_features='*'` 保留 2 条三元组、默认保留 1 条、`''` 保留 0 条 | `tests/test_layout_survival.py::test_naive_count_is_zero_only_when_extension_is_not_unwrapped` 等（测试内合成，落 `tmp_path`） |

> **推论（写进 HANDOFF-M2）**：`expect.json` 的 `fonttools_version` 必须记录**铸造时的版本**（常量
> `GOLDEN_FONTOOLS_VERSION`），不能写运行时版本 —— 否则 3.8（4.57.0）与 3.12（4.67.0）两条 CI 通道的
> `--check` 会在彼此生成的 golden 上互相判红，而二进制其实完全一样。

## 五、本机系统字体 fsType 分布（✅ 只读实测）

**扫描范围**：`C:\Windows\Fonts\*.ttf` + `*.otf`，**共 560 个字体（face）**；其中 1 个文件（`mstmc.ttf`）`bad sfntVersion` 无法解析，已排除。**`.ttc` 集合字体未计入**（若把每个 ttc 第 1 个 face 计入则为 575 个，口径不同，勿混用）。

| `fsType`（bits0–3 值） | face 数 | 说明 |
|---|---|---|
| `0x0008` Editable | **332** | — |
| `0x0001`（仅 bit0，保留位被置位） | **102** | 保留位置位（非法/历史遗留） |
| `0x0000` Installable | **67** | — |
| `0x000E`（2+4+8 三位并存） | **40** | OS/2 **v0: 39 个，v1: 1 个** → **v3+ 为 0** |
| `0x0004` Preview & Print | **15** | — |
| `0x0002` Restricted License | **3** | 全部 OS/2 **v1** |
| `0x0003`（bit0 + bit1） | **1** | OS/2 **v0** |

**派生（口径见 §六）**：

| 指标 | 数值 | 口径 |
|---|---|---|
| 保留位 bit0 置位 | **103 / 560** | `fsType & 0x0001`（= 0x0001 的 102 + 0x0003 的 1） |
| bits0–3 中 ≥2 位同时置位 | **41 / 560** | = 0x000E 的 40 + 0x0003 的 1；**v3+ 为 0** |
| 其中"权限位（bits1–3）多位置位" | **40 / 560** | 仅 0x000E（0x0003 只置了 bit1 一个权限位）；v0 39 + v1 1 |
| bits0–3 取值非法（∉{0,2,4,8}） | **143 / 560** | = 0x0001(102) + 0x0003(1) + 0x000E(40) |
| **严格 Restricted**（bits0–3 == 2） | **3 / 560（0.54%）** | 规范性判定 |
| **按版本分流后受限**（取最宽松） | **4 / 560（0.71%）** | 3 个 0x0002 + 1 个 0x0003（后者仅 bit1） |
| 表面含 bit1（若不做版本分流） | **44 / 560（7.86%）** | = 0x0002(3) + 0x0003(1) + 0x000E(40) → **40 个 0x000E 在 v0/v1 下应解析为 Editable**，这是"不做版本分流就会误报"的实例 |
| bit8 No-subsetting（`0x0100`） | **0 / 560** | — |
| bit9 Bitmap-only（`0x0200`） | **0 / 560** | — |
| 缺 nameID 13 | **336 / 560** | — |
| 缺 nameID 14 | **370 / 560** | — |

> **不可外推声明**：以上是**本机 Windows 系统字体池**的只读统计，**不是随机样本**，也不代表任何发行版、任何用户群或任何商业字体库的分布。**不得**把"bit8 在本池中为 0"读作"下游不需要 No-subsetting 闸门"——本池恰恰说明：**真实闸门是受限/保留位/元数据缺失（约 60% 字体缺 nameID 13），而 No-subsetting 在系统字体里几乎不出现**；把重心全押在"拒绝 No-subsetting"上会打空，因此 M1 必须同时覆盖 Restricted、保留位与元数据三类。

### 5.1 M2 实现回填：真实字体池复跑（✅ 2026-10-21，只读）

用交付实现 `license_gate.evaluate()` 对 `C:\Windows\Fonts` 的 `*.ttf` + `*.otf` 逐个 open/close 复跑
（**不写任何文件**）：**560 个 face 成功判定，1 个 `mstmc.ttf` 报 `not_an_sfnt_font`**
（`canonical.InputError` → 退出码 2，**不猜**）—— 与 §五 的"560 face，`mstmc.ttf` 已排除"同一口径。

| 检查项 | 实测 | 与 §五 预测的一致性 |
|---|---|---|
| 权限位含 `0x000E` / `0x0003` / `0x0002` 的 face | **44** | ✅ = 0x000E 40 + 0x0003 1 + 0x0002 3 |
| 报 `FSTYPE_MUTUAL_EXCLUSION` 的 | **0** | ✅ 44 个多位并存**全部**落在 v0/v1 → **零误报**；F2 的反例守护在真实池上成立 |
| 解析为 Editable 且 `least_restrictive` 的 | **40** | ✅ 与派生行"40 个 0x000E 在 v0/v1 下应解析为 Editable"一致 |
| 报 `FSTYPE_RESTRICTED_LICENSE` 的 | **4** | ✅ 与"按版本分流后受限 4/560（0.71%）"一致 |
| 报 `FSTYPE_BIT0_RESERVED` 的 | **103** | ✅ 与"保留位 bit0 置位 103/560"一致 |
| 报 `FSTYPE_NO_SUBSET` / `FSTYPE_BITMAP_ONLY` / `FSTYPE_RESERVED_BITS` 的 | **0 / 0 / 0** | ✅ 与 §五 bit8=0、bit9=0 一致；bits4–15 在本池确实无人置位 |

> 意义：**§五 数的是"位模式"，§5.1 跑的是"交付实现的输出"** —— 两条独立路径得出同一组数字，
> 说明实现与台账口径没有分叉。**仍未验证**：`.ttc` 集合字体（§五 未计入，本表也未计入）、
> 以及非 Windows 字体池的分布（本表**不可外推**，理由同 §五 的不可外推声明）。

### 5.2 M3 实现回填：真实 OFL 字体上的 pdfcraft#381 指纹（✅ 2026-10-21）

用交付实现 `coverage_diff.evaluate()` 在 `data/fonts/NotoSansSC-Regular.otf`（OFL 1.1，§八锁文件）
上复现"按词表切"的指纹。构造：源 = 该字体；产物 = `fontTools.subset` + `--text="字段列表保存全部页面区块删除"`
（**只写 `_scratch/`，不入仓**）；需求集 = `plan/01` §三 M2 验收② 的 29 个汉字。

| 项 | 实测 |
|---|---|
| 需求集 | 29 个码位（BMP 29） |
| `OK` | **6** —— `全 删 区 块 存 页`（词表与 29 字的交集） |
| `LOST_IN_SUBSET` | **23** —— 其余（`划务单图处导护旋码离突签线绪获账转选释钮需顺馈` 等） |
| `MISSING_IN_SOURCE` | **0** —— Noto Sans SC 覆盖全 29 字 |
| `severity` | 23 条全部 `error`（`LOST_IN_SUBSET` 恒 `error`） |
| `fallback_hint` | `BMP: lost=23, subset_available_in_block=14` |
| cmap 选表 | 源 `(3,10)/format 12`（**30,890** 项）→ 产物 `(3,1)/format 4`（**14** 项） |

> 意义：这条指纹**不依赖任何商用字体**即可复现，且与 `plan/01` 记录的原始现象同构
> （高频词表字在、中频专业字缺）。测试 `tests/test_coverage_diff.py::test_pdfcraft_381_fingerprint_on_real_ofl_font`
> 在字体未下载时**显式 skip**（不假装跑过）。**不可外推**：这是**一个** OFL 字体 + **一个**词表的
> 单次观察，不是"词表子集普遍如此"的统计结论。

## 六、数值口径（**一处定义**）

1. **`fsType` 判定（先版本分流，再五元结论）** —— 本节是 `license-gate` 的**唯一**判定来源；
   代码里的 `SPEC_REFS` 常量必须逐字复制 1.3 / 1.4 两表的字面量（有测试按表解析对账）。

   **1.1 解析顺序（不可调换）**：① 读 `OS/2.version` → ② `bits = fsType & 0x000F` →
   ③ 版本分流得 `perm`（1.2）→ ④ 读 bit8 / bit9 / 保留位 → ⑤ 由 `perm` + bit8 + bit9 推五元结论（1.3）。
   **五元结论全部基于解析后的 `perm`，不基于原始位串** —— 这是"不做版本分流就会误报"的落点。

   **1.2 `perm`（权限位解析值）**

   | 条件 | `perm` | `permission_resolution` | 依据（§3.2 原文） |
   |---|---|---|---|
   | `bits` 中 bits1–3 恰有 1 位置位 | 该位的值（2 / 4 / 8） | `direct` | 合法值只有 0/2/4/8 |
   | `bits` 中 bits1–3 全为 0（`bits ∈ {0x0000, 0x0001}`） | `0`（Installable） | `direct` | 值 0 = Installable；bit0 另按 1.4 单列 |
   | `version ≤ 2` 且 bits1–3 有 ≥2 位 | **最宽松者**（序 8 > 4 > 2） | `least_restrictive` | "the least-restrictive permission indicated take precedence" |
   | `version ≥ 3` 且 bits1–3 有 ≥2 位 | **最宽松者**（同上，仍解析） | `least_restrictive` | v3+ 互斥为强制；解析值照旧取最宽松，**违规独立成条**（1.4） |

   **1.3 五元结论（每条一个判定式 + 一个 `spec_ref` 字面量）**

   | 结论键 | 判定式（`perm` = 1.2 的解析值） | `spec_ref`（逐字使用） | 规范原句要点（§3.1） |
   |---|---|---|---|
   | `embed_pdf` | `perm != 2 and (fsType & 0x0200) == 0` | `MS-OS2 §fsType bits0-3 (0/4/8 allow document embedding)` | 0/4/8 均允许"embedded"进文档；2 须先取得明示许可；bit9 置位时"only bitmaps … may be embedded. No outline data may be embedded" → PDF 内嵌轮廓不成立 |
   | `embed_app` | `perm == 0 and (fsType & 0x0200) == 0` | `MS-OS2 §fsType value 0 (permanent installation)` | 只有值 0 允许"permanently installed for use on remote systems, or for use by other users"；4/8 只允许"temporarily loaded"（随应用分发 = 永久安装/供他人使用） |
   | `embed_web` | `perm != 2 and (fsType & 0x0100) == 0 and (fsType & 0x0200) == 0` | `MS-OS2 §fsType bits0-3 + bit8 (temporary loading for viewing, no subsetting)` | Web 字体 = "temporarily loaded … for purposes of viewing" **且** 交付前通常要子集 → bit8 "must not be subsetted prior to embedding" 与 bit9 轮廓禁令同时生效 |
   | `may_subset` | `(fsType & 0x0100) == 0` | `MS-OS2 §fsType bit8 (No subsetting)` | bit8 原文只限制**子集**，不限制嵌入本身（故 bit8 置位时 `embed_pdf` 仍可为 true） |
   | `may_modify` | `perm in (0, 8)` | `MS-OS2 §fsType bits0-3 (editing permitted / read-only)` | 8 = "editing is permitted … changes may be saved"；4 = "Documents … must be opened 'read-only'; no edits may be applied"；2 = "must not be modified"；0 = 用户取得与原购买者"identical rights" → `fsType` 不构成编辑限制 |

   > **`may_modify` 的边界（必须照此措辞，不得扩写）**：该键只回答"`fsType` 是否禁止**文档/产物**被编辑或保存"，
   > **不回答**"是否授予修改字体软件本身的权利"。`fsType` 是嵌入许可位，不是字体软件的再授权条款；
   > 报告与文案不得据此写"可以改这个字体"。

   **1.4 违规码（finding code → 级别 → `spec_ref`）** —— 只此六条，不另立

   | `code` | 触发条件 | 级别 | `primary_key` | `spec_ref`（逐字使用） |
   |---|---|---|---|---|
   | `FSTYPE_BIT0_RESERVED` | `fsType & 0x0001` | `error` | `bit0` | `MS-OS2 §fsType bit0 (permanently reserved)` |
   | `FSTYPE_RESERVED_BITS` | `fsType & 0xFCF0`（bits4–7 + bits10–15） | `version ≤ 1` → `warn`；`version ≥ 2` → `error` | `bits4-15` | `MS-OS2 §fsType bits4-7/bits10-15 (reserved)` |
   | `FSTYPE_MUTUAL_EXCLUSION` | `version ≥ 3` 且 bits1–3 有 ≥2 位 | `error` | `bits0-3` | `MS-OS2 §fsType (v3+ mutually exclusive)` |
   | `FSTYPE_NO_SUBSET` | `fsType & 0x0100` | `error` | `bit8` | `MS-OS2 §fsType bit8` |
   | `FSTYPE_BITMAP_ONLY` | `fsType & 0x0200` | `warn` | `bit9` | `MS-OS2 §fsType bit9 (Bitmap embedding only)` |
   | `FSTYPE_RESTRICTED_LICENSE` | `perm == 2` | `warn` | `bit1` | `MS-OS2 §fsType value 2 (Restricted License)` |

   **1.5 为什么"取值非法（∉{0,2,4,8}）"不另立第三条码（可证）**：设 `bits = fsType & 0x000F`。
   若 `bits ∉ {0,2,4,8}`，则二选一 —— ① `bits` 含 bit0（`0x0001`/`0x0003`/`0x0005`/…）→ 由
   `FSTYPE_BIT0_RESERVED` 覆盖；② `bits` 不含 bit0 且 ∉{0,2,4,8} → 其 bits1–3 必置 ≥2 位（`0x0006`/`0x000A`/`0x000C`/`0x000E`）
   → v3+ 由 `FSTYPE_MUTUAL_EXCLUSION` 覆盖、v0–v2 由 1.2 的"取最宽松"**吸收**（这正是 F2 的守护点）。
   两条码并集 ⊇ 全部非法值，故不得再加第三条码（加了就会出现 F3 双报，打挂 golden）。

   **1.6 保留位与版本**：`0xFCF1` = bit0 + bits4–7 + bits10–15（与 fontbakery 的 `0b1111110011110001` 一致，§二）。
   1.4 把 bit0 与 bits4–15 **拆成两条码**：bit0 在任何版本都是"permanently reserved"（含 v0，§3.1 末段），
   而 bits4–15 在 v0/v1 下规范要求"Applications must ignore bits 4 to 15"（§3.2 第三行）→ 故 v0/v1 降为 `warn`。
2. **覆盖三分类** —— 本节是 `coverage-diff` 的**唯一**判定来源。
   记号：需求字符集（输入原文）`R0`；闭包后的需求集 `R`（见 **2.1**，三分类**只用 `R0`**）；
   原字体 Unicode cmap 覆盖集 `S`；子集字体 Unicode cmap 覆盖集 `T`。

   | 分类 | 判定式 | 级别 | `primary_key` | `spec_ref`（逐字使用） |
   |---|---|---|---|---|
   | `MISSING_IN_SOURCE` | `R0 \ S` | **默认 `warn`**；`--strict-source` → `error` | `U+XXXX` | `data/README §6.2` |
   | `LOST_IN_SUBSET` | `(R0 ∩ S) \ T` | 恒 `error` | `U+XXXX` | `data/README §6.2` |
   | `OK` | `R0 ∩ S ∩ T` | 不产 finding（只进 `summary.coverage.OK`） | — | — |

   - **`--strict-source` 的语义**：只把 `MISSING_IN_SOURCE` 的级别由默认 `warn` 提升为 `error`
     （原文缺字才让退出码变 1）。它**不改变**三分类归属、不改变 `LOST_IN_SUBSET` 的级别、不加新码。
     默认 `warn` 的理由：本工具审的是**产物**，原文缺字是语料/源字体的问题，不该默认把流水线判红。
   - **finding 粒度**：每个码位一条；`primary_key = "U+%04X"`（大写、至少 4 位）；
     多码位时按码位升序（`canonical.sort_findings` 的 `primary_key` 字符串序与之相容）。
     证据键固定为 `{"codepoint", "block", "source_covered", "subset_covered"}`。
   - **glyph0 命中不计入覆盖**：映射到 `.notdef`（`cmapset.NOTDEF_NAMES`）的码位视为缺。
   - **单字体模式**（未给 `--subset`）：`T` 不参与 → `LOST_IN_SUBSET = ∅`，`OK = R0 ∩ S`，
     `MISSING_IN_SOURCE = R0 \ S`（级别同上）；`summary.coverage.LOST_IN_SUBSET` 为空列表。

   **2.1 组合字符闭包（NFC/NFD）** —— 范围 / 方向 / `added` 定义

   | 项 | 口径 |
   |---|---|
   | 范围 | 只对 `R0` 里的**单个码位**各自做规范化；不做整段文本的上下文规范化（不做 Hangul 组合串、不做 shaping） |
   | 方向 | **双向**：`NFD`（分解）与 `NFC`（合成）各取一次，结果里的**每个字符**都并入闭包集 `C`（含原码位自身） |
   | 深度 | **单层**：对新增码位不再递归展开 |
   | `added` | `added = C \ R0`，码位升序；`closed = C` |
   | 计数落点 | `summary.closure = {"added": [...], "added_codepoints": n, "missing_in_source": m, "lost_in_subset": k}`；`missing_in_source = |added \ S|`、`lost_in_subset = |(added ∩ S) \ T|`（无 `--subset` 时恒 0） |
   | 是否产 finding | **否**：闭包新增码位**只计数**，不产 `error`/`warn` —— 用户没要求的组合符不该把退出码判红；三分类仍只用 `R0` |

   **2.2 回退链建议（`summary.fallback_hint`）** —— 纯建议，**不参与任何判定**：

   | 项 | 口径 |
   |---|---|
   | 触发 | 仅当 `LOST_IN_SUBSET` 非空且给了 `--subset`；否则为空列表 `[]` |
   | 分组 | 按 §六.4 的 `block_of`（互斥分区）归组被丢码位 |
   | 每项字段 | `{"block": 块名, "lost": 该块被丢码位数, "subset_available_in_block": 产物在该块里**真实覆盖**的码位数}` |
   | 排序 | 按 `block` 名字符串升序（确定性） |
   | 禁止 | **不得**据此改级别、加 finding、或推断"换个子集就好了"——它只是"该块里产物还有多少可提供的字" |

3. **cmap 编码优先级**：`(3,10) → (0,4) → (3,1) → (0,3)`；多个同优先级子表同时存在时取并集，
   并在报告里列各子表的项数（`summary.cmap.*_chosen` = `[platform, encoding, format, count]` 列表，
   `summary.cmap.*_subtables` 同理，含未被选中的子表）。

   **取不到 Unicode cmap 的失败路径（两条理由不得合并）**：

   | 情形 | 输出 | 退出码 | 报告里**不得**出现 |
   |---|---|---|---|
   | 根本没有 `cmap` 表 | `SKIPPED(reason=no_cmap_table)` | 0 | 任何三分类结论（尤其"覆盖为空 = OK"） |
   | 有 cmap 表但没有 Unicode 子表（如仅 `(1,0)`/format 0） | `SKIPPED(reason=no_unicode_cmap)` | 0 | 同上 |
   | 给了 `--subset` 但**产物**取不到 Unicode cmap | 同上两条理由之一，`detail` 以 `subset:` 开头 | 0 | 同上（整份报告不产三分类，而不是只算源侧） |

   两条理由的 `detail` 以 `source:` / `subset:` 开头，指明是哪一侧；**任一输入取不到 Unicode cmap
   → `summary` 为空**（不猜、不给半份结论）。
4. **分区计数**：**互斥分区，按此优先级判定**（先命中者胜）——
   `ExtA` = `U+3400–U+4DBF` → `ExtB+` = `U+20000–U+2FA1F` → `BMP` = 其余 `U+0000–U+FFFF` → `other`。
   **ExtA 必须先于 BMP 判**：Ext A 的码位本身就落在 `U+0000–U+FFFF` 内，若先判 BMP 则 ExtA 永远为 0
   （M3 实现时实测踩到，`U+3400` 曾被算进 BMP）。四块之和恒等于码位总数。
5. **布局保真（`layout-survival`）** —— 本节是 `layout-survival` 的**唯一**判定来源；代码里
   `SPEC_REF = "data/README §6.5"` 是逐字副本（有测试解析本节做对账）。
   记号：源字体表 `T_src`、产物字体表 `T_out`（各自对 `GSUB` / `GPOS` 各取一次，**两表分开成条**）。

   **5.1 三元组枚举规则（`LangSysTag` 的三种取值与去重）**

   | 项 | 口径 |
   |---|---|
   | 三元组形状 | `(TableTag, ScriptTag, LangSysTag, FeatureTag)`；`TableTag ∈ {GSUB, GPOS}` —— **GSUB 与 GPOS 必须分开成条**（同一 Script/LangSys/Feature 在两张表里是两条不同的事实，不得合并） |
   | `LangSysTag` 取值 | ① `Script.DefaultLangSys` 非空 → 记一条 `"dflt"`；② `Script.LangSysRecord` 的每条 `LangSysTag` **原样**（4 字符，含尾部空格，如 `"ZHS "`）；③ 某 feature 在该 script 下的**全部** langsys（含 `dflt`）都出现时，额外记一条 `"all"` |
   | `"all"` 与具体标签的关系 | `"all"` 是**附加**的聚合条，**不替代**具体标签：该 feature 同时在 `(script,"dflt",feat)` 等具体条目上存在。故 `"all"` 条数 = 该 script 下"全 langsys 共有的 feature"个数 |
   | 去重 | 按四元组精确去重（同一 feature 被多个 `FeatureIndex` 指向同一 `FeatureTag` 时只记一条 —— 真实字体常见：`aalt` 在 NotoSansSC 有 11 条 FeatureRecord） |
   | 空 Script | `ScriptList` 为空 → 该表不产三元组（不是"全部丢失"） |
   | 排序 | `(TableTag, ScriptTag, LangSysTag, FeatureTag)` 字典序；`primary_key` 拼成 `"GSUB/hani/ZHS /liga"` 形态 |
   | `FeatureVariations` | **不参与三元组枚举**。`FeatureVariationRecord` 的替代 FeatureTable 是"条件满足时换一套 lookup"的**运行时**分支，不是独立 feature；本工具只报 `summary.layout.*.feature_variations` 的**记录数**（源/产物各一），差异**不产 finding**（理由：无法只凭表结构判断该条件是否落在用户的使用域内） |

   **5.2 子表计数（`raw` / `kept` / `naive`）与 LookupType 解包**

   | 计数 | 定义 | 用途 |
   |---|---|---|
   | `subtables_raw` | **该侧**解包后的逻辑子表总数 = 每个 Extension 包装记**被包裹的真子表** 1 条 | 结论用 |
   | `subtables_naive` | **该侧**不展开 Extension 时**可见**的子表数 = 只数非 Extension lookup 的 `SubTable`；**Extension 包装本身不计**（朴素遍历看不到里面的真子表，把它记成 1 会虚增） | **只作对照，不作结论** |
   | `ligature_rules_raw` | **该侧**解包后 `LigatureSubst` 的**规则**总数 = `Σ Σ len(LigatureSet.Ligature)` | 结论用 |
   | `ligature_rules_naive` | **该侧**不展开 Extension 时可见的 `LigatureSubst` 规则数（Extension 里的规则**一条都看不到**） | **只作对照** |
   | `triples_kept` | **跨两侧**：源侧四元组里能在产物侧找到的个数 = `|T_src ∩ T_out|` | 结论用（"保住了多少"） |
   | `triples_lost` | **跨两侧**：`|T_src \ T_out|` | 结论用（= `LAYOUT_FEATURE_LOST` 的条数） |

   > **三个计数分开报**（`raw` / `kept` / `naive`）的口径：`raw` 与 `naive` 是**单侧**的结构量（`source.gsub.*` /
   > `subset.gsub.*` 各自一份），`kept` 是**跨两侧**的结论量（`summary.layout.kept.triples`）。
   > 三者的分母不同，**不得相除**当作"保留率"（`raw` 数子表、`kept` 数四元组）。

   - **`LookupType 7`（GSUB Extension Substitution）** 与 **`LookupType 9`（GPOS Extension Positioning）**
     都必须解包：外层 lookup 的 `SubTable` 是 `ExtensionSubst` / `ExtensionPos`，真子表在 `ExtSubTable`
     字段里，真实类型写在 `ExtensionLookupType`。**只解 7 不解 9 是缺陷**（GPOS 侧会整段读不到）。
   - `naive` 恒 ≤ `raw`；两者相等 ⇔ 该表没有 Extension（三个 OFL 字体即此情形，见 §四.1 #12）。
   - 解包后按**真实类型**统计 **子表** 直方图 `subtable_type_histogram`（键 = 解包后真实类型号；
     Extension 的键取 `ExtensionLookupType`），**不按外层号**统计。注意粒度是**子表**不是 lookup：
     一个 lookup 可有多个子表（`NotoSans-Bold` GSUB 有 4 个 Type 6 lookup 共 6 个子表）。

   **5.3 判定式（丢失 / 改名 / 全量丢失）**

   | finding 码 | 判定式 | 级别 | `primary_key` | `spec_ref` |
   |---|---|---|---|---|
   | `LAYOUT_FEATURE_LOST` | `T_src \ T_out`（四元组差集） | 恒 `error` | `"<TABLE>/<script>/<langsys>/<feature>"` | `data/README §6.5` |
   | `LAYOUT_LIGATURE_LOST` | 见 5.4 的规则差分 | 恒 `error` | `"<TABLE>/<script>/<langsys>/<feature>"`（规则归属的三元组） | `data/README §6.5` |
   | `LAYOUT_LIGATURE_RENAMED` | 见 5.4 的"改名"分支 | 恒 `warn` | 同上 | `data/README §6.5` |

   - **`LAYOUT_FEATURE_LOST` 的粒度**：每个四元组一条。若产物**整张表都没了**（`T_out` 无该表），
     仍按源侧四元组逐条报 —— "全量丢失"就是差集的特例，**不另立码**（去重靠四元组集合）。
   - **默认丢弃标签**不是本工具的判定：`pyftsubset` 的默认白名单由 `fontTools.subset.Options().layout_features`
     决定（4.57.0 = **67** 个、4.67.0 = **68** 个，差 `palt` —— §四.1 #13）。本工具只**列出**产物上确实
     消失了哪些三元组，**不判断**"这个标签该不该丢"。

   **5.4 连字规则判定（`涉及必需字符` 的判定式）**

   **规则键 = 输入码位序列**（不是字形名，也不是 GID 数值）：

   ```
   lig_rule_key = tuple(码位 of first, 码位 of component_1, ...)   # 只含**输入**字形
   ```

   - **为什么不能用字形名**：`pyftsubset` 默认 `glyph_names=False` → 产物 post 表降到 **3.0**，
     名称全部丢失；fontTools 读入时按 GID **合成占位名** `glyph%05d % gid`（实测：gid 3 → `glyph00003`）。
     拿名字比对，会把"连字仍生效"误判成丢失。
   - **为什么不能用 GID 数值**：子集重排字形顺序（`junk1` 之类的未用字形被删 → 后面全部前移）；
     两侧 GID 空间不同。
   - **为什么输入侧可用码位**：输入字形**都有 cmap 映射**（它们是被用户敲出来的字符），cmap 在子集里保留
     → 反查稳定。规则键只取输入字形，**目标字形不参与键**（连字目标通常没有 cmap 映射）。
   - **`涉及必需字符`**：规则的**全部输入码位**都要在 cmap 反查里取到，且与需求字符集 `R0` 非空相交。
     `layout-survival` 子命令**没有 `--text`**（CLI 面已定，见 `plan/03` §4）→ 实际取**全体**连字规则
     （等价于不过滤），并在 `summary.layout.ligature_scope` 写 `"all"` 显式说明（**不假装过滤过**）。
     取不到某个输入码位 → 该规则**跳过**（无法建立跨字体同一性，不猜）。
   - **差分方向（LOST 与 RENAMED 互斥，先判 LOST）**：
     - 源侧的 `lig_rule_key` 在产物侧**不存在** → **`LAYOUT_LIGATURE_LOST`**（`error`）；
     - 存在 → 再判**改名**：记 `name_state(glyph, gid)` = `placeholder` ⇔ 该名字恰好等于
       `"glyph%05d" % gid`（即 fontTools 的占位名），否则 `named`。
       **`LAYOUT_LIGATURE_RENAMED`**（`warn`）触发条件：源侧目标 `named` 而产物侧目标 `placeholder`，
       **或**两侧都 `named` 且名字不同。两侧都 `placeholder` **不算**改名（名字两侧都没了，不是"改名"）。
       语义：**连字仍生效，但目标字形在产物里没有稳定名字** —— 这正是 `uniFB01 → glyph00003` 这一实测事实，
       报 `warn` 而非 `error`（功能未失效，只是可追溯性下降）。

   **5.5 失败路径（两条理由不得合并）**

   | 情形 | 输出 | 退出码 | `summary` |
   |---|---|---|---|
   | 两侧**都没有** `GSUB` 且都没有 `GPOS` | `SKIPPED(reason=no_layout_tables)` | 0 | 空（不猜） |
   | 只有一侧有布局表 | 照常判定 + `SKIPPED(reason=layout_tables_missing_on_one_side)`，`detail` 以 `source:` / `subset:` 开头 | 0（除非差集产 `error` → 1） | **非空**：有一侧的表就是可判定的事实，"全量丢失"由差集自然得出，**不因缺表而整份放弃** |

   - 只缺 `GSUB` 而 `GPOS` 两侧都有 → **不是**失败路径：`GSUB` 侧按"源有产物无"判全量丢失，
     `GPOS` 侧照常比对。`summary.layout.source.gsub` / `.gpos`（及 `.subset.*`）各带 `present: bool`。

   **5.6 落地约束（"同一规则"怎么比、`primary_key` 形态）**

   - 「同一规则」= **输入码位序列相同**（5.4 的 `lig_rule_key`）；两侧各算一次反查，
     **不比较字形名、不比较 GID 数值**。这不是第二条口径，只是 5.4 规则键的实施方式。
   - 同一 `lig_rule_key` 在一侧出现多次（重叠规则）→ 取**首次**（`LigatureSet.Ligature` 按优先级排序，
     首次 = 最高优先级，与规范一致）。
   - 连字规则的 `primary_key` = `"<TableTag>/<FeatureTag>/<U+xxxx>+<U+xxxx>"`；`FeatureTag` 取
     "含连字 lookup 的 feature 标签集合"里的 `liga`（若有），否则字母序最小者，再否则 `"-"`。
   - **层级关系**：连字规则丢失**不抑制** `LAYOUT_FEATURE_LOST` —— 两者是不同粒度的事实
     （`liga` 三元组可能整体还在，但某条具体规则没了）；`primary_key` 前缀不同，不会撞键。
6. **退出码**：`0` 通过；`1` 有发现（`error` 级 finding）；`2` 输入非法（文件不可读 / 非字体 / 缺必需参数 / JSON 反序列化失败）。`SKIPPED(reason=...)` 恒为**不影响退出码**的 `note`。
7. **fixture 名表**：`F1 fstype-nosubset`（0x0108）、`F2 fstype-multibit-v0`（0x000E + v0，**反例守护**）、`F3 fstype-multibit-v3`（0x000E + v3）、`F4 silent-drop`、`F5 metadata-stripped`、`F6 codepage-mismatch`。**F7 不入仓**：布局对照用**测试内合成字体**（落 `tmp_path`），理由见 §四.1 #14。
8. **确定性**：所有排序键固定（finding：`module, severity, 主键`；字符集：码位升序；布局三元组：`TableTag, ScriptTag, LangSysTag, FeatureTag`）；报告不含时间戳/绝对路径/主机名/用户名；同一输入两次运行逐字节一致。

## 七、更正记录（题面初稿 → 实测）

| # | 初稿主张 | 实测结果 | 处置 |
|---|---|---|---|
| 1 | fontbakery "373 个 .py、去掉 utils 后 323 个真检查，190 个厂商专属" | `.py` 373（含 45 个 `__init__.py`）；`@check` **320**；`vendorspecific` **157**；当前树无 `checks/utils` 目录 | 以实测为准（§二） |
| 2 | fontspector universal "74 个检查文件" | `.rs` **79**（含 2 个 `mod.rs`）→ **77** 个检查模块 | 以实测为准（§二） |
| 3 | "msyh 子集后 `ulUnicodeRange1` 由 0x80000287 → 0x0，位域声称不支持任何 Unicode 块，与实际覆盖矛盾" | `ulUnicodeRange2` **bit59 已正确置位**（CJK Unified Ideographs）；`ulUnicodeRange1 = 0` 是正确重算结果 → **不构成矛盾**（若照初稿实现将产生**假阳性**） | **改写 M4 验收**：真实矛盾点 = `ulCodePageRange1` 回退置 **0x1 (Latin 1)** 而 cmap 无 Latin-1 字符（§四 #7、#7c） |
| 4 | 保留位掩码 "`0b1111110011110001`（= 0xF071）" | `0b1111110011110001` = **0xFCF1**（bit0 + 0x00F0 + 0xFC00） | 更正为 0xFCF1（§三 3.1、§六 1） |
| 5 | "Inter 子集后 STAT 3 轴 17 值" | Inter 4.1 `InterVariable.ttf`：`fvar` **2 轴**、**9 instance**；`STAT` **3 轴**、**12 个 AxisValue** | 以实测为准（§四 #7b） |
| 6 | pdfcraft#381 视为在办（open） | 实测 **closed**（2026-10-08 开、2026-10-16 关，6 评论，仓库 16225★） | 状态更正后仍可作"按词表切"指纹证据 |
| 7 | justpdf#278（"`subset_font` 使已子集程序膨胀 27–47%"） | 未能定位仓库/编号（`yeslogic/justpdf` 不存在；同名仓库均无该 issue） | **降为未核实，不作锚点** |
| 8 | 560 字体的 "restricted 44/560≈7.9%" | 44 是"表面含 bit1"；**版本分流后受限仅 4/560（0.71%）**，40 个 0x000E 在 v0/v1 下应解析为 Editable | 两个数值并列并标注口径（§五） |
| 9 | Inter "876KB" / Noto Sans SC "17.7MB" | Inter 4.1 `InterVariable.ttf` **879,708 B**；Noto Sans SC Regular（OTF 子集）**8,331,336 B** | 以实测登记（§八） |
| 10 | "F2 与 F3 只差 `OS/2.version` 一个字节"（M1 生成器初稿注释） | 实测：`OS/2` 表长 **v0 = 78 B / v3+ = 96 B**（`ulCodePageRange` 自 v0 起才有）→ 产物总字节 **1512 vs 1528**；`cmap` 与其余表逐字节一致 | 改文档与生成器说明为"差别只有 version 与表长两处"（§四.1 #4） |
| 12 | "默认 `layout_features` 是 67 个标签"（M1 记录，未写版本） | **随版本漂移**：4.57.0 = **67**、4.67.0 = **68**（差 `palt`）。`ss01`–`ss08`、`cv01`–`cv14`、`case`、`tnum`、`zero`、`aalt` 两版都**不在**默认集合内 | 两个版本并列登记；`layout-survival` **不判断**某标签该不该丢，只报实际差集（§六.5.3） |
| 13 | "LookupType 7 是唯一需要解包的 Extension 类型" | **GPOS 的 Extension 是 Type 9 不是 7**（Arial 134 个 GPOS lookup 全为 Type 9；Calibri 254 个同）。只解 7 会让 GPOS 整段读不到 | §六.5.2 明确要求**同时解 7 与 9**；`tests/test_layout_survival.py` 用合成 GPOS Extension 样本钉住 |

## 八、数据源可获取性与锁文件口径

**原则**：只使用 **OFL / 开源许可** 字体；**二进制不入库**；`data/fonts.lock` 记录 `URL + 字节数 + sha256`；`tools/fetch_fonts.py --check` 离线校验既有文件哈希。

| 字体 | 来源（实测可达） | 实测字节数 | sha256 | 状态 |
|---|---|---|---|---|
| Inter 4.1（`InterVariable.ttf`，OFL 1.1） | `https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip`（zip 实测 33,707,794 B / `sha256:9883fdd4a49d4fb6…`） | **879,708** | `4989b125924991b90d05b2d16e0e388c48f7d5bb8b30539bbf9c755278d0ccaf` | ✅ 已下载并计算哈希（不保存） |
| Inter 4.1（`extras/ttf/Inter-Regular.ttf`，静态） | 同上 zip | **411,640** | `40d692fce188e4471e2b3cba937be967878f631ad3ebbbdcd587687c7ebe0c82` | ✅ 同上 |
| Noto Sans SC Regular（`NotoSansSC-Regular.otf`，OFL 1.1） | `notofonts/noto-cjk` → `Sans/SubsetOTF/SC/`（raw 直链，见 `data/fonts.lock`） | **8,331,336** | `faa6c9df652116dde789d351359f3d7e5d2285a2b2a1f04a2d7244df706d5ea9` | ✅ **2026-10-21 已下载并实测哈希**（31,036 字形 / OS/2 v3 / cmap 30,890 码位） |
| Noto Sans CJK SC VF（`NotoSansCJKsc-VF.otf`，OFL 1.1） | `notofonts/noto-cjk` → `Sans/Variable/OTF/` | **30,737,452** | ⬜ 未下载（仅 API 列目录取尺寸） | 备选，首期未纳入锁文件 |
| Noto Sans（Latin，`NotoSans-Bold.ttf`，OFL 1.1） | `notofonts/noto-fonts` → `hinted/ttf/NotoSans/` | **575,740** | `c976e4b1b99edc88775377fcc21692ca4bfa46b6d6ca6522bfda505b28ff9d6a` | ✅ **2026-10-21 已下载并实测哈希**（3,748 字形 / OS/2 v4 / cmap 2,840 码位） |
| Source Han Sans（OFL 1.1） | Adobe 官方 release | ⬜ 未实测 | ⬜ | 备选，首期可用 Noto Sans CJK 替代 |

> **下载实测坑（2026-10-21，本机）**：`raw.githubusercontent.com` 直链在本机会被中途重置，
> 单次 `curl` 只拿到 4.5–7.5 MB（目标 8,331,336 B）。可靠做法 = **HTTP Range 断点续传 + 字节数收敛判定**；
> `tools/fetch_fonts.py --download` 走的是单次请求，网络不稳时可能报 `DOWNLOAD_FAILED`（不写半截文件，
> 因为校验在写盘之前）。

**破损样本全部可合成**（**不依赖任何商用字体**）：
- 改 `fsType`：`TTFont` 读入 → 置 `OS/2.fsType` → 另存（**只用于生成 fixture，产物不入库**）；
- 删 nameID 13/14：用 `pyftsubset` 默认 `name_IDs=[0..6]` 产出，或直接构造 name 表；
- 清 GSUB FeatureList：`--layout-features=''`，或用 `TTFont` 置空后 `save`；
- 造静默丢字：`pyftsubset --text=...`（`--ignore-missing-unicodes` 为默认）；
- 造码页矛盾：仅 CJK 子集，观察 `recalcCodePageRanges` 的 Latin-1 回退。

**商用字体红线**：`Arial` / `Calibri` / `Microsoft YaHei`(`msyh.ttc`) / `Segoe UI Emoji` 等在本文档中**仅作为只读实测对象**（给出命令与观察），**不复制、不入库、不分发**；仓库二进制由 `.gitignore` 阻断。fixture 与回归套件一律使用 OFL 字体或程序合成的极小字体；若需复现某个商用字体的行为，以"同构 OFL 字体 + 文档标注替代关系"的方式表达。

## 九、未核实项（**写进文档时必须标注，不得当作事实**）

1. ⬜ **PDF/UA-2 §8.4.5.5.1 "legally embeddable"** 引文：`pdfa.org` 返回 **403**，未能独立核实 → 只能写"依 issue 报告（未核实）"。
2. ⬜ **justpdf#278**（重复子集化膨胀 27–47%）：来源不可定位 → 不作证据。
3. ⬜ **`text coverage font`（14）与 `font embeddability`（686）** 两个 GitHub 检索式：本次窗口**未复现**（检索配额受限）→ 只登记为 ⬜；已单独核实其中的 `nripankadas07/font-coverage-plan`（0★，2026-10-16 建当天停更）。
4. ⬜ **fontbakery "323 真检查 / 190 厂商专属"、fontspector "74 检查文件"**：上游记录与实测不符（§七 #1/#2）→ 以实测为准。
5. ⬜ **`mstmc.ttf`**：`bad sfntVersion` 无法解析 → 已从 560 计数中排除；其 `fsType` 未计入分布。
6. ✅ 已核实但需注意版本漂移的项：所有 star 数、`pushed_at`、issue 评论数均为 **2026-10-19 快照**；重新运行会得到不同数值，**必须标注测量日期**后引用。
