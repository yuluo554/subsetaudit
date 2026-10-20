# -*- coding: utf-8 -*-
"""M3 · `coverage-diff` 覆盖差集 —— 真实判定。

    evaluate(source_path, required, subset_path=None, strict_source=False)
        -> (findings, skips, summary)

**口径单点 = `data/README.md` §六.2 / §六.3 / §六.4**，本模块只实现、不定义：
  · §六.2 三分类判定式 + 级别（`MISSING_IN_SOURCE` 默认 `warn`，`--strict-source` → `error`；
    `LOST_IN_SUBSET` 恒 `error`）+ `spec_ref` 字面量 + finding 粒度（每码位一条）；
  · §六.2.1 组合字符闭包（单层、NFC/NFD 双向、`added = C \\ R0`，**只计数不产 finding**）；
  · §六.3 cmap 编码优先级与两条互不合并的失败路径（`no_cmap_table` / `no_unicode_cmap`）；
  · §六.4 分区计数（BMP / ExtA / ExtB+ / other）。

编排：``sfnt.select_unicode_cmap``（选表）→ ``cmapset.codepoints``（剔 glyph0）
→ ``cmapset.classify``（三分类）→ ``cmapset.block_counts``（分块）→ ``cmapset.closure``（闭包）
→ ``cmapset.fallback_hint``（回退链建议，**仅建议，不改判定**）。

失败路径：不可读 / 非 sfnt → ``canonical.InputError``（CLI 收口为退出码 2）；
取不到 Unicode cmap → ``SKIPPED`` 且 ``summary`` 为空 —— **绝不**输出"覆盖为空"的 OK 结论。
"""
from __future__ import print_function

from . import cmapset, sfnt
from ._skeleton import validate_inputs
from .canonical import finding, skipped

MODULE = "coverage-diff"

#: §六.2 —— 三分类的 `spec_ref` 字面量（**逐字**使用，勿改写措辞）
SPEC_REF = "data/README §6.2"

#: §六.2 的 finding 代码（分类名即代码）
CODE_MISSING = "MISSING_IN_SOURCE"
CODE_LOST = "LOST_IN_SUBSET"

#: §六.2 的分类输出顺序（summary 键序不依赖 dict 迭代运气）
CATEGORIES = ("OK", "MISSING_IN_SOURCE", "LOST_IN_SUBSET")

#: 闭包 / 分块在 summary 里的固定子键
BLOCKS = ("BMP", "ExtA", "ExtB+", "other")


def _u(cp):
    """``primary_key`` / summary 的统一写法：``U+5B57``（大写、至少 4 位，§六.2）。"""
    return "U+%04X" % int(cp)


def _read_side(path, side):
    """读一侧的**原始 cmap 映射**（``{codepoint: glyphName}``，尚未剔 glyph0）。

    返回 ``(selected, stats, skip_or_None)``；``skip`` 的两条理由**不得合并**（§六.3）。
    glyph0 的剔除放在 ``evaluate`` 里显式做（§六.2 的那条口径只在一个地方落）。
    """
    font = sfnt.open_font(path)
    try:
        selected, stats = sfnt.select_unicode_cmap(font)
    finally:
        sfnt.close_font(font)

    reason = stats.get("reason") or ""
    if reason:
        detail = "%s: %s；subtables=%s" % (
            side,
            "字体没有 cmap 表" if reason == "no_cmap_table"
            else "cmap 表里没有 Unicode 子表（如仅 (1,0)/format 0）",
            [list(row) for row in stats.get("subtables", [])],
        )
        return None, stats, skipped(MODULE, reason, detail)
    return selected, stats, None


def _evidence(cp, source_covered, subset_covered):
    return {
        "codepoint": _u(cp),
        "block": cmapset.block_of(cp),
        "source_covered": bool(source_covered),
        "subset_covered": None if subset_covered is None else bool(subset_covered),
    }


