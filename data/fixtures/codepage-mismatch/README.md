# codepage-mismatch（F6）

> 本目录由 `tools/gen_fixtures.py` 生成维护。**二进制产物不入仓**：
> `out/` 已被 `.gitignore` 阻断，入仓的只有本说明与 `expect.json`。

## 构造

`source.ttf` 的 `ulCodePageRange1 = 0x4001F`（含 CJK 与 Latin-1）；只对 `汉字` 子集。
fontTools 的 `recalcCodePageRanges` 在无可用码页时**回退置 bit0 (Latin 1)** → 产物 `ulCodePageRange1 = 0x1`，而 cmap 只有 CJK = 真实矛盾。

## 真值来源

码页 bit0 声明 Latin-1，而 cmap 覆盖 ∩ `U+0000–U+00FF` = ∅ → 矛盾。
同时 `ulUnicodeRange1 = 0` 是**正确重算**（bit59 在 `ulUnicodeRange2`）→ **不得**报矛盾。

## 期望（`expect.json` 摘要）

```
cmap_has_latin1: false
codepage_claims_latin1: true
counterexample_guard: "ulUnicodeRange1=0 是正确重算（bit59 在 ulUnicodeRange2），不得报矛盾；真实矛盾点只在 ulCodePageRange1 的 Latin-1 回退"
expected_absent_findings: [{"code": "UNICODE_RANGE_CONTRADICTION", "primary_key": "ur1:zero"}]
expected_findings: [{"code": "CODEPAGE_CLAIMS_LATIN1_WITHOUT_COVERAGE", "severity": "error", "primary_key": "cp1:latin1", "spec_ref": "fontTools O_S_2f_2.recalcCodePageRanges"}]
ulCodePageRange1: "0x00000001"
ulCodePageRange2: "0x00000000"
ulUnicodeRange1: "0x00000000"
ulUnicodeRange2_bit59_set: true
```

## 重生成

```bash
py tools/gen_fixtures.py --only F6
py tools/gen_fixtures.py --check          # 位级一致
```

> 口径单点：`data/README.md` §六（本文件不复制判定式，只描述构造与期望形状）。
