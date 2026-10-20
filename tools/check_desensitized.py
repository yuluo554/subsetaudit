#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""脱敏门（发布前必跑，进 CI 的 layout job）。

为什么它是"门"而不是一次性 grep：发布之后任何一次文档改动都可能把本机路径带回来；
判据必须可跑红（命中时逐行打印 `文件:行: [规则] 原文`），不许静默通过。

四条规则（变异验证 V1–V4 各自对应一条）：
  V1  写一行 `D:/ProgramData/<something>`              → absolute-session-path
  V2  写 `C:\\Users\\<真实用户名>\\x`（非 `<user>` 占位）  → absolute-session-path + host-username
  V3  写 `/c/Users/<真实用户名>/x`                       → msys-user-path
  V4  写 `127.0.0.1:7897`                               → loopback-proxy

三条口径：
  ① 占位符必须放行（`<user>` / `<repo>` / `<local-proxy>`）——它们正是脱敏后的正确写法；
  ② 公开镜像不是私有代理（只认回环 / 私网）；
  ③ 门豁免自己，并把豁免份数打进结论行；worktree 里 `.git` 是文件不是目录，两态都跳过。
退出码：0 零命中 / 1 有命中 / 2 用法错误。
"""
from __future__ import print_function

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF = "tools/check_desensitized.py"

SKIP_DIRS = {
    ".git", ".tmp", "dist", "dist-release", "node_modules", ".cache",
    ".venv", "venv", "build", "_scratch", "__pycache__",
}
SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".gz", ".exe", ".dll",
    ".pdf", ".woff", ".woff2", ".ttf", ".otf", ".ttc", ".pyc",
}

RULES = [
    # 盘符绝对路径；`<repo>` / `<user>` 这类占位符放行（负向前瞻）
    ("absolute-session-path",
     re.compile(r"\b[A-Za-z]:[\\/](?:ProgramData|Users|zcode|repos?|projects?)[\\/](?!<)")),
    # Git Bash 形态 `/c/Users/<name>/…`
    ("msys-user-path", re.compile(r"/[a-z]/Users/(?!<)[A-Za-z0-9._-]+/")),
    # 本机用户名（换机器改这一行；别用环境实算——runner 上叫 runner）
    ("host-username", re.compile(r"\bASUS\b")),
    # 回环代理端口；私网段同理可加
    ("loopback-proxy", re.compile(r"\b127\.0\.0\.1:\d{2,5}\b")),
]


def walk(directory):
    for entry in sorted(os.listdir(directory)):
        path = os.path.join(directory, entry)
        if entry == ".git":  # 目录形态与 worktree 文件形态一起挡
            continue
        if os.path.isdir(path):
            if entry in SKIP_DIRS:
                continue
            for item in walk(path):
                yield item
            continue
        if not os.path.isfile(path):
            continue
        _, ext = os.path.splitext(entry)
        if ext.lower() in SKIP_EXTS:
            continue
        yield path


def main(argv):
    if argv:
        sys.stderr.write("check_desensitized: 不接受参数 %r\n" % (argv,))
        return 2

    hits = []
    scanned = 0
    for path in walk(ROOT):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if rel == SELF:
            continue  # 自豁免（规则本身必须写出被禁的字面量）
        try:
            with io.open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        if "\u0000" in text:
            continue  # 二进制
        scanned += 1
        for lineno, line in enumerate(text.split("\n"), 1):
            for rule_id, pattern in RULES:
                if pattern.search(line):
                    hits.append("%s:%d: [%s] %s" % (rel, lineno, rule_id, line.strip()[:160]))

    out = io.open(sys.stdout.fileno(), "w", encoding="utf-8", closefd=False) \
        if hasattr(sys.stdout, "fileno") else sys.stdout
    if hits:
        out.write("脱敏门：%d 处命中（扫了 %d 个文本文件，豁免 %s）\n" % (len(hits), scanned, SELF))
        for hit in hits:
            out.write("FAIL  %s\n" % hit)
        out.flush()
        return 1
    out.write("脱敏门：扫了 %d 个文本文件，0 命中（豁免 %s）\n" % (scanned, SELF))
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
