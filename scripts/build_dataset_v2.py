"""版式识别数据集构建 v2 — 从 data/raw/ + metadata.csv 构建"""
import os, sys, csv, json
from pathlib import Path
from collections import Counter

import cv2, numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
META_CSV = DATA_DIR / "metadata.csv"
OUT_DIR = DATA_DIR / "processed"
CROP_DIR = OUT_DIR / "crops"
SPLIT_DIR = OUT_DIR / "splits"

os.makedirs(CROP_DIR, exist_ok=True)
os.makedirs(SPLIT_DIR, exist_ok=True)

# ============================================================
# 1. 加载 92 类名
# ============================================================
with open(ROOT / "backend" / "instance" / "classification.json", "r", encoding="utf-8") as f:
    cls_tree = json.load(f)


def flatten_tree(node, prefix=""):
    result = []
    if isinstance(node, dict):
        name = node.get("unicode", "")
        new_prefix = f"{prefix} > {name}" if prefix else name
        childs = node.get("childs")
        if isinstance(childs, dict) and childs:
            for child in childs.values():
                result.extend(flatten_tree(child, new_prefix))
        elif isinstance(childs, list) and childs:
            for child in childs:
                result.extend(flatten_tree(child, new_prefix))
        else:
            result.append({"path": new_prefix, "name": name})
    return result


CLASS_LIST = flatten_tree(cls_tree["jizhiyinbi"])
CLASS_IDX = {c["path"]: i for i, c in enumerate(CLASS_LIST)}
print(f"92 类叶子节点: {len(CLASS_LIST)}")

