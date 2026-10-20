# silent-drop（F4）

> 本目录由 `tools/gen_fixtures.py` 生成维护。**二进制产物不入仓**：
> `out/` 已被 `.gitignore` 阻断，入仓的只有本说明与 `expect.json`。

## 构造

`source.ttf` 含 `a b c 汉 字` 五个码位；用 `fontTools.subset`（默认 `ignore_missing_unicodes=True`）对 `abc` 子集得到 `subset.ttf`。
产物 cmap 只有 `a b c` —— 汉字**静默消失**（无报错、退出码 0）。

## 真值来源

需求集 `R = {{a,b,c,汉,字}}`，产物覆盖 `T = {{a,b,c}}`，源覆盖 `S ⊇ R`：
`LOST_IN_SUBSET = (R ∩ S) \ T = {{汉, 字}}`；`MISSING_IN_SOURCE = R \ S = ∅`。
由「合成本身」决定，不依赖被测实现（`data/README.md` §六.2）。

## 期望（`expect.json` 摘要）

```
LOST_IN_SUBSET: ["U+5B57", "U+6C49"]
MISSING_IN_SOURCE: []
OK: ["U+0061", "U+0062", "U+0063"]
counterexample_guard: "丢失的码位源字体确有覆盖 → 不得归入 MISSING_IN_SOURCE"
expected_findings: [{"code": "LOST_IN_SUBSET", "severity": "error", "primary_key": "U+5B57", "spec_ref": "data/README §6.2"}, {"code": "LOST_IN_SUBSET", "severity": "error", "primary_key": "U+6C49", "spec_ref": "data/README §6.2"}]
```

## 重生成

```bash
py tools/gen_fixtures.py --only F4
py tools/gen_fixtures.py --check          # 位级一致
```

> 口径单点：`data/README.md` §六（本文件不复制判定式，只描述构造与期望形状）。
