#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识语料清洗：剔除不产生有效实体的文本单元

问题背景
--------
data/artifacts/text_units.parquet 共 221 篇，其中 74 篇内容只有一行 PCGS 目录编号
（形如 `PCGS #709846`）。这类文本不携带任何语义，进入 GraphRAG 后只会抽出
`709846` 这种噪音实体（已在现有图谱中确认存在），并稀释向量检索的召回质量。

分类规则
--------
    纯编号   : 全文匹配 `PCGS #<数字>`
    单字段   : 形如 `发行时间：1898-1907`，只有一个字段
    术语表   : 含 DDO / DDR 等评级术语定义
    实质条目 : 其余

用法：
    python scripts/clean_corpus.py --dry-run     # 只统计
    python scripts/clean_corpus.py               # 输出清洗后的语料
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "data" / "artifacts"
SRC = ARTIFACTS / "text_units.parquet"

RE_PCGS_ONLY = re.compile(r"^\s*PCGS\s*#\s*\d+\s*$", re.I)
RE_SINGLE_FIELD = re.compile(r"^\s*[\u4e00-\u9fa5]{2,6}\s*[:：]\s*\S{1,40}\s*$")
TERMS = ("DDO", "DDR", "DMPL", "DCAM")


def classify(text: str) -> str:
    t = text.strip()
    if RE_PCGS_ONLY.match(t):
        return "纯编号"
    if RE_SINGLE_FIELD.match(t):
        return "单字段"
    if all(k in t for k in TERMS[:2]):
        return "术语表"
    if len(t) < 15:
        return "过短"
    return "实质条目"


def main() -> int:
    ap = argparse.ArgumentParser(description="知识语料清洗")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-chars", type=int, default=15, help="低于该长度视为无效")
    args = ap.parse_args()

    if not SRC.exists():
        print(f"错误：找不到 {SRC}", file=sys.stderr)
        return 2

    df = pd.read_parquet(SRC)
    if "text_unit" not in df.columns:
        print(f"错误：缺少 text_unit 列，实际列：{list(df.columns)}", file=sys.stderr)
        return 2

    texts = df["text_unit"].astype(str)
    cats = texts.map(classify)
    # 过短阈值可调
    cats = pd.Series(
        [("过短" if (c == "实质条目" and len(t.strip()) < args.min_chars) else c)
         for c, t in zip(cats, texts)],
        index=df.index,
    )

    print(f"来源：{SRC}")
    print(f"总篇数：{len(df)}   总字数：{int(texts.str.len().sum())}")
    print()
    print("分类统计：")
    for k, v in cats.value_counts().items():
        chars = int(texts[cats == k].str.len().sum())
        print(f"  {k:6s} {v:4d} 篇  {chars:6d} 字")
    print()

    keep = df[cats == "实质条目"].copy()
    drop = df[cats != "实质条目"].copy()
    print(f"保留 {len(keep)} 篇 / {int(keep['text_unit'].astype(str).str.len().sum())} 字")
    print(f"剔除 {len(drop)} 篇 / {int(drop['text_unit'].astype(str).str.len().sum())} 字")
    print()

    # 检查是否存在同内容的重复副本文件
    dup = ROOT / "data" / "text_units_df.parquet"
    if dup.exists():
        print(f"提示：{dup.relative_to(ROOT)} 也存在，是同一批语料的另一份副本，"
              f"入库时请统一以清洗后的文件为准。")
        print()

    if args.dry_run:
        print("--dry-run：未写出文件。")
        return 0

    out_pq = ARTIFACTS / "text_units_clean.parquet"
    out_csv = ARTIFACTS / "text_units_clean.csv"
    keep.to_parquet(out_pq, index=False)
    keep.assign(类别=cats[keep.index]).to_csv(out_csv, index=False, encoding="utf-8-sig")
    dropped = drop.assign(剔除原因=cats[drop.index])
    dropped[["document_id", "text_unit", "剔除原因"]].to_csv(
        ARTIFACTS / "text_units_dropped.csv", index=False, encoding="utf-8-sig")

    print(f"已写出：{out_pq.relative_to(ROOT)}")
    print(f"已写出：{out_csv.relative_to(ROOT)}")
    print(f"已写出：{(ARTIFACTS / 'text_units_dropped.csv').relative_to(ROOT)}（剔除清单，便于复核）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
