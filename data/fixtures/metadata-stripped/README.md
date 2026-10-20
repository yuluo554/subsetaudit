# metadata-stripped（F5）

> 本目录由 `tools/gen_fixtures.py` 生成维护。**二进制产物不入仓**：
> `out/` 已被 `.gitignore` 阻断，入仓的只有本说明与 `expect.json`。

## 构造

`source.ttf` 含 nameID 13/14 与许可文本；用默认 `name_IDs=[0,1,2,3,4,5,6]` / `name_languages=[1033]` 子集。
产物只剩 nameID 0–6、单一语言 → 13/14 被**默认剥离**。

## 真值来源

源有 13/14、产物没有 → 差集非空 → 判「默认剥离」；语言记录数由产物 name 表实读得到 `1`。
（若源也没有 13/14，则应判「原作者没写」 —— 这一分类需要 `--source` 才能做。）

## 期望（`expect.json` 摘要）

```
author_absent_name_ids: [7, 11, 16, 17]
counterexample_guard: "只有拿到 --source 且原文确有 13/14 时，才可判『默认剥离』；原文也没有则判『原作者没写』（不产 finding）"
default_stripped_name_ids: [13, 14]
expected_absent_findings: [{"code": "NAME_TRADEMARK_STRIPPED", "primary_key": "nameID7"}, {"code": "NAME_VENDOR_URL_STRIPPED", "primary_key": "nameID11"}, {"code": "NAME_TYPOGRAPHIC_FAMILY_STRIPPED", "primary_key": "nameID16"}, {"code": "NAME_TYPOGRAPHIC_SUBFAMILY_STRIPPED", "primary_key": "nameID17"}]
expected_findings: [{"code": "NAME_LICENSE_DESCRIPTION_STRIPPED", "severity": "warn", "primary_key": "nameID13", "spec_ref": "MS-NAME nameID13"}, {"code": "NAME_LICENSE_INFO_URL_STRIPPED", "severity": "warn", "primary_key": "nameID14", "spec_ref": "MS-NAME nameID14"}]
missing_classification: "default_stripped"
missing_name_ids: [13, 14]
name_language_count: 1
required_name_ids: [0, 7, 11, 13, 14, 16, 17]
subset_name_ids: [0, 1, 2, 3, 4, 5, 6]
subset_name_languages: [1033]
```

## 重生成

```bash
py tools/gen_fixtures.py --only F5
py tools/gen_fixtures.py --check          # 位级一致
```

> 口径单点：`data/README.md` §六（本文件不复制判定式，只描述构造与期望形状）。
