# -*- coding: utf-8 -*-
"""M2 · `license-gate` 许可闸门 —— 真实判定。

    evaluate(path) -> (findings, skips, summary)

**口径单点 = `data/README.md` §六.1**，本模块只实现、不定义：
  · §六.1.1 解析顺序：读 ``OS/2.version`` → ``bits = fsType & 0x000F`` → 版本分流得 ``perm``
    → bit8 / bit9 / 保留位 → 五元结论；
  · §六.1.2 ``perm`` 解析（单权限位 direct；v0–v2 多位并存取最宽松；v3+ 多位并存**仍取最宽松**
    但互斥违规独立成条）；
  · §六.1.3 五元结论的判定式与 ``spec_ref`` 字面量；
  · §六.1.4 违规码表（六条，不多不少）。

``SPEC_REFS`` / ``CODE_SPEC_REFS`` 是 §六.1.3 / §六.1.4 两表的**逐字副本**；
``tests/test_license_gate.py`` 会解析 `data/README.md` 对账，改一边不改另一边必红。

失败路径：文件不可读 / 非 sfnt → ``canonical.InputError``（CLI 收口为退出码 2）；
无 ``OS/2`` 表 → ``SKIPPED(reason=no_os2_table)`` 且退出码 0（§六.1 不适用，绝不猜）。
"""
from __future__ import print_function

from . import sfnt
from ._skeleton import validate_inputs
from .canonical import finding, skipped

MODULE = "license-gate"

#: §六.1.2 的权限名（合法值只有 0/2/4/8，§3.1）
PERMISSION_NAMES = {0: "Installable", 2: "Restricted", 4: "Preview & Print", 8: "Editable"}

#: §六.1.3 —— 五元结论 → spec_ref 字面量（**逐字**复制，勿改写措辞）
SPEC_REFS = {
    "embed_pdf": "MS-OS2 §fsType bits0-3 (0/4/8 allow document embedding)",
    "embed_app": "MS-OS2 §fsType value 0 (permanent installation)",
    "embed_web": "MS-OS2 §fsType bits0-3 + bit8 (temporary loading for viewing, no subsetting)",
    "may_subset": "MS-OS2 §fsType bit8 (No subsetting)",
    "may_modify": "MS-OS2 §fsType bits0-3 (editing permitted / read-only)",
}

#: 五元结论的固定输出顺序（报告键序不依赖 dict 迭代运气）
CONCLUSION_KEYS = ("embed_pdf", "embed_app", "embed_web", "may_subset", "may_modify")

#: §六.1.4 —— 违规码 → spec_ref 字面量（**逐字**复制）
CODE_SPEC_REFS = {
    "FSTYPE_BIT0_RESERVED": "MS-OS2 §fsType bit0 (permanently reserved)",
    "FSTYPE_RESERVED_BITS": "MS-OS2 §fsType bits4-7/bits10-15 (reserved)",
    "FSTYPE_MUTUAL_EXCLUSION": "MS-OS2 §fsType (v3+ mutually exclusive)",
    "FSTYPE_NO_SUBSET": "MS-OS2 §fsType bit8",
    "FSTYPE_BITMAP_ONLY": "MS-OS2 §fsType bit9 (Bitmap embedding only)",
    "FSTYPE_RESTRICTED_LICENSE": "MS-OS2 §fsType value 2 (Restricted License)",
}

#: §六.1.4 的 primary_key 与（固定部分的）级别
CODE_PRIMARY_KEYS = {
    "FSTYPE_BIT0_RESERVED": "bit0",
    "FSTYPE_RESERVED_BITS": "bits4-15",
    "FSTYPE_MUTUAL_EXCLUSION": "bits0-3",
    "FSTYPE_NO_SUBSET": "bit8",
    "FSTYPE_BITMAP_ONLY": "bit9",
    "FSTYPE_RESTRICTED_LICENSE": "bit1",
}

BIT0 = 0x0001
RESERVED_BITS = 0xFCF0  # bits4–7 + bits10–15（bit0 单列，见 §六.1.6）
PERMISSION_MASK = 0x000E  # bits1–3
BIT8_NO_SUBSET = 0x0100
BIT9_BITMAP_ONLY = 0x0200


def _hex16(value):
    return "0x%04X" % (int(value) & 0xFFFF)


def resolve_permission(bits, version):
    """§六.1.2：由 ``bits``（= fsType & 0x000F）与 ``OS/2.version`` 得 ``(perm, resolution)``。

    v3+ 的多位并存**照样**解析成最宽松值 —— 违规由 ``FSTYPE_MUTUAL_EXCLUSION`` 独立成条，
    两者不互相抵消（F3 的 golden 就钉这一点）。
    """
    permission_bits = int(bits) & PERMISSION_MASK
    if permission_bits == 0:
        return 0, "direct"
    if bin(permission_bits).count("1") == 1:
        return permission_bits, "direct"
    for candidate in (8, 4, 2):
        if permission_bits & candidate:
            return candidate, "least_restrictive"
    return 0, "direct"  # 不可达：permission_bits 非 0 时必有一位


