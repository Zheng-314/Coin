#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
构建实体向量库（ChromaDB）

背景：后端 backend/services/__init__.py 启动时会用 LocalSearch 做本地检索，
它要求 data/vectors_stores 下的 ChromaDB 存在 collection「entity-embedding」且非空，
否则只走离线兜底。本脚本负责把 data/artifacts/entities.parquet 的实体嵌入写进去。

嵌入文本与元数据格式严格对齐 langchain_graphrag 的官方实现
（langchain_graphrag/indexing/artifacts_generation/entities.py）：
    文本   ：f"{title}:{description}"
    元数据 ：name / description / degree / entity_id
    id     ：entities.parquet 的 id 列
本地检索端（query/local_search/context_selectors/entities.py）依赖 metadata["entity_id"]
把检索结果映射回实体表，因此该字段不可省略。

用法：
    python scripts/build_vector_store.py --dry-run     # 只校验数据与配置，不调用接口
    python scripts/build_vector_store.py               # 真正建库
    python scripts/build_vector_store.py --rebuild     # 清空集合后重建
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from config import (  # noqa: E402
    ARTIFACTS_DIR,
    OPENAI_EMBED_API_BASE,
    OPENAI_EMBED_API_KEY,
    OPENAI_EMBED_MODEL,
    VECTOR_STORES_DIR,
)

COLLECTION_NAME = "entity-embedding"


def load_entity_records() -> tuple[list[str], list[dict], list[str]]:
    """从 entities.parquet 构造 文本 / 元数据 / id 三组数据"""
    path = ARTIFACTS_DIR / "entities.parquet"
    if not path.exists():
        raise FileNotFoundError(f"找不到实体文件：{path}")

    df = pd.read_parquet(path)
    for col in ("title", "description", "id"):
        if col not in df.columns:
            raise ValueError(f"entities.parquet 缺少必需列：{col}")

    texts, metadatas, ids = [], [], []
    for row in df.itertuples(index=False):
        title = "" if pd.isna(row.title) else str(row.title)
        desc = "" if pd.isna(row.description) else str(row.description)
        if not title and not desc:
            continue
        degree = getattr(row, "degree", None)
        texts.append(f"{title}:{desc}")
        metadatas.append({
            "name": title,
            "description": desc,
            "degree": None if pd.isna(degree) else int(degree),
            "entity_id": str(row.id),
        })
        ids.append(str(row.id))
    return texts, metadatas, ids


def main() -> int:
    ap = argparse.ArgumentParser(description="构建实体向量库")
    ap.add_argument("--dry-run", action="store_true", help="只校验，不调用嵌入接口")
    ap.add_argument("--rebuild", action="store_true", help="清空已有集合后重建")
    ap.add_argument("--batch-size", type=int, default=64, help="每批嵌入条数")
    args = ap.parse_args()

    print(f"项目根目录 : {PROJECT_ROOT}")
    print(f"实体文件   : {ARTIFACTS_DIR / 'entities.parquet'}")
    print(f"向量库目录 : {VECTOR_STORES_DIR}")
    print(f"嵌入模型   : {OPENAI_EMBED_MODEL}")
    print(f"嵌入接口   : {OPENAI_EMBED_API_BASE}")
    print(f"密钥       : {'已配置' if OPENAI_EMBED_API_KEY else '未配置！'}")
    print()

    if not OPENAI_EMBED_API_KEY:
        print("错误：.env 中没有 OPENAI_EMBED_API_KEY，无法生成嵌入。", file=sys.stderr)
        return 2

    texts, metadatas, ids = load_entity_records()
    print(f"读到实体 {len(texts)} 条")
    print(f"  文本样例：{texts[0][:70]}")
    print(f"  元数据键：{sorted(metadatas[0].keys())}")
    print()

    if args.dry_run:
        print("--dry-run：数据与配置校验通过，未调用嵌入接口。")
        return 0

    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    VECTOR_STORES_DIR.mkdir(parents=True, exist_ok=True)
    embeddings = OpenAIEmbeddings(
        model=OPENAI_EMBED_MODEL,
        base_url=OPENAI_EMBED_API_BASE,
        api_key=OPENAI_EMBED_API_KEY,
    )

    store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(VECTOR_STORES_DIR),
        embedding_function=embeddings,
    )

    if args.rebuild:
        try:
            store.reset_collection()
            print("已清空集合。")
        except Exception as exc:  # noqa: BLE001
            print(f"清空集合失败（忽略，继续追加）：{exc}")

    before = store._collection.count()
    print(f"入库前向量数：{before}")

    total = 0
    step = max(1, args.batch_size)
    for i in range(0, len(texts), step):
        store.add_texts(
            texts[i:i + step],
            metadatas=metadatas[i:i + step],
            ids=ids[i:i + step],
        )
        total += len(texts[i:i + step])
        print(f"  已写入 {total}/{len(texts)}")

    after = store._collection.count()
    print()
    print(f"入库后向量数：{after}")
    if after <= 0:
        print("错误：向量数为 0，建库失败。", file=sys.stderr)
        return 1
    print("建库完成。后端启动时本地检索即可用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
