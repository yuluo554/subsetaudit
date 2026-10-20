# fstype-nosubset（F1）

> 本目录由 `tools/gen_fixtures.py` 生成维护。**二进制产物不入仓**：
> `out/` 已被 `.gitignore` 阻断，入仓的只有本说明与 `expect.json`。

## 构造

程序合成极小 TTF（`fontBuilder`，3 字形），`OS/2.fsType = 0x0108`：
bit3（Editable）+ bit8（No subsetting）。`OS/2.version = 4`。

## 真值来源

直接由 `fsType` 位运算得到：`may_subset = (fsType & 0x0100) == 0` → `false`。
不是「跑一遍工具再看输出」，而是对**输入位值**的独立复算（`data/README.md` §六.1）。

## 期望（`expect.json` 摘要）

```
bit8_no_subsetting: true
bit9_bitmap_only: false
expected_findings: [{"code": "FSTYPE_NO_SUBSET", "severity": "error", "spec_ref": "MS-OS2 §fsType bit8"}]
fsType: "0x0108"
may_subset: false
mutual_exclusion_violation: false
os2_version: 4
pending_conclusions: {"keys": ["embed_pdf", "embed_app", "embed_web", "may_modify"], "reason": "data/README.md §六.1 目前只定义了 may_subset 与保留位掩码；其余四条由 M2 先写入口径表再实现（plan/01 §三 禁第二套口径）"}
permission_bits: "0x0008"
permission_name: "Editable"
reserved_bits_set: false
```

## 重生成

```bash
py tools/gen_fixtures.py --only F1
py tools/gen_fixtures.py --check          # 位级一致
```

> 口径单点：`data/README.md` §六（本文件不复制判定式，只描述构造与期望形状）。
