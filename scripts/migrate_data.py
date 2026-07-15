"""数据迁移脚本 — 合并 images + coindata → 统一仓库"""
import os, sys, csv, shutil, re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
os.makedirs(RAW_DIR, exist_ok=True)

# ============================================================
# 1. 从 data/images/ 复制（改写命名）
# ============================================================
images_dir = DATA_DIR / "images"
img_src_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
done = set()
n_images = 0
for f in img_src_files:
    name = f.name
    # 已经是 {id}_front.jpg 格式
    target = RAW_DIR / name
    if not target.exists():
        shutil.copy2(f, target)
    done.add(name)
    n_images += 1
print(f"[1/5] data/images/ → raw/: {n_images} 张")

# ============================================================
# 2. 从 coindata 复制（改写命名：Photo_xxx.jpg → {id}_{front/back}.jpg）
# ============================================================
coindata_dir = Path("D:/coindata")
metadata_rows = []
n_coindata = 0
n_label = 0

for grade_dir in coindata_dir.iterdir():
    if not grade_dir.is_dir():
        continue
    for cert_dir in grade_dir.iterdir():
        if not cert_dir.is_dir():
            continue
        pcgs_id = cert_dir.name
        if not pcgs_id.isdigit():
            continue

        # 读取 label.txt
        label_file = cert_dir / "label.txt"
        coin_name, kind, score, year = "", "", "", ""
        if label_file.exists():
            try:
                with open(label_file, "r", encoding="utf-8") as f:
                    text = f.read()
                m = re.search(r"名称：(.+)", text)
                if m:
                    coin_name = m.group(1).strip()
                m = re.search(r"分数：([A-Z]+)\s*(\d+)", text)
                if m:
                    kind = m.group(1)
                    score = m.group(2)
                m = re.search(r"年份：(\d+)", text)
                if m:
                    year = m.group(1)
                n_label += 1
            except Exception:
                pass

        # 复制图片
        jpgs = sorted(cert_dir.glob("*.jpg"))
        front_file, back_file = None, None
        for jpg in jpgs:
            if jpg.name.endswith("-1.jpg"):
                back_file = jpg
            else:
                front_file = jpg

        if front_file:
            target = RAW_DIR / f"{pcgs_id}_front.jpg"
            if not target.exists():
                shutil.copy2(front_file, target)
            n_coindata += 1

        if back_file:
            target = RAW_DIR / f"{pcgs_id}_back.jpg"
            if not target.exists():
                shutil.copy2(back_file, target)
            n_coindata += 1

        # 记录元数据
        if front_file and back_file:
            metadata_rows.append({
                "pcgs_id": pcgs_id,
                "coin_name": coin_name,
                "kind": kind,
                "score": score,
                "year": year,
                "source": "coindata",
            })

print(f"[2/5] coindata → raw/: {n_coindata} 张, label.txt {n_label} 个")

# ============================================================
# 3. 从 coins.csv 补充 images 来源的元数据
# ============================================================
coins_csv = ROOT / "training" / "coins.csv"
coindata_ids = {r["pcgs_id"] for r in metadata_rows}
n_csv = 0
with open(coins_csv, "r", encoding="utf-8") as f:
    reader = csv.reader(f, delimiter="\t")
    for row in reader:
        if len(row) < 2:
            continue
        pcgs_id = row[0]
        if pcgs_id in coindata_ids:
            continue  # coindata 已有
        # 检查 raw/ 里有没有这个 id 的图
        if (RAW_DIR / f"{pcgs_id}_front.jpg").exists() and (RAW_DIR / f"{pcgs_id}_back.jpg").exists():
            coin_name = row[1] if len(row) > 1 else ""
            kind = row[4] if len(row) > 4 else ""
            score = row[5] if len(row) > 5 else ""
            year = row[6] if len(row) > 6 else ""
            metadata_rows.append({
                "pcgs_id": pcgs_id,
                "coin_name": coin_name,
                "kind": kind,
                "score": score,
                "year": year,
                "source": "coins.csv",
            })
            n_csv += 1

print(f"[3/5] coins.csv 补充: {n_csv} 条")

# ============================================================
# 4. 扫描 raw/ 中还没有元数据的图片
# ============================================================
known_ids = {r["pcgs_id"] for r in metadata_rows}
orphans = []
for f in RAW_DIR.glob("*_front.jpg"):
    pid = f.name.replace("_front.jpg", "")
    if pid not in known_ids:
        orphans.append({"pcgs_id": pid, "coin_name": "", "kind": "", "score": "", "year": "", "source": "raw_only"})
        known_ids.add(pid)

metadata_rows.extend(orphans)
print(f"[4/5] raw/ 中无标签图片: {len(orphans)} 枚")

# ============================================================
# 5. 写 metadata.csv
# ============================================================
meta_csv = DATA_DIR / "metadata.csv"
with open(meta_csv, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["pcgs_id", "coin_name", "kind", "score", "year", "source"])
    writer.writeheader()
    writer.writerows(metadata_rows)

# 统计
total_ids = len(metadata_rows)
with_name = sum(1 for r in metadata_rows if r["coin_name"])
with_kind = sum(1 for r in metadata_rows if r["kind"])
with_score = sum(1 for r in metadata_rows if r["score"])

raw_fronts = len(list(RAW_DIR.glob("*_front.jpg")))
raw_backs = len(list(RAW_DIR.glob("*_back.jpg")))

print(f"\n[5/5] metadata.csv 已生成: {DATA_DIR / 'metadata.csv'}")
print(f"\n{'='*50}")
print(f"  迁移完成")
print(f"{'='*50}")
print(f"  raw/ 正面图: {raw_fronts} 张")
print(f"  raw/ 反面图: {raw_backs} 张")
print(f"  唯一证书:   {total_ids} 枚")
print(f"  有名:     {with_name} ({100*with_name//max(1,total_ids)}%)")
print(f"  有品相:   {with_kind} ({100*with_kind//max(1,total_ids)}%)")
print(f"  有分数:   {with_score} ({100*with_score//max(1,total_ids)}%)")
print(f"  无标签孤儿: {len(orphans)} 枚")