# ============================================================
# 2. 读取 metadata.csv，收集有效配对
# ============================================================
pairs = []
with open(META_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pid = row["pcgs_id"]
        name = row["coin_name"]
        front = RAW_DIR / f"{pid}_front.jpg"
        back = RAW_DIR / f"{pid}_back.jpg"
        if front.exists() and back.exists() and name:
            pairs.append((pid, name))

print(f"有效正反面对: {len(pairs)}")

# ============================================================
# 3. 币名 → 92类映射
# ============================================================
KEYWORDS = [
    "袁大头", "袁世凯", "孙小头", "孙中山", "黎元洪", "段祺瑞", "曹锟", "徐世昌", "唐继尧",
    "光绪元宝", "宣统元宝", "大清银币", "开国纪念", "龙凤", "三帆", "船洋",
    "孙像三鸟", "孙像船洋", "湖南省宪", "四川军政府", "富字", "鹿头",
    "壹圆", "中圆", "贰角", "壹角", "五角", "半圆", "七钱二分", "三钱六分",
    "一两", "半两", "贰毫", "壹毫",
    "普通", "精发", "粗发", "O版", "三角圆", "甘肃", "海南", "中央", "T点年",
    "湖北省造", "四川省造", "广东省造", "云南省造", "江南省造", "北洋造",
    "东三省", "吉林省造", "奉天", "新疆", "西藏",
    "军政府", "光绪", "富字一两", "富字半两", "鹿头一两",
]


def match_class(coin_name):
    keywords = [coin_name]
    for kw in KEYWORDS:
        if kw in coin_name:
            keywords.append(kw)
    best_score, best_path = 0, None
    clean_name = coin_name.replace(" ", "")
    for c in CLASS_LIST:
        clean_path = c["path"].replace(" ", "")
        score = 0
        for kw in keywords:
            if kw.replace(" ", "") in clean_path:
                score += len(kw) * 2
        if score == 0:
            score = sum(1 for ch in clean_name if ch in clean_path)
        if score > best_score:
            best_score = score
            best_path = c["path"]
    return best_path, best_score


label_data = []
unmatched = Counter()
for pid, name in pairs:
    cls_path, score = match_class(name)
    if cls_path:
        label_data.append((pid, name, cls_path))
    else:
        unmatched[name] += 1

print(f"成功映射: {len(label_data)}, 未匹配: {len(unmatched)} 种币名")

# ============================================================
# 4. YOLO 裁剪
# ============================================================
print("\n加载 YOLO...")
model = YOLO(str(ROOT / "backend" / "best1.pt"))
print(f"开始裁剪 {len(label_data)} 对...")

cropped = []
n_skipped = 0
for i, (pid, name, cls_path) in enumerate(label_data):
    if (i + 1) % 1000 == 0:
        print(f"  进度: {i+1}/{len(label_data)}")

    pair_ok = True
    crops = []
    for side in ["front", "back"]:
        img = cv2.imread(str(RAW_DIR / f"{pid}_{side}.jpg"))
        if img is None:
            pair_ok = False
            break
        results = model(img, verbose=False)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            pair_ok = False
            break
        best_idx = boxes.conf.argmax().item()
        xyxy = boxes.xyxy[best_idx].cpu().numpy()
        x1, y1, x2, y2 = map(int, xyxy)
        h, w = img.shape[:2]
        x1, y1 = max(0, x1 - 10), max(0, y1 - 10)
        x2, y2 = min(w, x2 + 10), min(h, y2 + 10)
        crops.append(img[y1:y2, x1:x2])

    if not pair_ok:
        n_skipped += 1
        continue

    out_front = CROP_DIR / f"{pid}_front_crop.jpg"
    out_back = CROP_DIR / f"{pid}_back_crop.jpg"
    cv2.imwrite(str(out_front), crops[0])
    cv2.imwrite(str(out_back), crops[1])

    cls_id = CLASS_IDX[cls_path]
    cropped.append((f"{pid}_front_crop.jpg", f"{pid}_back_crop.jpg", cls_id, cls_path, name))

print(f"裁剪完成: {len(cropped)} 对, 跳过 {n_skipped} 对")

# ============================================================
# 5. 保存 labels.csv
# ============================================================
with open(OUT_DIR / "labels.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["front_img", "back_img", "class_id", "class_path", "coin_name"])
    for row in cropped:
        writer.writerow(row)

# ============================================================
# 6. 分层划分 70/15/15
# ============================================================
rng = np.random.RandomState(42)
y = [r[2] for r in cropped]
class_counts = Counter(y)
valid_classes = {c for c, n in class_counts.items() if n >= 3}
valid_indices = [i for i in range(len(y)) if y[i] in valid_classes]
valid_labels = [y[i] for i in valid_indices]

indices = list(range(len(valid_labels)))


def stratified_split(labels_list, test_ratio):
    unique = list(set(labels_list))
    train_idx, test_idx = [], []
    idx_by_label = {lbl: [i for i in range(len(labels_list)) if labels_list[i] == lbl] for lbl in unique}
    for lbl in unique:
        lbl_idx = idx_by_label[lbl]
        rng.shuffle(lbl_idx)
        n_test = max(1, int(len(lbl_idx) * test_ratio))
        test_idx.extend(lbl_idx[:n_test])
        train_idx.extend(lbl_idx[n_test:])
    rng.shuffle(train_idx)
    rng.shuffle(test_idx)
    return train_idx, test_idx


train, temp = stratified_split(valid_labels, 0.3)
temp_labels_sub = [valid_labels[i] for i in temp]
val, test = stratified_split(temp_labels_sub, 0.5)

for split_name, split_indices in [("train", train), ("val", val), ("test", test)]:
    out_file = SPLIT_DIR / f"{split_name}.csv"
    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["front_img", "back_img", "class_id"])
        for i in split_indices:
            orig_idx = valid_indices[i]
            r = cropped[orig_idx]
            writer.writerow([r[0], r[1], r[2]])
    print(f"  {split_name}: {len(split_indices)} 对")

n_classes = len(set(r[2] for r in cropped))
print(f"\n=== 完成 ===")
print(f"总图片对: {len(cropped)}")
print(f"类别数: {n_classes}/{len(CLASS_LIST)}")
print(f"跳过(检测失败): {n_skipped}")
