#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
按「同一枚钱币」为单位重新划分数据集（修复验证集泄漏）

问题背景
--------
training/kinds/model/split.py 用 sklearn 的 train_test_split 对**行**做随机切分。
但 make.py 为同一枚钱币生成了多行（原图 + gs/jy/rd 增强副本，共 5~9 行），
按行切分会让同一枚币的增强副本同时进入训练集和验证集，验证集因此包含训练时
见过的图像，指标虚高。

实测（修复前）：
    品相任务  训练集与验证集同名图像重叠 8,129 张
    分数任务  训练集与验证集同名图像重叠 3,643 张

修复方式
--------
1. 先把文件名归一化到「钱币编号」：去掉 gs/jy/rd 增强后缀
   （0gs.jpg / 0jy.jpg / 0.jpg 都归一为 0；1gs.jpg / 1.jpg 归一为 1）
2. 以「钱币对」（排序后的两个编号）为分组单位，整组落入同一集合
3. 分层：按标签比例切分，保证小类别也有训练样本
4. 输出前校验：任一集合之间不得有同名图像，也不得有同编号钱币

用法：
    python scripts/split_dataset.py --dry-run     # 只统计与校验
    python scripts/split_dataset.py               # 写 *_grouped.csv
    python scripts/split_dataset.py --in-place    # 覆盖原文件（先备份 .bak）
    python scripts/split_dataset.py --dedupe-identical
                                                   # 顺带去掉完全重复的行
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import random
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = {"kinds": "品相", "scores": "分数"}

# 增强后缀：make.py 写出 gs（高斯噪声）/ jy（椒盐噪声）/ rd（亮度+旋转）
AUG_SUFFIX = re.compile(r"^(?P<stem>.+?)(?:gs|jy|rd)?(?P<ext>\.\w+)$")


_LEADING_NUM = re.compile(r"^(\d+)")


def coin_id(path: str) -> str:
    """归一化到钱币编号

    训练数据里的文件名形如 0.jpg / 0gs.jpg / 0jy.jpg / 0rd.jpg / 90016gs1.jpg，
    同一枚钱币的所有增强副本都以同一个前导数字开头，因此取前导数字作为币号最稳。
    没有前导数字时退化为剥离增强后缀。
    """
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0] if "." in name else name
    m = _LEADING_NUM.match(stem)
    if m:
        return m.group(1)
    for suf in ("gs", "jy", "rd"):
        if stem.endswith(suf) and len(stem) > len(suf):
            return stem[: -len(suf)]
    return stem


def read_rows(path: Path) -> list[list[str]]:
    rows = []
    with io.open(path, encoding="utf-8-sig") as f:
        for line in f:
            parts = [x.strip() for x in line.strip().split(",")]
            if len(parts) >= 3:
                rows.append(parts)
    return rows


class CoinGraph:
    """并查集：把共用图像的钱币编号合并为同一连通分量

    实测发现部分图像被两个相邻钱币对共用（编号链式相连），
    仅按「钱币对」分组仍会让同一图像落入不同集合，
    因此需要先在编号层面求连通分量，以分量为分组单位。
    """

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:      # 路径压缩
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def group_of(self, row: list[str]) -> str:
        return self.find(coin_id(row[0]))


def split_groups(by_label, ratios, seed):
    train_r, val_r, _ = ratios
    train, val, test = [], [], []
    for label, groups in by_label.items():
        groups = sorted(groups, key=str)
        random.Random((seed * 7919) ^ (hash(label) & 0xFFFFFFFF)).shuffle(groups)
        n = len(groups)
        if n == 1:
            train.extend(groups)
            continue
        if n == 2:
            train.append(groups[0])
            val.append(groups[1])
            continue
        n_val = max(1, int(round(n * val_r)))
        n_test = max(1, int(round(n * (1 - train_r - val_r))))
        n_train = n - n_val - n_test
        if n_train < 1:
            n_train = 1
            n_val = max(1, min(n_val, n - 1))
            n_test = max(0, n - n_train - n_val)
        train.extend(groups[:n_train])
        val.extend(groups[n_train:n_train + n_val])
        test.extend(groups[n_train + n_val:])
    return set(train), set(val), set(test)


