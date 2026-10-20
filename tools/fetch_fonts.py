#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OFL 字体获取与校验（M1）。

纪律（`data/README.md` §八、`plan/04` §3）：

  · **字体二进制永不入仓**：本脚本把文件放到 ``data/fonts/``（``.gitignore`` 已阻断）；
  · **默认不联网**：无参数等价于 ``--check``，只校验 ``data/fonts/`` 已有文件的
    字节数与 sha256，**不发起任何网络请求**（``urllib`` 只在 ``--download`` 分支内 import）；
  · **缺文件不崩**：报 ``MISSING`` 并 exit 1，而不是抛异常；
  · **哈希不符**：报 ``MISMATCH`` 并 exit 1（逐文件给出 期望/实得）。

用法::

    py tools/fetch_fonts.py                  # = --check（离线）
    py tools/fetch_fonts.py --check          # 同上
    py tools/fetch_fonts.py --download       # 联网补齐缺失文件（用户显式触发）
    py tools/fetch_fonts.py --list           # 只列锁文件登记项，不读写磁盘之外的状态

退出码：0 全部在位且哈希一致 / 1 有 MISSING 或 MISMATCH / 2 用法错误。
"""
from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(ROOT, "data", "fonts.lock")
FONT_DIR = os.path.join(ROOT, "data", "fonts")

CHUNK = 1 << 20


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def load_lock(path=LOCK):
    """读锁文件（3.8 可解析的 JSON）。结构非法 → ``ValueError``（由 main 收口为 2）。"""
    with io.open(path, "r", encoding="utf-8") as fh:
        body = json.load(fh)
    if body.get("version") != 1:
        raise ValueError("fonts.lock version 必须是 1，实得 %r" % (body.get("version"),))
    fonts = body.get("fonts")
    if not isinstance(fonts, list) or not fonts:
        raise ValueError("fonts.lock 的 fonts 必须是非空数组")
    for entry in fonts:
        for field in ("name", "url", "bytes", "sha256", "license"):
            if field not in entry:
                raise ValueError("fonts.lock 条目缺字段 %r: %r" % (field, entry.get("name")))
        sha = str(entry["sha256"]).lower()
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("fonts.lock 条目 sha256 非法: %r" % (entry.get("name"),))
    return body


def check(entries, font_dir=FONT_DIR, verbose=True):
    """离线校验：返回 ``(problems, report)``；``report`` 每项含 name/status/detail。"""
    problems = []
    report = []
    for entry in entries:
        name = entry["name"]
        path = os.path.join(font_dir, name)
        if not os.path.isfile(path):
            detail = "MISSING %s（期望 %d B sha=%s…）" % (name, entry["bytes"],
                                                        entry["sha256"][:16])
            problems.append(detail)
            report.append({"name": name, "status": "MISSING", "detail": "not downloaded"})
            if verbose:
                print("  MISSING   %-28s 期望 %d B" % (name, entry["bytes"]))
            continue
        size = os.path.getsize(path)
        if size != entry["bytes"]:
            detail = "MISMATCH %s 字节数 实得 %d / 期望 %d" % (name, size, entry["bytes"])
            problems.append(detail)
            report.append({"name": name, "status": "MISMATCH",
                           "detail": "bytes %d != %d" % (size, entry["bytes"])})
            if verbose:
                print("  MISMATCH  %-28s 字节数 %d != %d" % (name, size, entry["bytes"]))
            continue
        digest = _sha256_file(path)
        if digest != entry["sha256"].lower():
            detail = "MISMATCH %s sha256 实得 %s / 期望 %s" % (name, digest, entry["sha256"])
            problems.append(detail)
            report.append({"name": name, "status": "MISMATCH",
                           "detail": "sha256 %s != %s" % (digest, entry["sha256"])})
            if verbose:
                print("  MISMATCH  %-28s sha256 %s… != %s…"
                      % (name, digest[:16], entry["sha256"][:16]))
            continue
        report.append({"name": name, "status": "OK", "detail": digest})
        if verbose:
            print("  OK        %-28s %9d B  sha=%s…" % (name, size, digest[:16]))
    return problems, report


def _download_bytes(url):
    """**唯一**联网入口：``urllib`` 在这里才 import（``--check`` 路径不会触发）。"""
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "subsetaudit-fetch/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def download(entries, font_dir=FONT_DIR, verbose=True):
    """联网补齐缺失文件。返回 ``(problems, report)``；已存在的文件不重复下载。"""
    if not os.path.isdir(font_dir):
        os.makedirs(font_dir)
    problems = []
    report = []
    for entry in entries:
        name = entry["name"]
        target = os.path.join(font_dir, name)
        if os.path.isfile(target) and os.path.getsize(target) == entry["bytes"] \
                and _sha256_file(target) == entry["sha256"].lower():
            if verbose:
                print("  SKIP      %-28s 已存在且哈希一致" % name)
            report.append({"name": name, "status": "OK", "detail": "already present"})
            continue
        try:
            if verbose:
                print("  DOWNLOAD  %-28s %s" % (name, entry["url"]))
            payload = _download_bytes(entry["url"])
            member = entry.get("archive_member")
            if member:
                import tempfile

                handle, tmp_zip = tempfile.mkstemp(suffix=".zip")
                os.close(handle)
                try:
                    with open(tmp_zip, "wb") as fh:
                        fh.write(payload)
                    archive = entry.get("archive") or {}
                    if archive.get("sha256"):
                        got = _sha256_file(tmp_zip)
                        if got != archive["sha256"].lower():
                            raise ValueError("压缩包 sha256 不符: %s" % got)
                    with zipfile.ZipFile(tmp_zip) as zf:
                        payload = zf.read(member)
                finally:
                    if os.path.exists(tmp_zip):
                        os.remove(tmp_zip)
        except Exception as exc:  # noqa: BLE001 - 网络异常类型随平台变
            detail = "DOWNLOAD_FAILED %s（%s: %s）" % (name, exc.__class__.__name__, exc)
            problems.append(detail)
            report.append({"name": name, "status": "DOWNLOAD_FAILED",
                           "detail": exc.__class__.__name__})
            if verbose:
                print("  FAILED    %-28s %s" % (name, exc.__class__.__name__))
            continue
        digest = hashlib.sha256(payload).hexdigest()
        if len(payload) != entry["bytes"] or digest != entry["sha256"].lower():
            detail = "MISMATCH %s 下载内容与锁文件不符（%d B / %s）" % (name, len(payload), digest)
            problems.append(detail)
            report.append({"name": name, "status": "MISMATCH", "detail": digest})
            if verbose:
                print("  MISMATCH  %-28s 下载内容与锁文件不符" % name)
            continue
        with open(target, "wb") as fh:
            fh.write(payload)
        report.append({"name": name, "status": "OK", "detail": "downloaded"})
        if verbose:
            print("  OK        %-28s %9d B  sha=%s…" % (name, len(payload), digest[:16]))
    return problems, report


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fetch_fonts.py",
        description="校验 / 下载 data/fonts.lock 登记的 OFL 字体（默认离线 --check）。",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="离线校验已有文件（默认行为）")
    group.add_argument("--download", action="store_true", help="联网补齐缺失文件（需显式触发）")
    group.add_argument("--list", action="store_true", help="只列出锁文件登记项")
    parser.add_argument("--dir", metavar="DIR", default=FONT_DIR,
                        help="字体目录（默认 data/fonts）")
    args = parser.parse_args(argv)

    try:
        body = load_lock()
    except (OSError, ValueError) as exc:
        sys.stderr.write("fonts.lock 不可用: %s\n" % exc)
        return 2
    entries = body["fonts"]

    if args.list:
        print("data/fonts.lock：%d 个字体" % len(entries))
        for entry in entries:
            print("  %-28s %-10s %9d B  %s" % (entry["name"], entry["license"],
                                              entry["bytes"], entry["family"]))
        return 0

    font_dir = args.dir if os.path.isabs(args.dir) else os.path.join(ROOT, args.dir)

    if args.download:
        print("fetch_fonts --download：联网补齐 → %s"
              % os.path.relpath(font_dir, ROOT).replace(os.sep, "/"))
        problems, _report = download(entries, font_dir)
        print("结论: %s" % ("全部在位" if not problems else "发现 %d 处问题" % len(problems)))
        return 0 if not problems else 1

    print("fetch_fonts --check：离线校验 %d 个字体（不联网）" % len(entries))
    problems, _report = check(entries, font_dir)
    print("结论: %s" % ("全部在位且哈希一致" if not problems
                        else "发现 %d 处问题（缺文件用 --download 获取）" % len(problems)))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
