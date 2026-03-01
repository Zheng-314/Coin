# ==============================================================================
# YOLO检测服务
# ==============================================================================
import cv2
import numpy as np
from config import get_yolo

def detect_yolo(img, confidence_threshold=0.2):
    """
    使用YOLO模型检测图像中的物体

    Args:
        img: OpenCV图像 (numpy数组)
        confidence_threshold: 置信度阈值

    Returns:
        results: 检测结果列表，每个元素包含 [x, y, w, h, conf]
    """
    from models import yolo_model1, yolo_model2

    results = []
    try:
        # 获取YOLO类
        YOLO = get_yolo()
        # 如果YOLO不可用，返回None
        if YOLO is None:
            return None

        # 优先使用模型1
        model = yolo_model1 if yolo_model1 is not None else yolo_model2
        if model is None:
            return None

        # 运行推理
        detections = model(img, conf=confidence_threshold, verbose=False)

        # 提取结果
        for det in detections:
            boxes = det.boxes
            if boxes is not None:
                for box in boxes:
                    # 获取边界框坐标和置信度
                    xyxy = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())

                    x, y, w, h = xyxy[0], xyxy[1], xyxy[2] - xyxy[0], xyxy[3] - xyxy[1]
                    results.append([x, y, w, h, conf])

        # 按置信度排序
        results.sort(key=lambda x: x[4], reverse=True)

        return results if results else None

    except Exception as e:
        print(f"YOLO检测失败: {e}")
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
        print(f"圆形区域提取失败: {e}")
        return None