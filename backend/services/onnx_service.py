# ==============================================================================
# ONNX推理服务
# ==============================================================================

# 导入必要的库
import logging
import cv2  # OpenCV库，用于图像处理
import numpy as np  # 数值计算库，处理数组数据
from PIL import Image  # Python图像库，用于图像操作
# 从models模块导入ONNX相关的对象
from models import onnx_session, onnx_input_names, onnx_output_names

logger = logging.getLogger('services.onnx')

def preprocess_for_onnx(pil_image):
    """
    为ONNX模型预处理图像
    
    预处理步骤：
    1. 确保图像是RGB格式
    2. 缩放到224x224像素
    3. 转换为numpy数组并归一化到[0,1]
    4. 使用ImageNet的均值和标准差进行标准化
    5. 转换为CHW格式（通道、高度、宽度）
    6. 添加batch维度
    
    Args:
        pil_image: PIL图像对象
        
    Returns:
        numpy: 预处理后的numpy数组 (shape: [1, 3, 224, 224], dtype: float32)
    """
    
    # 转换为RGB（如果需要）
    # 检查图像模式，如果不是RGB模式就转换
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    # 调整大小为模型期望的输入尺寸
    # 目标尺寸为224x224像素（ImageNet标准尺寸）
    target_size = (224, 224)
    # LANCZOS是高质量的重采样算法
    pil_image = pil_image.resize(target_size, Image.LANCZOS)
    
    # 转换为numpy数组并归一化 (确保使用 float32)
    # 将PIL图像转换为numpy数组，数据类型为float32
    img_array = np.array(pil_image, dtype=np.float32)
    
    # 归一化到 [0, 1]
    # 将像素值从[0,255]范围缩放到[0,1]范围
    img_array = img_array / 255.0
    
    # 标准化（使用ImageNet的均值和标准差）- 使用 float32
    # ImageNet数据集的均值
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    # ImageNet数据集的标准差
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    # 标准化公式: (x - mean) / std，使数据符合标准正态分布
    img_array = (img_array - mean) / std
    
    # 转换为CHW格式 (Channels, Height, Width)
    # 原来的格式是HWC（高度、宽度、通道），现在转换为CHW
    # transpose(2,0,1)表示将第2维（通道）移到第0维
    img_array = np.transpose(img_array, (2, 0, 1))
    
    # 添加batch维度
    # expand_dims在第0维（最前面）增加一个维度，表示batch size
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array

def run_onnx_pair_inference(image1_np, image2_np):
    """
    使用ONNX模型对两张图像进行推理
    
    功能：将两张图像输入到ONNX模型，判断它们的相似度或关系
    
    Args:
        image1_np: 第一张图像的numpy数组 (OpenCV格式，BGR)
        image2_np: 第二张图像的numpy数组 (OpenCV格式，BGR)
        
    Returns:
        probs: 预测概率数组，表示两张图像的匹配程度
    """
    try:
        # 检查ONNX模型是否已加载
        if onnx_session is None:
            raise ValueError("ONNX模型未加载")
        
        # 检查输入输出名称是否已初始化
        if not onnx_input_names or not onnx_output_names:
            raise ValueError(f"ONNX模型输入输出名称未初始化: inputs={onnx_input_names}, outputs={onnx_output_names}")
        
        # 打印调试信息：显示模型的输入输出结构
        logger.info(f"ONNX输入名称: {onnx_input_names}")
        logger.info(f"ONNX输出名称: {onnx_output_names}")
        logger.info(f"输入名称数量: {len(onnx_input_names)}")
        
        # 检查输入数量是否足够（至少需要2个输入：两张图像）
        if len(onnx_input_names) < 2:
            raise ValueError(f"ONNX模型期望至少2个输入，但只找到 {len(onnx_input_names)} 个")
        
        # 将OpenCV BGR图像转换为PIL RGB图像
        # OpenCV默认使用BGR格式，但模型期望RGB格式
        img1_rgb = cv2.cvtColor(image1_np, cv2.COLOR_BGR2RGB)
        img2_rgb = cv2.cvtColor(image2_np, cv2.COLOR_BGR2RGB)
        
        # 转换为PIL图像
        # PIL是Python Imaging Library，提供更丰富的图像处理功能
        pil_img1 = Image.fromarray(img1_rgb)
        pil_img2 = Image.fromarray(img2_rgb)
        
        # 预处理：将两张图像都转换为模型可接受的格式
        processed1 = preprocess_for_onnx(pil_img1)
        processed2 = preprocess_for_onnx(pil_img2)
        
        # 打印调试信息：显示预处理后的数据形状
        logger.info(f"图像1处理后形状: {processed1.shape}")
        logger.info(f"图像2处理后形状: {processed2.shape}")
        
        # 准备输入数据：创建一个字典，键是输入名称，值是处理后的图像数据
        # onnx_input_names[0]通常是第一个输入（如"input1"或"image1"）
        # onnx_input_names[1]通常是第二个输入（如"input2"或"image2"）
        inputs = {
            onnx_input_names[0]: processed1,
            onnx_input_names[1]: processed2
        }
        
        # 运行推理：将输入数据传入模型，得到输出结果
        # run方法：第一个参数指定要获取的输出名称，第二个参数是输入数据
        outputs = onnx_session.run(onnx_output_names, inputs)
        
        # 打印调试信息：显示输出信息
        logger.info(f"推理输出数量: {len(outputs)}")
        logger.info(f"第一个输出形状: {outputs[0].shape}")
        
        # 获取预测结果（raw logits）
        logits = outputs[0]

        # 应用softmax将logits转换为概率分布
        # softmax(x_i) = exp(x_i) / sum(exp(x_j))
        logits_flat = logits.flatten()
        # 减去最大值防止数值溢出
        logits_shifted = logits_flat - np.max(logits_flat)
        exp_values = np.exp(logits_shifted)
        probs = exp_values / np.sum(exp_values)

        return probs
        
    except Exception as e:
        # 如果推理过程中出现任何异常，打印错误信息
        logger.error(f"ONNX推理失败: {e}", exc_info=True)
        return None  # 返回None表示推理失败