def overlap_report(split_rows: dict[str, list[list[str]]],
                   graph: "CoinGraph") -> dict[str, int]:
    """同时按『文件名』和『钱币』两种口径统计跨集合重叠"""
    out = {}
    names = list(split_rows)
    for kind, keyfunc in (("图像", lambda r: {r[0], r[1]}),
                          ("钱币", lambda r: {graph.group_of(r)})):
        sets = {k: set() for k in names}
        for k, rows in split_rows.items():
            for r in rows:
                sets[k] |= keyfunc(r)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                out[f"{kind} {a}∩{b}"] = len(sets[a] & sets[b])
    return out


def process(task, ratios, seed, in_place, dry_run, dedupe) -> bool:
    base_dir = ROOT / "training" / task
    data_csv = base_dir / "data.csv"
    if not data_csv.exists():
        print(f"  跳过：找不到 {data_csv}")
        return True

    rows = read_rows(data_csv)
    if not rows:
        print(f"  跳过：{data_csv} 为空")
        return True

    if dedupe:
        seen = set()
        uniq = []
        removed = 0
        for r in rows:
            h = hashlib.md5(",".join(r).encode("utf-8")).hexdigest()
            if h in seen:
                removed += 1
                continue
            seen.add(h)
            uniq.append(r)
        print(f"  去重：{len(rows)} -> {len(uniq)} 行（移除完全重复 {removed} 行）")
        rows = uniq

    graph = CoinGraph()
    for r in rows:
        graph.union(coin_id(r[0]), coin_id(r[1]))

    group_label: dict[str, str] = {}
    group_rows: dict[str, list[list[str]]] = collections.defaultdict(list)
    conflict = 0
    for r in rows:
        g = graph.group_of(r)
        if g in group_label and group_label[g] != r[-1]:
            conflict += 1
        group_label[g] = r[-1]
        group_rows[g].append(r)

    by_label: dict[str, list[tuple]] = collections.defaultdict(list)
    for g, lab in group_label.items():
        by_label[lab].append(g)

    tr, va, te = split_groups(by_label, ratios, seed)
    split_sets = {"train": tr, "val": va, "test": te}

    result_rows = {}
    for name, gs in split_sets.items():
        rs = []
        for g in gs:
            rs.extend(group_rows[g])
        result_rows[name] = rs

    rep = overlap_report(result_rows, graph)

    print(f"  [{TASKS[task]}] 行 {len(rows)} | 钱币 {len(group_label)} | 类别 {len(by_label)}"
          + (f" | 同组多标签 {conflict}" if conflict else ""))
    for name in ("train", "val", "test"):
        rs = result_rows[name]
        imgs, coins = set(), set()
        for r in rs:
            imgs.add(r[0]); imgs.add(r[1]); coins.add(graph.group_of(r))
        print(f"    {name:5s} 行 {len(rs):6d}  图像 {len(imgs):6d}  钱币 {len(coins):5d}")
    for k, v in rep.items():
        print(f"    重叠 {k}: {v}")

    ok = all(v == 0 for v in rep.values())
    print(f"    结论: {'✅ 无任何跨集合重叠' if ok else '❌ 仍有重叠'}")

    if dry_run:
        return ok

    suffix = "" if in_place else "_grouped"
    for name in ("train", "val", "test"):
        dst = base_dir / f"{name}{suffix}.csv"
        if in_place and (base_dir / f"{name}.csv").exists():
            shutil.copy2(base_dir / f"{name}.csv", base_dir / f"{name}.csv.bak")
        with io.open(dst, "w", encoding="utf-8", newline="\n") as f:
            for r in result_rows[name]:
                f.write(",".join(r) + "\n")
        print(f"    已写入 {dst.name}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="按钱币为单位重新划分数据集")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ratio", default="0.7,0.1,0.2", help="训练,验证,测试")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--in-place", action="store_true")
    ap.add_argument("--dedupe-identical", action="store_true", help="移除完全重复的行")
    args = ap.parse_args()

    ratios = tuple(float(x) for x in args.ratio.split(","))
    if len(ratios) != 3 or abs(sum(ratios) - 1.0) > 1e-6:
        print(f"错误：--ratio 三个数之和须为 1，当前 {ratios}")
        return 2

    print(f"划分比例 {ratios}  seed={args.seed}"
          + ("  （仅统计）" if args.dry_run else ""))
    ok = True
    for task in TASKS:
        ok &= process(task, ratios, args.seed, args.in_place, args.dry_run,
                      args.dedupe_identical)
    print()
    print("全部任务无重叠" if ok else "存在重叠，请检查")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
