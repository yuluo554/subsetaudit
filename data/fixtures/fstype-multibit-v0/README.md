# fstype-multibit-v0（F2）

> 本目录由 `tools/gen_fixtures.py` 生成维护。**二进制产物不入仓**：
> `out/` 已被 `.gitignore` 阻断，入仓的只有本说明与 `expect.json`。

## 构造

程序合成极小 TTF，`OS/2.fsType = 0x000E`（bits 1/2/3 同时置位），`OS/2.version = 0`。
这是**反例守护**样本：v0–v2 规范要求「取最宽松」，任何实现只要报互斥违规就是误报。

## 真值来源

`bits = 0x000E`，`version = 0 <= 2` → 取最宽松 = bit3 Editable（`least_restrictive`）；`may_subset = (0x000E & 0x0100) == 0` → `true`。
其余四条：`embed_pdf = true`、`embed_app = false`（perm≠0）、`embed_web = true`（perm≠2 且 bit8/bit9 均未置位）、`may_modify = true`。
规范原文：「the least-restrictive permission indicated take precedence」（`data/README.md` §3.2）。

## 期望（`expect.json` 摘要）

```
bit8_no_subsetting: false
bit9_bitmap_only: false
counterexample_guard: "v0 的 bits0–3 多位并存必须解析为最宽松权限，不得误报互斥"
embed_app: false
embed_pdf: true
embed_web: true
expected_findings: []
fsType: "0x000E"
may_modify: true
may_subset: true
mutual_exclusion_violation: false
os2_version: 0
permission_bits: "0x000E"
permission_name: "Editable"
permission_resolution: "least_restrictive"
reserved_bits_set: false
```

## 重生成

```bash
py tools/gen_fixtures.py --only F2
py tools/gen_fixtures.py --check          # 位级一致
```

> 口径单点：`data/README.md` §六（本文件不复制判定式，只描述构造与期望形状）。
