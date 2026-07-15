"""构建版式识别数据集 — YOLO裁剪 + 92类标签映射 + train/val/test划分"""
import os, sys, csv, json, shutil
from pathlib import Path
from collections import Counter

import cv2, numpy as np
from ultralytics import YOLO

def stratified_split(items, labels, test_size, random_state=42):
    """手动分层划分，不依赖 sklearn"""
    rng = np.random.RandomState(random_state)
    unique_labels = list(set(labels))
    train_idx, test_idx = [], []
    for lbl in unique_labels:
        lbl_indices = [i for i in range(len(items)) if labels[i] == lbl]
        rng.shuffle(lbl_indices)
        n_test = max(1, int(len(lbl_indices) * test_size))
        test_idx.extend(lbl_indices[:n_test])
        train_idx.extend(lbl_indices[n_test:])
    rng.shuffle(train_idx)
    rng.shuffle(test_idx)
    return train_idx, test_idx

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
IMG_DIR = DATA_DIR / "images"
OUT_DIR = DATA_DIR / "processed"
CROP_DIR = OUT_DIR / "crops"
SPLIT_DIR = OUT_DIR / "splits"

os.makedirs(CROP_DIR, exist_ok=True)
os.makedirs(SPLIT_DIR, exist_ok=True)

# ============================================================
# 1. 加载 92 类名（按 ONNX 输出的顺序）
# ============================================================
with open(ROOT / "backend" / "instance" / "classification.json", "r", encoding="utf-8") as f:
    cls_tree = json.load(f)


def flatten_tree(node, prefix=""):
    """展平分类树为列表 [{'path': '机制银币 > 地方省造 > ...', 'name': '普通'}, ...]"""
    result = []
    if isinstance(node, dict):
        name = node.get("unicode", "")
        new_prefix = f"{prefix} > {name}" if prefix else name
        childs = node.get("childs")
        if isinstance(childs, dict) and childs:
            for _key, child in childs.items():
                result.extend(flatten_tree(child, new_prefix))
        elif isinstance(childs, list) and childs:
            for child in childs:
                result.extend(flatten_tree(child, new_prefix))
        else:
            result.append({"path": new_prefix, "name": name})
    return result


CLASS_LIST = flatten_tree(cls_tree["jizhiyinbi"])
CLASS_IDX = {c["path"]: i for i, c in enumerate(CLASS_LIST)}
print(f"92 类叶子节点数: {len(CLASS_LIST)}")
print(f"前5类: {[c['path'][:50] for c in CLASS_LIST[:5]]}")

