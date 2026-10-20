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

## 六、数值口径（**一处定义**）

1. **`fsType` 判定**：先读 `OS/2.version`；`bits = fsType & 0x000F`。若 `version ≤ 2` 且 `bits` 有 ≥2 位 → 取**最宽松**权限（8 > 4 > 2 > 0 的宽松序：8 最宽松，2 最严）；若 `version ≥ 3` 且 ≥2 位 → **互斥违规**。`may_subset = (fsType & 0x0100) == 0`；`embed_web` 由权限位与 bit8/bit9 共同决定；保留位：`fsType & 0xFCF1 != 0`（**0xFCF1** = bit0 + bits4–7 + bits10–15）→ 报保留位置位。
2. **覆盖三分类**：对需求字符集 `R`，原字体 cmap 覆盖集 `S`，子集字体覆盖集 `T`：`MISSING_IN_SOURCE = R \ S`（是否报取决于 `--strict-source`，默认 report 为 `error`）；`LOST_IN_SUBSET = (R ∩ S) \ T`；`OK = R ∩ S ∩ T`。**glyph0 命中不计入覆盖**（映射到 `.notdef` 的码位视为缺）。
3. **cmap 编码优先级**：`(3,10) → (0,4) → (3,1) → (0,3)`；仅含 `(1,0)`/format 0 等非 Unicode 映射的字体 → 输出 `SKIPPED(reason=no_unicode_cmap)`。多个同优先级子表同时存在时取并集，并在报告里列各子表的项数。
4. **分区计数**：BMP = `U+0000–U+FFFF`；ExtA = `U+3400–U+4DBF`；ExtB+ = `U+20000–U+2FA1F`；其余按规范块名归入 `other`。
5. **布局三元组**：`(ScriptTag, LangSysTag|"dflt"|"all", FeatureTag)`；`"all"` 表示该 feature 在所有 langsys 中出现。查找表计数：`计数(LookupType 7) = Σ 解包 ExtSubTable 后的子表`；朴素遍历结果单独记为 `naive`（**只用于对照，不作结论**）。
6. **退出码**：`0` 通过；`1` 有发现（`error` 级 finding）；`2` 输入非法（文件不可读 / 非字体 / 缺必需参数 / JSON 反序列化失败）。`SKIPPED(reason=...)` 恒为**不影响退出码**的 `note`。
7. **fixture 名表**：`F1 fstype-nosubset`（0x0108）、`F2 fstype-multibit-v0`（0x000E + v0，**反例守护**）、`F3 fstype-multibit-v3`（0x000E + v3）、`F4 silent-drop`、`F5 metadata-stripped`、`F6 codepage-mismatch`。
8. **确定性**：所有排序键固定（finding：`module, severity, 主键`；字符集：码位升序；三元组：`script, langsys, feature`）；报告不含时间戳/绝对路径/主机名/用户名；同一输入两次运行逐字节一致。

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
| 11 | "`expect.json` 记录运行时 fontTools 版本"（M1 生成器初稿） | 3.8 通道写 `4.57.0`、3.12 通道写 `4.67.0`，而**产物二进制逐字节相同** → 跨通道 `--check` 互红 | 改为记录**铸造版本**常量 `GOLDEN_FONTOOLS_VERSION`（§四.1 推论） |

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
