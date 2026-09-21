# ==============================================================================
# YOLO检测服务
# ==============================================================================
import logging
import cv2
import numpy as np
from config import get_yolo

logger = logging.getLogger('services.yolo')

def _run_yolo_model(model, img, confidence_threshold):
    """对单个 YOLO 模型运行推理，返回检测结果列表"""
    results = []
    detections = model(img, conf=confidence_threshold, verbose=False)
    for det in detections:
        boxes = det.boxes
        if boxes is not None:
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                x, y, w, h = xyxy[0], xyxy[1], xyxy[2] - xyxy[0], xyxy[3] - xyxy[1]
                results.append([x, y, w, h, conf])
    return results


def detect_yolo(img, confidence_threshold=0.2):
    """
    使用YOLO模型检测图像中的物体。
    会同时尝试 model1（正面检测）和 model2（反面检测），
    返回置信度最高的检测结果。

    Args:
        img: OpenCV图像 (numpy数组)
        confidence_threshold: 置信度阈值

    Returns:
        results: 检测结果列表，每个元素包含 [x, y, w, h, conf]
    """
    from models import model_loader

    all_results = []
    try:
        YOLO = get_yolo()
        if YOLO is None:
            return None

        # 尝试两个模型，汇总结果
        for model in [model_loader.yolo_model1, model_loader.yolo_model2]:
            if model is not None:
                try:
                    res = _run_yolo_model(model, img, confidence_threshold)
                    all_results.extend(res)
                except Exception as e:
                    logger.warning(f"YOLO 单模型检测失败: {e}")

        if not all_results:
            return None

        # 按置信度排序
        all_results.sort(key=lambda x: x[4], reverse=True)
        return all_results

    except Exception as e:
        logger.error(f"YOLO检测失败: {e}")
        return None

def segment_circle_from_image(image, box):
    """
    从图像中根据边界框提取圆形区域

    Args:
        image: 输入图像 (numpy数组)
        box: 边界框 [x, y, w, h, conf]

    Returns:
        segmented_image: 裁剪后的图像，如果提取失败返回None
    """
    try:
        x, y, w, h, _ = box
        # 将所有坐标转换为 Python float
        x = float(x) if hasattr(x, 'item') else float(x)
        y = float(y) if hasattr(y, 'item') else float(y)
        w = float(w) if hasattr(w, 'item') else float(w)
        h = float(h) if hasattr(h, 'item') else float(h)
        # 使用原始box尺寸计算圆形参数
        radius = int(min(w, h) // 2)

        # 创建圆形遮罩，基于实际图像尺寸
        mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
        cv2.circle(mask, (int(x + w // 2), int(y + h // 2)), radius, 255, -1)

        # 应用遮罩
        masked = cv2.bitwise_and(image, image, mask=mask)

        # 创建白色背景
        white_bg = np.ones_like(image) * 255
        result = np.where(mask[..., np.newaxis] > 0, masked, white_bg)

        return result

    except Exception as e:
        logger.error(f"圆形区域提取失败: {e}")
        return None