def conclusions_for(fs_type, perm):
    """§六.1.3 的五条判定式（键序由 ``CONCLUSION_KEYS`` 固定）。"""
    bit8 = (fs_type & BIT8_NO_SUBSET) != 0
    bit9 = (fs_type & BIT9_BITMAP_ONLY) != 0
    values = {
        "embed_pdf": (perm != 2) and not bit9,
        "embed_app": (perm == 0) and not bit9,
        "embed_web": (perm != 2) and not bit8 and not bit9,
        "may_subset": not bit8,
        "may_modify": perm in (0, 8),
    }
    return dict((key, values[key]) for key in CONCLUSION_KEYS)


def _violations(fs_type, version, perm, bits):
    """§六.1.4 的六条码。返回 ``[(code, severity, message)]``，顺序即码表顺序。"""
    out = []
    base = {"fsType": _hex16(fs_type), "os2_version": int(version)}
    permission_bits = int(bits) & PERMISSION_MASK
    multi = bin(permission_bits).count("1") >= 2

    if fs_type & BIT0:
        out.append((
            "FSTYPE_BIT0_RESERVED", "error",
            "fsType=%s 的 bit0 置位：该位在任何 OS/2 版本都是 permanently reserved，合法字体必须为 0"
            % _hex16(fs_type),
            dict(base, bit0_set=True),
        ))

    reserved = fs_type & RESERVED_BITS
    if reserved:
        # §六.1.6：v0/v1 规范要求「Applications must ignore bits 4 to 15」→ 降为 warn
        severity = "error" if int(version) >= 2 else "warn"
        out.append((
            "FSTYPE_RESERVED_BITS", severity,
            "fsType=%s 的保留位 %s 置位（bits4–7 / bits10–15 必须为 0）；OS/2 v%d %s"
            % (_hex16(fs_type), _hex16(reserved), int(version),
               "按强制要求判 error" if severity == "error" else "规范要求应用忽略 bits4–15，降为 warn"),
            dict(base, reserved_mask=_hex16(reserved)),
        ))

    if int(version) >= 3 and multi:
        out.append((
            "FSTYPE_MUTUAL_EXCLUSION", "error",
            "OS/2 v%d 的权限位 bits1–3 同时置位（%s）：v3+ 规范要求互斥；解析值仍取最宽松 %s，"
            "违规与解析结果各自独立" % (int(version), _hex16(permission_bits),
                                        PERMISSION_NAMES.get(perm, "unknown")),
            dict(base, permission_bits=_hex16(permission_bits),
                 resolved=PERMISSION_NAMES.get(perm, "unknown")),
        ))

    if fs_type & BIT8_NO_SUBSET:
        out.append((
            "FSTYPE_NO_SUBSET", "error",
            "bit8 置位：该字体声明不得在嵌入前子集化 → may_subset=false",
            dict(base, bit8_no_subsetting=True),
        ))

    if fs_type & BIT9_BITMAP_ONLY:
        out.append((
            "FSTYPE_BITMAP_ONLY", "warn",
            "bit9 置位：只允许嵌入位图，不得嵌入轮廓数据 → PDF/App/Web 的轮廓内嵌不成立",
            dict(base, bit9_bitmap_only=True),
        ))

    if perm == 2:
        out.append((
            "FSTYPE_RESTRICTED_LICENSE", "warn",
            "权限值解析为 2 Restricted License：未经权利人明示许可不得修改、嵌入或交换",
            dict(base, permission_bits=_hex16(permission_bits)),
        ))

    return out


def evaluate(path):
    """许可闸门：返回 ``(findings, skips, summary)``（形状与 M0 骨架一致，接口不改）。"""
    validate_inputs([path])  # 不可读 / 非 sfnt → InputError → 退出码 2

    font = sfnt.open_font(path)
    try:
        info = sfnt.os2_info(font)
    finally:
        sfnt.close_font(font)

    if info is None:
        return (
            [],
            [skipped(MODULE, "no_os2_table",
                     "字体无 OS/2 表：嵌入许可位不存在，任何五元结论都会是猜测")],
            {},
        )

    fs_type = int(info["fsType"])
    version = int(info["version"])
    bits = fs_type & 0x000F
    perm, resolution = resolve_permission(bits, version)
    values = conclusions_for(fs_type, perm)
    violations = _violations(fs_type, version, perm, bits)

    findings = [
        finding(
            MODULE, code, severity, CODE_PRIMARY_KEYS[code],
            message,
            evidence=evidence,
            spec_ref=CODE_SPEC_REFS[code],
        )
        for (code, severity, message, evidence) in violations
    ]

    summary = {
        "fsType": _hex16(fs_type),
        "os2_version": version,
        "permission_bits": _hex16(bits),
        "permission_name": PERMISSION_NAMES.get(perm, "unknown"),
        "permission_resolution": resolution,
        "conclusions": dict(
            (key, {"value": values[key], "spec_ref": SPEC_REFS[key]}) for key in CONCLUSION_KEYS
        ),
        "violations": [code for (code, _sev, _msg, _ev) in violations],
    }
    return (findings, [], summary)
