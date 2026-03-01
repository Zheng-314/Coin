# ==============================================================================
# ONNX推理服务
# ==============================================================================
import cv2
import numpy as np
from PIL import Image
from models import onnx_session, onnx_input_names, onnx_output_names

def preprocess_for_onnx(pil_image):
    """
    为ONNX模型预处理图像

    Args:
        pil_image: PIL图像对象

    Returns:
        numpy: 预处理后的numpy数组 (shape: [1, 3, 224, 224], dtype: float32)
    """
    # 转换为RGB（如果需要）
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')

    # 调整大小为模型期望的输入尺寸
    target_size = (224, 224)
    pil_image = pil_image.resize(target_size, Image.LANCZOS)

    # 转换为numpy数组并归一化 (确保使用 float32)
    img_array = np.array(pil_image, dtype=np.float32)

    # 归一化到 [0, 1]
    img_array = img_array / 255.0

    # 标准化（使用ImageNet的均值和标准差）- 使用 float32
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_array = (img_array - mean) / std

    # 转换为CHW格式 (Channels, Height, Width)
    img_array = np.transpose(img_array, (2, 0, 1))

    # 添加batch维度
    img_array = np.expand_dims(img_array, axis=0)

    return img_array

def run_onnx_pair_inference(image1_np, image2_np):
    """
    使用ONNX模型对两张图像进行推理

    Args:
        image1_np: 第一张图像的numpy数组 (OpenCV格式，BGR)
        image2_np: 第二张图像的numpy数组 (OpenCV格式，BGR)

    Returns:
        probs: 预测概率数组
    """
    try:
        if onnx_session is None:
            raise ValueError("ONNX模型未加载")

        if not onnx_input_names or not onnx_output_names:
            raise ValueError(f"ONNX模型输入输出名称未初始化: inputs={onnx_input_names}, outputs={onnx_output_names}")

        print(f"ONNX输入名称: {onnx_input_names}")
        print(f"ONNX输出名称: {onnx_output_names}")
        print(f"输入名称数量: {len(onnx_input_names)}")

        # 检查输入数量
        if len(onnx_input_names) < 2:
            raise ValueError(f"ONNX模型期望至少2个输入，但只找到 {len(onnx_input_names)} 个")

        # 将OpenCV BGR图像转换为PIL RGB图像
        img1_rgb = cv2.cvtColor(image1_np, cv2.COLOR_BGR2RGB)
        img2_rgb = cv2.cvtColor(image2_np, cv2.COLOR_BGR2RGB)

        # 转换为PIL图像
        pil_img1 = Image.fromarray(img1_rgb)
        pil_img2 = Image.fromarray(img2_rgb)

        # 预处理
        processed1 = preprocess_for_onnx(pil_img1)
        processed2 = preprocess_for_onnx(pil_img2)

        print(f"图像1处理后形状: {processed1.shape}")
        print(f"图像2处理后形状: {processed2.shape}")

        # 准备输入，分别输入两个图像
        inputs = {
            onnx_input_names[0]: processed1,
            onnx_input_names[1]: processed2
        }

        # 运行推理
        outputs = onnx_session.run(onnx_output_names, inputs)

        print(f"推理输出数量: {len(outputs)}")
        print(f"第一个输出形状: {outputs[0].shape}")

        # 获取预测结果
        probs = outputs[0]  # 假设输出是概率分布

        return probs

    except Exception as e:
        print(f"ONNX推理失败: {e}")
        import traceback
        traceback.print_exc()
        return None