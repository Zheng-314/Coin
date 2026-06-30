"""共享推理服务 — 多候选 ONNX 推理和 Top-K 结果提取"""
import logging
import numpy as np

logger = logging.getLogger("services.inference")


def run_multi_candidate_inference(images_a, images_b, onnx_infer_fn):
    """对 4 组候选（processed/raw × normal/swapped）运行 ONNX 推理，返回最优结果。

    Args:
        images_a: 正面候选列表 [processed_img, raw_img]
        images_b: 反面候选列表 [processed_img, raw_img]
        onnx_infer_fn: ONNX 推理函数，签名为 (img_a, img_b) -> Optional[np.ndarray]

    Returns:
        (best_probs, best_confidence) 或 (None, 0.0)
    """
    candidate_pairs = [
        ("processed", "normal", images_a[0], images_b[0]),
        ("processed", "swapped", images_b[0], images_a[0]),
        ("raw", "normal", images_a[1], images_b[1]),
        ("raw", "swapped", images_b[1], images_a[1]),
    ]

    best_probs = None
    best_conf = 0.0
    best_meta = {}

    for i, (pipeline_name, order_name, img_a, img_b) in enumerate(candidate_pairs):
        probs = onnx_infer_fn(img_a, img_b)
        if probs is None:
            logger.debug(f"候选 {i+1}/4 ({pipeline_name}/{order_name}) 推理失败")
            continue

        if len(probs.shape) == 2:
            probs = probs[0]

        top1_idx = int(np.argmax(probs))
        top1_conf = float(probs[top1_idx])

        logger.debug(f"候选 {i+1}/4 ({pipeline_name}/{order_name}) top1={top1_idx} conf={top1_conf:.4f}")

        if top1_conf > best_conf:
            best_probs = probs
            best_conf = top1_conf
            best_meta = {"pipeline": pipeline_name, "order": order_name}

    return best_probs, best_conf, best_meta


def extract_top_k(probs, class_names, k=3):
    """从概率向量提取 Top-K 预测结果。

    Args:
        probs: 1-D numpy 概率数组
        class_names: 类别名称列表
        k: 返回数量

    Returns:
        [{"name": str, "confidence": float}, ...]
    """
    if probs is None:
        return []

    probs = np.asarray(probs).flatten()
    sorted_indices = np.argsort(probs)[::-1][:k]

    results = []
    for idx in sorted_indices:
        idx_int = int(idx)
        conf = float(probs[idx_int]) * 100
        name = class_names[idx_int] if idx_int < len(class_names) else f"类别#{idx_int}"
        results.append({"name": name, "confidence": round(conf, 1)})

    return results
