"""系统评测脚本 — 评估模型推理和 API 性能"""
import time
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

results = {"model": {}, "api": {}}


# ==============================================================================
# 1. 模型加载评测
# ==============================================================================
def benchmark_model_loading():
    print("=" * 60)
    print("1. 模型加载评测")
    print("=" * 60)

    # ONNX
    t0 = time.time()
    from models.model_loader import load_models

    load_models()
    t1 = time.time()
    results["model"]["onnx_load_time"] = round(t1 - t0, 2)
    print(f"  ONNX 模型加载: {results['model']['onnx_load_time']}s")

    from models.model_loader import onnx_session, yolo_model1

    results["model"]["onnx_ready"] = onnx_session is not None
    results["model"]["yolo1_ready"] = yolo_model1 is not None
    print(f"  ONNX 就绪: {results['model']['onnx_ready']}")
    print(f"  YOLO 就绪: {results['model']['yolo1_ready']}")

    # 类别数
    from routes.predict import load_class_names, CLASS_NAMES

    load_class_names()
    results["model"]["num_classes"] = len(CLASS_NAMES)
    print(f"  分类类别数: {len(CLASS_NAMES)}")


# ==============================================================================
# 2. 推理性能评测
# ==============================================================================
def benchmark_inference():
    print("\n" + "=" * 60)
    print("2. 推理性能评测")
    print("=" * 60)

    import cv2
    import numpy as np
    from models.model_loader import onnx_session

    if onnx_session is None:
        print("  ONNX 模型未加载，跳过推理评测")
        return

    # 随机数据测试
    dummy1 = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    dummy2 = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)

    from services.onnx_service import run_onnx_pair_inference

    # 预热
    for _ in range(3):
        run_onnx_pair_inference(dummy1, dummy2)

    # 计时
    latencies = []
    n_runs = 20
    for _ in range(n_runs):
        t0 = time.time()
        run_onnx_pair_inference(dummy1, dummy2)
        latencies.append((time.time() - t0) * 1000)

    latencies.sort()
    results["inference"] = {
        "n_runs": n_runs,
        "p50_ms": round(latencies[n_runs // 2], 1),
        "p95_ms": round(latencies[int(n_runs * 0.95)], 1),
        "min_ms": round(min(latencies), 1),
        "max_ms": round(max(latencies), 1),
    }
    print(f"  推理次数: {n_runs}")
    print(f"  P50 延迟: {results['inference']['p50_ms']}ms")
    print(f"  P95 延迟: {results['inference']['p95_ms']}ms")


# ==============================================================================
# 3. API 响应评测
# ==============================================================================
def benchmark_api():
    print("\n" + "=" * 60)
    print("3. API 响应评测")
    print("=" * 60)

    import urllib.request

    endpoints = ["/api/health", "/api/predict/capabilities", "/api/predict/classes", "/api/artifacts/classification"]

    for ep in endpoints:
        url = f"http://127.0.0.1:5001{ep}"
        try:
            t0 = time.time()
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            elapsed = (time.time() - t0) * 1000
            status = resp.status
        except Exception as e:
            elapsed = -1
            status = str(e)

        results.setdefault("api", {})[ep] = {"status": status, "latency_ms": round(elapsed, 1)}
        print(f"  {ep}: {status} ({results['api'][ep]['latency_ms']}ms)")


# ==============================================================================
# 4. 数据集统计
# ==============================================================================
def benchmark_data():
    print("\n" + "=" * 60)
    print("4. 数据集统计")
    print("=" * 60)

    import sqlite3
    from pathlib import Path

    db_path = Path(__file__).parent / "instance" / "item.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM item").fetchone()[0]
        results["data"] = {"item_db_records": count}
        print(f"  item.db 记录数: {count}")
        conn.close()

    # 图片统计
    img_dir = Path(__file__).parent.parent / "data" / "images"
    if img_dir.exists():
        n_images = len(list(img_dir.glob("*.jpg")))
        results["data"]["images"] = n_images
        print(f"  data/images/ 图片数: {n_images}")

    # 训练数据统计
    training_dir = Path(__file__).parent.parent / "training"
    if training_dir.exists():
        for split_dir in ["kinds", "scores"]:
            for split in ["train", "val", "test"]:
                f = training_dir / split_dir / f"{split}.csv"
                if f.exists():
                    with open(f) as fh:
                        n = sum(1 for _ in fh)
                    results["data"][f"{split_dir}_{split}"] = n


# ==============================================================================
if __name__ == "__main__":
    benchmark_model_loading()
    benchmark_inference()
    benchmark_api()
    benchmark_data()

    print("\n" + "=" * 60)
    print("评测结果汇总")
    print("=" * 60)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    # 保存结果
    out_path = os.path.join(os.path.dirname(__file__), "benchmark_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存到: {out_path}")
