#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从知识语料中抽取「部位级」鉴别要点，产出 data/authenticity/part_hints.json

用途
----
真伪鉴定需要的不只是一张二分类打分，还需要告诉用户「看哪里」。
现成语料里有一部分句子带明确部位（边齿 / 珠圈 / 字口 / 包浆 / 重量 / 声音），
本脚本把它们抽出来，作为真伪鉴定功能的提示库。

注意：本脚本只做抽取，不做改写、不补充语料中不存在的事实。

用法：
    python scripts/build_authenticity_hints.py --dry-run
    python scripts/build_authenticity_hints.py
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "artifacts" / "text_units_clean.csv"
FALLBACK_SRC = ROOT / "data" / "artifacts" / "text_units.parquet"
OUT = ROOT / "data" / "authenticity" / "part_hints.json"

PARTS = {
    "边齿": ["边齿", "齿边", "齿纹"],
    "珠圈": ["珠圈", "点珠"],
    "字口": ["字口", "文字笔画", "笔画"],
    "包浆": ["包浆", "浆色", "原光"],
    "重量": ["重量", "克重", "重约"],
    "声音": ["声音", "音色", "吹响"],
}

# 判定「是否是鉴别性表述」的关键词：出现仿品/真品/假/赝等对比词
JUDGE_WORDS = ("仿品", "赝品", "假币", "真品", "正品", "伪造", "仿制", "必为", "多为")
SENT_SPLIT = re.compile(r"[。；;\n]")
# 形制/特征描述用词：句子需同时含部位词与下列任一词，才认定为描述性内容
DESC_WORDS = ("深峻", "清晰", "规整", "自然", "细腻", "饱满", "立体", "紧密",
              "排列", "均匀", "刚劲", "挺括", "流畅", "平整", "磨损", "氧化")
MAX_LEN = 120


def load_texts() -> list[tuple[str, str]]:
    """返回 [(document_id, text)]"""
    if SRC.exists():
        df = pd.read_csv(SRC)
    elif FALLBACK_SRC.exists():
        df = pd.read_parquet(FALLBACK_SRC)
    else:
        raise FileNotFoundError(f"找不到语料：{SRC} 或 {FALLBACK_SRC}")
    col = "text_unit" if "text_unit" in df.columns else df.columns[0]
    ids = df["document_id"] if "document_id" in df.columns else pd.Series(range(len(df)))
    return [(str(i), str(t)) for i, t in zip(ids, df[col])]


def extract(texts) -> list[dict]:
    hints = []
    seen = set()
    for doc_id, text in texts:
        for sent in SENT_SPLIT.split(text):
            sent = sent.strip()
            if len(sent) < 8 or len(sent) > MAX_LEN:
                continue
            parts = [p for p, kws in PARTS.items() if any(k in sent for k in kws)]
            if not parts:
                continue
            judged = any(w in sent for w in JUDGE_WORDS)
            descriptive = any(w in sent for w in DESC_WORDS)
            if not (judged or descriptive):
                continue
            # 鉴别性表述优先；非鉴别性的形制描述也保留，但标记 judged=false
            key = (sent, tuple(parts))
            if key in seen:
                continue
            seen.add(key)
            hints.append({
                "part": parts[0],
                "parts": parts,
                "text": sent,
                "judged": judged,
                "source": f"text_units#{doc_id}",
            })
    # 有判断词的排前面
    hints.sort(key=lambda h: (not h["judged"], -len(h["text"])))
    return hints


def main() -> int:
    ap = argparse.ArgumentParser(description="抽取部位级鉴别要点")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    texts = load_texts()
    hints = extract(texts)

    by_part = {}
    for p in PARTS:
        by_part[p] = [h["text"] for h in hints if h["part"] == p][:20]

    print(f"语料 {len(texts)} 篇，抽出部位相关句子 {len(hints)} 条")
    print(f"其中带鉴别判断词的 {sum(1 for h in hints if h['judged'])} 条")
    print()
    for p in PARTS:
        print(f"  {p:4s} {len(by_part[p]):3d} 条")
    print()
    print("示例：")
    for h in hints[:6]:
        print(f"  [{h['part']}] {h['text'][:56]}")

    if args.dry_run:
        print("\n--dry-run：未写出。")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "note": "由 scripts/build_authenticity_hints.py 从知识语料抽取，仅含语料原文，未做补充。",
        "parts": list(PARTS.keys()),
        "hints": hints,
        "by_part": by_part,
    }
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"\n已写出 {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
