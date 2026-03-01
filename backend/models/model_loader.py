# ==============================================================================
# 模型加载和管理
# ==============================================================================
import os
from config import get_yolo, YOLO_MODEL_PATH_1, YOLO_MODEL_PATH_2, ONNX_MODEL_PATH

# 全局模型实例
yolo_model1 = None
yolo_model2 = None
onnx_session = None
onnx_input_names = []
onnx_output_names = []
predict_model_errors = []
onnxruntime = None
_models_loaded = False  # 标记模型是否已加载

def load_models():
    """加载所有模型"""
    global yolo_model1, yolo_model2, onnx_session, onnx_input_names, onnx_output_names, predict_model_errors, onnxruntime, _models_loaded

    # 避免重复加载
    if _models_loaded:
        return

    predict_model_errors = []

    # 检查ONNX运行时
    try:
        import onnxruntime as _onnxruntime
        onnxruntime = _onnxruntime
        print("onnxruntime 导入成功")
    except Exception as e:
        onnxruntime = None
        predict_model_errors.append(f"onnxruntime 导入失败: {e}")
        print(f"onnxruntime 导入失败: {e}")

    # 检查YOLO
    YOLO = get_yolo()
    if YOLO is None:
        predict_model_errors.append("ultralytics 导入失败，将跳过 YOLO 预处理")
        print("YOLO 不可用，将跳过 YOLO 预处理")

    # 加载YOLO模型1
    try:
        if YOLO is None:
            raise RuntimeError("YOLO 不可用")
        if os.path.exists(YOLO_MODEL_PATH_1):
            yolo_model1 = YOLO(YOLO_MODEL_PATH_1)
            print(f"YOLO 模型1 加载成功: {YOLO_MODEL_PATH_1}")
        else:
            print(f"YOLO 模型1 文件不存在: {YOLO_MODEL_PATH_1}")
            predict_model_errors.append(f"缺少 YOLO 模型文件: {YOLO_MODEL_PATH_1}")
    except Exception as e:
        print(f"加载 YOLO1 失败: {e}")
        predict_model_errors.append(f"加载 YOLO1 失败: {e}")

    # 加载YOLO模型2
    try:
        if YOLO is None:
            raise RuntimeError("YOLO 不可用")
        if os.path.exists(YOLO_MODEL_PATH_2):
            yolo_model2 = YOLO(YOLO_MODEL_PATH_2)
            print(f"YOLO 模型2 加载成功: {YOLO_MODEL_PATH_2}")
        else:
            print(f"YOLO 模型2 文件不存在: {YOLO_MODEL_PATH_2}")
            predict_model_errors.append(f"缺少 YOLO 模型文件: {YOLO_MODEL_PATH_2}")
    except Exception as e:
        print(f"加载 YOLO2 失败: {e}")
        predict_model_errors.append(f"加载 YOLO2 失败: {e}")

    # 加载ONNX模型
    try:
        if onnxruntime is None:
            raise RuntimeError("onnxruntime 不可用")
        print(f"尝试加载 ONNX 模型: {ONNX_MODEL_PATH}")
        if not os.path.exists(ONNX_MODEL_PATH):
            raise FileNotFoundError(f"缺少 ONNX 模型文件: {ONNX_MODEL_PATH}")
        print(f"ONNX 模型文件存在: {ONNX_MODEL_PATH}")

        # 设置日志级别为 ERROR,减少噪音
        os.environ['ORT_LOGGING_LEVEL'] = 'ERROR'

        onnx_session = onnxruntime.InferenceSession(ONNX_MODEL_PATH)
        print(f"ONNX 会话创建成功")
        onnx_input_names = [x.name for x in onnx_session.get_inputs()]
        onnx_output_names = [x.name for x in onnx_session.get_outputs()]
        print(f"ONNX 输入名称: {onnx_input_names}")
        print(f"ONNX 输出名称: {onnx_output_names}")
    except Exception as e:
        print(f"加载 ONNX 失败: {e}")
        import traceback
        traceback.print_exc()
        predict_model_errors.append(f"加载 ONNX 失败: {e}")

    # 输出加载状态
    if onnx_session is not None:
        print("推理核心模型 ONNX 加载成功")
    else:
        print("推理核心模型 ONNX 未就绪，将返回可诊断错误")

    if predict_model_errors:
        print("模型加载告警:")
        for err in predict_model_errors:
            print(f" - {err}")

    _models_loaded = True

def ensure_onnx_session_ready():
    """确保ONNX会话已准备好"""
    global onnx_session
    print(f"调用 ensure_onnx_session_ready，当前 onnx_session: {onnx_session}")
    if onnx_session is None:
        print("onnx_session 为 None，调用 load_models")
        load_models()
    print(f"ensure_onnx_session_ready 返回: {onnx_session is not None}, {predict_model_errors}")
    return onnx_session is not None, predict_model_errors

# 立即初始化模型
# 这样当模块被导入时，模型就会被加载
load_models()