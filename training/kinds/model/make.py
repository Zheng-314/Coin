# ### 正样本对：水平翻转，随机旋转、随机扰动

import cv2
import numpy as np
import random
import pandas as pd

def create_circular_mask(h, w):
    """创建圆形掩码，仅在圆内为True"""
    center = (h // 2, w // 2)
    radius = min(center[0], center[1])
    y, x = np.ogrid[:h, :w]
    mask = (x - center[1])**2 + (y - center[0])**2 <= radius**2
    return mask

def _circular_mask(h, w):
    """创建圆形掩码（uint8类型）"""
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, (w//2, h//2), h//2, 255, -1)
    return mask

# 高斯噪声
def add_gaussian_noise(image, mean=0, sigma=25, prob=0.05):
    """在圆形区域内添加高斯噪声（与椒盐噪声逻辑一致）"""
    h, w = image.shape[:2]
    mask = create_circular_mask(h, w)
    
    output = image.copy()
    # 生成高斯噪声（仅在圆内生成）
    noise = np.random.normal(mean, sigma, (h, w, 3)).astype(np.float32)
    # 创建噪声掩码（按概率决定每个像素是否添加噪声）
    noise_mask = (np.random.rand(h, w) < prob) & mask
    # 应用噪声掩码
    output[noise_mask] = np.clip(
        output[noise_mask].astype(np.float32) + noise[noise_mask],
        0, 255
    ).astype(np.uint8)
    return output

# 随机坑洞
def generate_irregular_holes(img, max_holes=3, vertex_range=(3, 4), max_size=14, min_size=6):
    h, w = img.shape[:2]
    assert h == w, "Input image must be square"
    result = img.copy()
    circular_mask = _circular_mask(h, w)  # uint8掩码

    num_holes = random.randint(1, max_holes)
    for _ in range(num_holes):
        # 生成基准点（极坐标）
        radius = h // 2
        theta = np.random.uniform(0, 2*np.pi)
        r = np.random.uniform(0, radius*0.8)
        center_x = int(w//2 + r * np.cos(theta))
        center_y = int(h//2 + r * np.sin(theta))

        # 生成多边形顶点
        num_vertices = random.randint(*vertex_range)
        points = []
        for _ in range(num_vertices):
            while True:
                dx = random.randint(-max_size//2, max_size//2)
                dy = random.randint(-max_size//2, max_size//2)
                px, py = center_x + dx, center_y + dy
                if (px - w//2)**2 + (py - h//2)**2 <= radius**2:
                    points.append([px, py])
                    break

        # 创建多边形掩码
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [np.array(points)], 255)
        mask = cv2.bitwise_and(mask, circular_mask)  # 应用圆形约束

        # 形态学操作
        kernel_size = random.choice([3, 5])
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # 获取掩码区域内所有像素
        masked_pixels = result[mask == 255]
        
        # 计算每个通道的最大值
        if len(masked_pixels) > 0:
            max_color = np.max(masked_pixels, axis=0)
            result[mask == 255] = max_color

    result[circular_mask == 0] = 0  # 圆外设为黑色
    return result

# 椒盐噪声
def add_salt_pepper(image, prob=0.05):
    """在圆形区域内添加椒盐噪声"""
    h, w = image.shape[:2]
    mask = create_circular_mask(h, w)
    
    output = image.copy()
    # 椒噪声（仅在圆内生成）
    pepper = (np.random.rand(h, w) < prob/2) & mask
    output[pepper] = 0
    # 盐噪声（仅在圆内生成）
    salt = (np.random.rand(h, w) < prob/2) & mask
    output[salt] = 255
    return output

# 随机旋转
def random_rotation(image, max_angle=30):
    angle = np.random.uniform(-max_angle, max_angle)
    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1)
    rotated = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    return rotated

# 亮度变化
def adjust_brightness(image, brightness_factor):
    """
    调整图像亮度
    :param image: 输入图像（BGR格式）
    :param brightness_factor: 亮度调节因子 
              1.0-原始亮度
              >1.0-增加亮度
              <1.0-降低亮度
    :return: 调整后的图像
    """
    # 转换到HSV颜色空间
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 调整亮度通道（V通道）
    hsv = hsv.astype(np.float32)
    hsv[..., 2] = hsv[..., 2] * brightness_factor
    hsv = np.clip(hsv, 0, 255)  # 确保值在0-255之间
    
    # 转换回BGR格式
    hsv = hsv.astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

dic = {'XF': 0, 'VF': 1, 'AU': 2, 'MS': 3}

def data_enhance(frow):
    save_file = "/workspace/vggse/now/"
    path1, path2, class1 = frow.iloc[2], frow.iloc[3], frow.iloc[4]
    if class1 not in dic:
        return 
        
    label1 = dic[class1]

    img1 = cv2.imread(save_file + path1)

    # 正面数据集
    gs1 = add_gaussian_noise(img1, sigma=50, prob = 0.030)
    sp1 = add_salt_pepper(img1, prob=0.015)
    
    f1 = path1.split('.')
    cv2.imwrite(save_file + f1[0] + "gs." + f1[1], gs1)
    cv2.imwrite(save_file + f1[0] + "jy." + f1[1], sp1)
    
    # 反面数据集
    img2 = cv2.imread(save_file + path2)
    gs2 = add_gaussian_noise(img2, sigma=50, prob = 0.030)
    sp2 = add_salt_pepper(img2, prob=0.015)
    f2 = path2.split('.')
    cv2.imwrite(save_file + f2[0] + "gs." + f2[1], gs2)
    cv2.imwrite(save_file + f2[0] + "jy." + f2[1], sp2)

    
    with open("ndata.csv", "at") as fs:
        # 格式为 图片1、图片2、评级类别、类别标签
        fs.write(f"{path1},{path2},{class1},{label1}\n")
        fs.write(f"{f1[0] + 'gs.' + f1[1]},{f2[0] + 'gs.' + f2[1]},{class1},{label1}\n")
        fs.write(f"{f1[0] + 'jy.' + f1[1]},{f2[0] + 'jy.' + f2[1]},{class1},{label1}\n")
        fs.write(f"{f1[0] + 'gs.' + f1[1]},{f2[0] + 'jy.' + f2[1]},{class1},{label1}\n")
        fs.write(f"{f1[0] + 'gs.' + f1[1]},{f2[0] + 'jy.' + f2[1]},{class1},{label1}\n")
    
    if class1 == 'VF':
        print(f"class: {class1}")
        rd = np.random.uniform(0.7, 1.3)
        rimg1 = adjust_brightness(img1, rd)
        rimg1 = random_rotation(rimg1)
        rd = np.random.uniform(0.7, 1.3)
        rimg2 = adjust_brightness(img2, rd)
        rimg2 = random_rotation(rimg2)

        cv2.imwrite(save_file + f1[0] + "rd." + f1[1], rimg1)
        cv2.imwrite(save_file + f2[0] + "rd." + f2[1], rimg2)
        with open("ndata.csv", "at") as fs:
            # 格式为 图片1、图片2、评级类别、类别标签
            fs.write(f"{f1[0] + 'gs.' + f1[1]},{f2[0] + 'rd.' + f2[1]},{class1},{label1}\n")
            fs.write(f"{f1[0] + 'rd.' + f1[1]},{f2[0] + 'jy.' + f2[1]},{class1},{label1}\n")
            fs.write(f"{f1[0] + 'rd.' + f1[1]},{f2[0] + 'gs.' + f2[1]},{class1},{label1}\n")
            fs.write(f"{f1[0] + 'jy.' + f1[1]},{f2[0] + 'rd.' + f2[1]},{class1},{label1}\n")

  
        

# ------------------------- 验证示例 -------------------------
if __name__ == "__main__":
    # data_enhance("1.jpg")
    df = pd.read_csv("filtered_coins.csv")    
    print(df.head())
    # print(df.iloc[:, 0])
    # print(df.iloc[:, 1])
    # print(df.iloc[:, 3])
    c =  df.iloc[0]
    # c1 = list(df.iloc[:, 2])f
    # c2 = list(df.iloc[:, 3])
    for index, frow in df.iterrows():
        # path = os.path.join("/media/data/workplace_wph/new", path1)
        data_enhance(frow)

    # for path1 in c1:
    #     # path = os.path.join("/media/data/workplace_wph/new", path1)
    #     data_enhance(path1)
    # for path2 in c2:
    #     # path = os.path.join("/media/data/workplace_wph/new", path1)
    #     data_enhance(path2)
        
        
    
    
    
    