# ============================================================
# 2. 匹配 coins.csv → data/images/
# ============================================================
imgs = set(os.listdir(IMG_DIR))
matched = []
with open(ROOT / "training" / "coins.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f, delimiter="\t")
    for row in reader:
        if len(row) < 2:
            continue
        pid, name = row[0], row[1].strip()
        front = f"{pid}_front.jpg"
        back = f"{pid}_back.jpg"
        if front in imgs and back in imgs:
            matched.append((pid, name, front, back))

print(f"匹配到完整正反面图片: {len(matched)} 对")

# ============================================================
# 3. 币名 → 92类映射
# ============================================================


def extract_keywords(name):
    """从币名中提取关键词"""
    keywords = [name]  # 完整名称
    for kw in ["袁大头", "袁世凯", "孙小头", "孙中山", "黎元洪", "段祺瑞", "曹锟", "徐世昌", "唐继尧",
               "光绪元宝", "宣统元宝", "大清银币", "开国纪念", "龙凤", "三帆", "船洋",
               "孙像三鸟", "孙像船洋", "湖南省宪", "四川军政府", "富字", "鹿头",
               "壹圆", "中圆", "贰角", "壹角", "五角", "半圆", "七钱二分", "三钱六分",
               "一两", "半两", "贰毫", "壹毫",
               "普通", "精发", "粗发", "O版", "三角圆", "甘肃", "海南", "中央", "T点年",
               "湖北省造", "四川省造", "广东省造", "云南省造", "江南省造", "北洋造",
               "东三省", "吉林省造", "奉天", "新疆", "西藏",
               "军政府", "光绪", "富字一两", "富字半两", "鹿头一两"]:
        if kw in name:
            keywords.append(kw)
    return keywords


def match_class(coin_name):
    """用关键词匹配把币名映射到92类"""
    keywords = extract_keywords(coin_name)
    best_score, best_path = 0, None
    clean_name = coin_name.replace(" ", "")
    for c in CLASS_LIST:
        clean_path = c["path"].replace(" ", "")
        score = 0
        for kw in keywords:
            clean_kw = kw.replace(" ", "")
            if clean_kw in clean_path:
                score += len(clean_kw) * 2  # 关键词匹配权重高
        # 再加字符级匹配
        if score == 0:
            score = sum(1 for ch in clean_name if ch in clean_path)
        if score > best_score:
            best_score = score
            best_path = c["path"]
    return best_path, best_score


label_data = []
unmatched_names = Counter()
for pid, name, front, back in matched:
    cls_path, score = match_class(name)
    if cls_path:
        label_data.append((pid, name, cls_path, front, back))
    else:
        unmatched_names[name] += 1

print(f"成功映射到92类: {len(label_data)} 对")
print(f"未匹配: {len(unmatched_names)} 种币名")
if unmatched_names:
    print(f"  样例: {unmatched_names.most_common(5)}")

# ============================================================
# 4. YOLO 检测 + 裁剪
# ============================================================
print("\n加载 YOLO 模型...")
model = YOLO(str(ROOT / "backend" / "best1.pt"))
print(f"开始裁剪 {len(label_data)} 对图片...")

cropped = []
n_skipped = 0
for i, (pid, name, cls_path, front_fn, back_fn) in enumerate(label_data):
    if (i + 1) % 500 == 0:
        print(f"  进度: {i+1}/{len(label_data)}")

    pair_ok = True
    crops = []
    for side, fn in [("front", front_fn), ("back", back_fn)]:
        img_path = IMG_DIR / fn
        img = cv2.imread(str(img_path))
        if img is None:
            pair_ok = False
            break

        results = model(img, verbose=False)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            # YOLO 未检测到，直接 resize 原图兜底
            crop = cv2.resize(img, (224, 224))
        else:
            # 取置信度最高的检测框
            best_idx = boxes.conf.argmax().item()
            xyxy = boxes.xyxy[best_idx].cpu().numpy()
            x1, y1, x2, y2 = map(int, xyxy)
            h, w = img.shape[:2]
            x1 = max(0, x1 - 10)
            y1 = max(0, y1 - 10)
            x2 = min(w, x2 + 10)
            y2 = min(h, y2 + 10)
            crop = img[y1:y2, x1:x2]
        crops.append(crop)

    # 保存裁剪后的正反面
    out_front = CROP_DIR / f"{pid}_front_crop.jpg"
    out_back = CROP_DIR / f"{pid}_back_crop.jpg"
    cv2.imwrite(str(out_front), crops[0])
    cv2.imwrite(str(out_back), crops[1])

    cls_id = CLASS_IDX[cls_path]
    cropped.append((f"{pid}_front_crop.jpg", f"{pid}_back_crop.jpg", cls_id, cls_path, name))

print(f"裁剪完成: {len(cropped)} 对, 跳过 {n_skipped} 对")

# 保存标签映射
label_csv = OUT_DIR / "labels.csv"
with open(label_csv, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["front_img", "back_img", "class_id", "class_path", "coin_name"])
    for row in cropped:
        writer.writerow(row)
print(f"标签文件: {label_csv}")

# ============================================================
# 5. 7:2:1 分层划分
# ============================================================
X = list(range(len(cropped)))
y = [r[2] for r in cropped]  # class_id

# 过滤样本数<3的类
min_samples = 3
y = [r[2] for r in cropped]  # class_id 列表
class_counts = Counter(y)
valid_classes = {c for c, n in class_counts.items() if n >= min_samples}
valid_items = [r for r in cropped if r[2] in valid_classes]
valid_labels = [r[2] for r in valid_items]

# 70% train, 15% val, 15% test
train_local_idx, temp_local_idx = stratified_split(valid_items, valid_labels, test_size=0.3, random_state=42)
temp_labels = [valid_labels[i] for i in temp_local_idx]
temp_items = [valid_items[i] for i in temp_local_idx]
val_local_idx, test_local_idx = stratified_split(temp_items, temp_labels, test_size=0.5, random_state=42)

# 映射回 cropped 的索引
train_idx = [cropped.index(valid_items[i]) for i in train_local_idx]
val_idx = [cropped.index(valid_items[i]) for i in val_local_idx]
test_idx = [cropped.index(valid_items[i]) for i in test_local_idx]

for split_name, indices in [("train", train_idx), ("val", val_idx), ("test", test_idx)]:
    split_csv = SPLIT_DIR / f"{split_name}.csv"
    with open(split_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["front_img", "back_img", "class_id"])
        for idx in indices:
            r = cropped[idx]
            writer.writerow([r[0], r[1], r[2]])
    print(f"{split_name}: {len(indices)} 对 → {split_csv}")

# ============================================================
# 6. 统计报告
# ============================================================
print(f"\n=== 数据集统计 ===")
print(f"总图片对: {len(cropped)}")
print(f"类别数: {len(set(r[2] for r in cropped))}")
print(f"训练/验证/测试: {len(train_idx)}/{len(val_idx)}/{len(test_idx)}")
print(f"输出目录: {OUT_DIR}")
print(f"  crops/  : 裁剪图片")
print(f"  labels.csv : 完整标签")
print(f"  splits/ : train.csv / val.csv / test.csv")
