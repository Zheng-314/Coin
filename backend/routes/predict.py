# ==============================================================================
# AI预测鉴定路由
# ==============================================================================
import sys
import importlib.util
import cv2
import numpy as np
import traceback
import json
import os
import logging
from flask import Blueprint, request, jsonify, make_response
from app_new import limiter

logger = logging.getLogger('routes.predict')
from models.model_loader import (
    yolo_model1, yolo_model2, onnx_session, onnx_input_names, onnx_output_names,
    predict_model_errors, ensure_onnx_session_ready
)
from services.yolo_service import detect_yolo, segment_circle_from_image
from services.onnx_service import run_onnx_pair_inference
from utils.helpers import encode_image_to_base64

# 加载分类数据
CLASSIFICATION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'classification.json')
CLASS_NAMES = []

def load_class_names():
    """加载类别名称列表"""
    global CLASS_NAMES
    try:
        with open(CLASSIFICATION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 提取所有叶子节点的类别名称(作为扁平列表)
        def extract_leaf_names(data, path=""):
            names = []

            for key, value in data.items():
                # 每个键的值应该包含 unicode 和 childs
                if isinstance(value, dict):
                    if 'unicode' in value:
                        current_name = value['unicode']
                        current_path = f"{path} > {current_name}" if path else current_name

                        if 'childs' in value and value['childs']:
                            # 递归处理子节点
                            names.extend(extract_leaf_names(value['childs'], current_path))
                        else:
                            # 叶子节点
                            names.append(current_path)

            return names

        CLASS_NAMES = extract_leaf_names(data)
        logger.info(f"已加载 {len(CLASS_NAMES)} 个类别名称")
        if CLASS_NAMES:
            logger.info(f"前3个类别: {CLASS_NAMES[:3]}")
    except Exception as e:
        logger.error(f"加载分类数据失败: {e}")
        import traceback
        logger.error("加载分类数据异常", exc_info=True)
        # 如果加载失败,使用默认的占位符
        CLASS_NAMES = [f"类别 #{i}" for i in range(26)]

# 模块加载时初始化类别名称
load_class_names()

predict_bp = Blueprint('predict', __name__)

def run_optional_yolo_pipeline(image_data):
    """
    使用 YOLO + 圆形分割预处理图像。
    若 YOLO 不可用或失败，回退到原图。
    """
    final_image = image_data

    if image_data is None:
        return None

    if yolo_model1 is None or yolo_model2 is None:
        return final_image

    try:
        results = detect_yolo(image_data)
        if results and len(results) > 0:
            # results 格式: [[x, y, w, h, conf], ...]
            box = results[0]  # 取置信度最高的检测框
            x, y, w, h, _ = box
            # 扩展边界框并裁剪
            padding = int(min(w, h) * 0.1)
            x_start = max(0, int(x - padding))
            y_start = max(0, int(y - padding))
            x_end = min(image_data.shape[1], int(x + w + padding))
            y_end = min(image_data.shape[0], int(y + h + padding))
            cropped = image_data[y_start:y_end, x_start:x_end]
            if cropped is not None and cropped.size > 0:
                final_image = cropped
                segmented = segment_circle_from_image(cropped, box)
                if segmented is not None:
                    final_image = segmented
    except Exception as e:
        logger.error(f"YOLO 预处理失败，回退原图: {e}")

    return final_image

@predict_bp.route('/api/predict/capabilities', methods=['GET'])
def predict_capabilities():
    """获取预测模型能力信息"""
    logger.info("调用 predict_capabilities 函数")
    late_ok, late_err = ensure_onnx_session_ready()
    # 重新导入模型变量，确保获取最新值
    from models import onnx_session, yolo_model1, yolo_model2, onnx_input_names, onnx_output_names, predict_model_errors
    logger.debug(f"predict_capabilities: onnx_session={onnx_session}, late_ok={late_ok}, late_err={late_err}")
    onnx_spec = importlib.util.find_spec("onnxruntime")
    yolo_spec = importlib.util.find_spec("ultralytics")

    return jsonify({
        "onnx_ready": onnx_session is not None and late_ok,
        "yolo1_ready": yolo_model1 is not None,
        "yolo2_ready": yolo_model2 is not None,
        "onnx_inputs": onnx_input_names,
        "onnx_outputs": onnx_output_names,
        "errors": predict_model_errors,
        "late_init_error": late_err,
        "ready": onnx_session is not None and late_ok,
        "runtime": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "onnxruntime_found": onnx_spec is not None,
            "ultralytics_found": yolo_spec is not None
        }
    })

