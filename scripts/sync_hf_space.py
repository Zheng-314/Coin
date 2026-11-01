#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把 backend/ 的源码同步到 hf-space/backend/

问题背景
--------
hf-space/backend 是 backend 的一份部署副本，供 HuggingFace Spaces 使用。
两份代码手工维护，已经出现漂移：hf-space 那份缺少限流器、缺少同源前端伺服、
向量库报错信息也不同。漂移会让"本地能跑、线上不行"这类问题难以定位。

同步范围
--------
只同步 Python 源码（含子目录），不同步：
    .env / .env.*      密钥，必须各环境独立
    instance/          运行时数据库
    venv/ .venv/       虚拟环境
    __pycache__/       字节码
    *.log              日志
    best_model.onnx 等大文件（由 HF Space 侧单独管理）

用法：
    python scripts/sync_hf_space.py --dry-run   # 只列出将要变更的文件
    python scripts/sync_hf_space.py             # 执行同步
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "backend"
DST = ROOT / "hf-space" / "backend"

SKIP_DIRS = {"__pycache__", "venv", ".venv", "instance", ".git", "node_modules"}
SKIP_SUFFIX = {".log", ".db", ".sqlite3", ".onnx", ".pt", ".pth", ".om"}
SKIP_NAMES = {".env", ".DS_Store", "Thumbs.db"}


def should_skip(path: Path, base: Path) -> bool:
    rel = path.relative_to(base)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if path.name in SKIP_NAMES or path.name.startswith(".env"):
        return True
    return path.suffix in SKIP_SUFFIX


def main() -> int:
    ap = argparse.ArgumentParser(description="同步 backend -> hf-space/backend")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SRC.is_dir():
        print(f"错误：找不到源目录 {SRC}", file=sys.stderr)
        return 2
    if not DST.is_dir():
        print(f"错误：找不到目标目录 {DST}", file=sys.stderr)
        return 2

    files = [p for p in SRC.rglob("*") if p.is_file() and not should_skip(p, SRC)]
    new, changed, same = [], [], 0
    for f in files:
        rel = f.relative_to(SRC)
        target = DST / rel
        if not target.exists():
            new.append(rel)
        elif not filecmp.cmp(f, target, shallow=False):
            changed.append(rel)
        else:
            same += 1

    print(f"源目录：{SRC.relative_to(ROOT)}")
    print(f"目标目录：{DST.relative_to(ROOT)}")
    print(f"待检查文件 {len(files)} 个：新增 {len(new)}，内容不同 {len(changed)}，一致 {same}")
    print()
    for r in new:
        print(f"  [新增] {r}")
    for r in changed:
        print(f"  [修改] {r}")

    if not new and not changed:
        print("两份代码已一致，无需同步。")
        return 0

    if args.dry_run:
        print("\n--dry-run：未写入。")
        return 0

    for rel in new + changed:
        src = SRC / rel
        dst = DST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"\n已同步 {len(new) + len(changed)} 个文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
