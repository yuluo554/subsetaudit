# fstype-multibit-v3（F3）

> 本目录由 `tools/gen_fixtures.py` 生成维护。**二进制产物不入仓**：
> `out/` 已被 `.gitignore` 阻断，入仓的只有本说明与 `expect.json`。

## 构造

程序合成极小 TTF，`OS/2.fsType = 0x000E`（bits 1/2/3 同时置位），`OS/2.version = 3`。
v3+ 规范要求互斥，故必须报互斥违规。
F2 与 F3 的差别**只有两处**：`OS/2.version`（0 vs 3），以及由版本决定的 OS/2 表长（v0 = 78 B / v3+ = 96 B —— `ulCodePageRange` 自 v0 起才有）；cmap 与其余表完全一致。这是本工具版本分流能力的唯一判别样本。

## 真值来源

`bits = 0x000E`，`version = 3 ≥ 3` → **互斥违规**（`error`）。
最宽松权限仍是 Editable（`least_restrictive`），五元结论与 F2 **完全相同** —— 违规本身独立成条，两者不互相抵消（这是 F2/F3 对照的判别点）。

## 期望（`expect.json` 摘要）

```
bit8_no_subsetting: false
bit9_bitmap_only: false
embed_app: false
embed_pdf: true
embed_web: true
expected_findings: [{"code": "FSTYPE_MUTUAL_EXCLUSION", "severity": "error", "spec_ref": "MS-OS2 §fsType (v3+ mutually exclusive)"}]
fsType: "0x000E"
may_modify: true
may_subset: true
mutual_exclusion_violation: true
os2_version: 3
permission_bits: "0x000E"
permission_name: "Editable"
permission_resolution: "least_restrictive"
reserved_bits_set: false
```

## 重生成

```bash
py tools/gen_fixtures.py --only F3
py tools/gen_fixtures.py --check          # 位级一致
```

> 口径单点：`data/README.md` §六（本文件不复制判定式，只描述构造与期望形状）。