def _classify_findings(result, subset_cps, subset_present, strict_source):
    """§六.2：每码位一条 finding；`MISSING_IN_SOURCE` 的级别随 `--strict-source` 变。

    `evidence` 的四个键固定（§六.2）；两个覆盖位都填**实测值**（不按分类反推）：
    产物可能恰好覆盖了源字体没有的字，此时 `MISSING_IN_SOURCE` 的 `subset_covered` 是 `True`。
    `subset_covered` 只在**没给 `--subset`** 时是 `None`（该信息不存在，不猜）。
    """
    out = []
    missing_severity = "error" if strict_source else "warn"
    for cp in result["MISSING_IN_SOURCE"]:
        out.append(finding(
            MODULE, CODE_MISSING, missing_severity, _u(cp),
            "需求字符 %s 在原字体里没有真实覆盖（映射到 .notdef 视同缺失）" % _u(cp),
            evidence=_evidence(cp, False, None if not subset_present else cp in subset_cps),
            spec_ref=SPEC_REF,
        ))
    for cp in result["LOST_IN_SUBSET"]:
        out.append(finding(
            MODULE, CODE_LOST, "error", _u(cp),
            "需求字符 %s 原字体有覆盖、子集产物丢失（静默丢字）" % _u(cp),
            evidence=_evidence(cp, True, False),
            spec_ref=SPEC_REF,
        ))
    return out


def _closure_summary(required0, source_cps, subset_cps, subset_present):
    """§六.2.1：闭包只计数、不产 finding；三分类仍只用 `R0`。"""
    _closed, added = cmapset.closure(required0)
    added_set = set(added)
    missing = added_set - source_cps
    lost = (added_set & source_cps) - subset_cps if subset_present else set()
    return {
        "added": [_u(cp) for cp in added],
        "added_codepoints": len(added),
        "missing_in_source": len(missing),
        "lost_in_subset": len(lost),
    }


def evaluate(source_path, required, subset_path=None, strict_source=False):
    """覆盖差集：返回 ``(findings, skips, summary)``（形状与 M0 骨架一致，接口不改）。"""
    validate_inputs([source_path, subset_path])  # 不可读 / 非 sfnt → InputError → 退出码 2

    required0 = set(int(cp) for cp in required)
    subset_present = subset_path is not None

    source_selected, source_stats, source_skip = _read_side(source_path, "source")
    subset_selected, subset_stats, subset_skip = (None, None, None)
    if subset_present:
        subset_selected, subset_stats, subset_skip = _read_side(subset_path, "subset")

    skips = [s for s in (source_skip, subset_skip) if s is not None]
    if skips:
        # §六.3：任一侧取不到 Unicode cmap → 整份报告不给三分类（不猜、不给半份结论）
        return ([], skips, {})

    # §六.2：映射到 .notdef 的码位视为缺 —— 剔除动作只在 `cmapset.codepoints` 一处落
    source_cps = cmapset.codepoints(source_selected)
    subset_cps = cmapset.codepoints(subset_selected) if subset_present else None

    result = cmapset.classify(required0, source_cps, subset_cps if subset_present else None)
    findings = _classify_findings(result, set(subset_cps or ()), subset_present, strict_source)

    blocks = {
        "required": cmapset.block_counts(required0),
    }
    for key in CATEGORIES:
        blocks[key] = cmapset.block_counts(result[key])

    summary = {
        "required": {
            "count": len(required0),
            "blocks": blocks["required"],
        },
        "coverage": {
            "OK": [_u(cp) for cp in result["OK"]],
            "MISSING_IN_SOURCE": [_u(cp) for cp in result["MISSING_IN_SOURCE"]],
            "LOST_IN_SUBSET": [_u(cp) for cp in result["LOST_IN_SUBSET"]],
            "counts": dict(
                (key, len(result[key])) for key in CATEGORIES
            ),
            "blocks": dict((key, blocks[key]) for key in CATEGORIES),
        },
        "closure": _closure_summary(required0, set(source_cps),
                                    set(subset_cps or ()), subset_present),
        "fallback_hint": cmapset.fallback_hint(result["LOST_IN_SUBSET"],
                                              subset_cps if subset_present else ()),
        "cmap": {
            "source_chosen": source_stats.get("chosen", []),
            "source_subtables": source_stats.get("subtables", []),
        },
        "strict_source": bool(strict_source),
        "subset_present": bool(subset_present),
    }
    if subset_present:
        summary["cmap"]["subset_chosen"] = subset_stats.get("chosen", [])
        summary["cmap"]["subset_subtables"] = subset_stats.get("subtables", [])

    return (findings, [], summary)