@predict_bp.route('/api/predict/classes', methods=['GET'])
def get_classes():
    """获取所有类别名称"""
    return jsonify({
        "classes": CLASS_NAMES,
        "count": len(CLASS_NAMES)
    })

@predict_bp.route('/api/predict/test', methods=['POST'])
def test_inference():
    """测试推理接口,使用随机数据"""
    try:
        import numpy as np
        # 创建测试图像
        test_img1 = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        test_img2 = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)

        # 运行推理
        probs = run_onnx_pair_inference(test_img1, test_img2)

        if probs is None:
            return jsonify({'error': '推理失败'}), 500

        # 获取 Top3 预测
        top_k = np.argsort(probs)[::-1][:3]
        result_predictions = [
            {
                'class': int(i.item()) if hasattr(i, 'item') else int(i),
                'confidence': float(probs[i].item()) if hasattr(probs[i], 'item') else float(probs[i]),
                'name': CLASS_NAMES[int(i.item()) if hasattr(i, 'item') else int(i)] if (int(i.item()) if hasattr(i, 'item') else int(i)) < len(CLASS_NAMES) else f'类别 #{int(i.item()) if hasattr(i, "item") else int(i)}'
            }
            for i in top_k
        ]

        return jsonify({
            'success': True,
            'predictions': result_predictions,
            'output_shape': list(probs.shape),
            'message': '测试推理成功'
        })
    except Exception as e:
        logger.error(f"测试推理失败: {e}")
        import traceback
        logger.error("测试推理异常", exc_info=True)
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@predict_bp.route('/predict', methods=['POST'])
@limiter.limit("20 per minute")  # AI推理是计算密集型，限制调用频率
def predict():
    """执行钱币预测鉴定"""
    logger.info("=== 收到 /predict 请求 ===")
    late_ok, late_err = ensure_onnx_session_ready()
    # 重新导入onnx_session和predict_model_errors，确保获取最新值
    from models import onnx_session, predict_model_errors
    if onnx_session is None or not late_ok:
        return jsonify({
            'error': '推理模型未就绪，请检查 backend/best_model.onnx 与 onnxruntime 环境。',
            'details': predict_model_errors,
            'late_init_error': late_err
        }), 503

    if 'image1' not in request.files or 'image2' not in request.files:
        return jsonify({'error': '缺少图像文件 (image1 或 image2)'}), 400

    file1, file2 = request.files['image1'], request.files['image2']
    if file1.filename == '' or file2.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    # 验证文件类型
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    def validate_file(file):
        ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return False
        # 验证文件内容类型
        if file.content_type not in ['image/jpeg', 'image/png', 'image/webp', 'image/bmp']:
            return False
        return True

    if not validate_file(file1) or not validate_file(file2):
        return jsonify({'error': '不支持的文件格式,请上传 JPG、PNG、WebP 或 BMP 图片'}), 400

    # 验证文件大小 (限制为 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    file1.seek(0, 2)  # SEEK_END = 2
    file1_size = file1.tell()
    file1.seek(0)
    file2.seek(0, 2)  # SEEK_END = 2
    file2_size = file2.tell()
    file2.seek(0)

    if file1_size > MAX_FILE_SIZE or file2_size > MAX_FILE_SIZE:
        return jsonify({'error': '图片文件过大,请上传 10MB 以内的图片'}), 400

    try:
        # 解码图片
        logger.info("开始解码图片...")
        image1_data = cv2.imdecode(np.frombuffer(file1.read(), np.uint8), cv2.IMREAD_COLOR)
        image2_data = cv2.imdecode(np.frombuffer(file2.read(), np.uint8), cv2.IMREAD_COLOR)

        logger.debug(f"图片1解码结果: {image1_data.shape if image1_data is not None else 'None'}")
        logger.debug(f"图片2解码结果: {image2_data.shape if image2_data is not None else 'None'}")

        if image1_data is None or image2_data is None:
            return jsonify({'error': '上传的图片无法解析，请更换清晰图片后重试。'}), 400

        # ========== YOLO 检测阶段：判断是否为钱币 ==========
        logger.info("开始YOLO检测...")
        det1 = detect_yolo(image1_data)
        det2 = detect_yolo(image2_data)

        # 两张图都检测不到硬币 → 拒识
        yolo_detected_1 = det1 is not None and len(det1) > 0
        yolo_detected_2 = det2 is not None and len(det2) > 0

        if not yolo_detected_1 and not yolo_detected_2:
            logger.warning("两张图片均未检测到钱币")
            return jsonify({
                'error': '无法识别为钱币',
                'message': '上传的图片中未检测到钱币，请上传清晰的钱币正反面照片'
            }), 422

        # 只有一张检测到 → 提示用户
        if not yolo_detected_1 or not yolo_detected_2:
            missing = "第一张（正面）" if not yolo_detected_1 else "第二张（反面）"
            logger.warning(f"仅一张图片检测到钱币: {missing}未检测到")
            return jsonify({
                'error': '图片不完整',
                'message': f'{missing}图片中未检测到钱币，请确保上传的是钱币正反面照片'
            }), 422

        # ========== 预处理：YOLO裁剪 + 圆形分割 ==========
        logger.info("开始预处理...")
        processed1 = run_optional_yolo_pipeline(image1_data)
        processed2 = run_optional_yolo_pipeline(image2_data)
        logger.info("预处理完成")

        from services.inference_service import run_multi_candidate_inference, extract_top_k

        # 多候选推理：处理后图像和原图，正常和交换顺序
        best_probs, best_conf, best_meta = run_multi_candidate_inference(
            images_a=[processed1, image1_data],
            images_b=[processed2, image2_data],
            onnx_infer_fn=run_onnx_pair_inference,
        )

        if best_probs is None:
            return jsonify({'error': '推理失败，请检查模型配置'}), 500

        logger.info(f"最优候选: pipeline={best_meta['pipeline']}, order={best_meta['order']}, conf={best_conf:.4f}")

        # Top-3 预测
        result_predictions = extract_top_k(best_probs, CLASS_NAMES, k=3)

        # 展示图与最终入模策略一致
        if best_meta.get('pipeline') == 'processed':
            display1, display2 = processed1, processed2
        else:
            display1, display2 = image1_data, image2_data

        if best_meta.get('order') == 'swapped':
            display1, display2 = display2, display1

        base64_image1 = encode_image_to_base64(display1)
        base64_image2 = encode_image_to_base64(display2)

        response = make_response(jsonify({
            'predictions': result_predictions,
            'processedImage1': f"data:image/jpeg;base64,{base64_image1}",
            'processedImage2': f"data:image/jpeg;base64,{base64_image2}",
            'selectedPipeline': best['pipeline'],
            'selectedOrder': best['order']
        }))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    except Exception as e:
        logger.error("预测处理异常", exc_info=True)
        # 记录详细错误到日志,但只返回通用错误信息给用户
        logger.error(f"预测处理错误: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        # 在开发模式下返回详细错误,方便调试
        import os
        if os.getenv('FLASK_DEBUG'):
            return jsonify({
                'error': f'服务器处理图像时发生错误: {str(e)}',
                'error_type': type(e).__name__,
                'details': traceback.format_exc()
            }), 500
        return jsonify({'error': '服务器处理图像时发生错误,请稍后重试'}), 500