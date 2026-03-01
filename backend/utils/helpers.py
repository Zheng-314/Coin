# ==============================================================================
# 辅助函数
# ==============================================================================
import json
import base64
import cv2
import re

def json_response(data, status_code=200):
    """返回一个正确编码的 JSON 响应"""
    from flask import jsonify
    response = jsonify(data)
    response.status_code = status_code
    return response

def encode_image_to_base64(image_np):
    """将OpenCV图像(numpy array)编码为Base64字符串"""
    _, buffer = cv2.imencode('.jpg', image_np)
    return base64.b64encode(buffer).decode('utf-8')

def cn_num_to_arabic(cn):
    """中文数字转阿拉伯数字"""
    mapping = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,
        '陆': 6, '柒': 7, '捌': 8, '玖': 9
    }
    return mapping.get(cn, 0)

def parse_cn_republic_year(cn):
    """解析中华民国年份（如：民国三年）"""
    if not cn:
        return None
    # 匹配 "民国XX年" 格式
    match = re.search(r'民国(\s*([一二三四五六七八九十壹贰叁肆伍陆柒捌玖零]+)\s*)年', cn)
    if match:
        year_text = match.group(2)
        # 将中文数字转换为阿拉伯数字
        # 简单处理两位数
        if len(year_text) == 1:
            year = cn_num_to_arabic(year_text)
        else:
            # 处理如"二十三"的情况
            year = 0
            i = 0
            while i < len(year_text):
                char = year_text[i]
                if char in '二':
                    if i + 1 < len(year_text) and year_text[i + 1] in '一二三四五六七八九十':
                        year += 20
                        i += 1
                    else:
                        year += 2
                elif char in '三':
                    if i + 1 < len(year_text) and year_text[i + 1] in '一二三四五六七八九十':
                        year += 30
                        i += 1
                    else:
                        year += 3
                elif char in '四':
                    if i + 1 < len(year_text) and year_text[i + 1] in '一二三四五六七八九十':
                        year += 40
                        i += 1
                    else:
                        year += 4
                else:
                    year += cn_num_to_arabic(char)
                i += 1
        # 中华民国年份 + 1911 = 公元年份
        return 1911 + year
    return None

def extract_year(title):
    """从标题中提取年份"""
    if not title:
        return None
    # 优先匹配 "民国XX年"
    year = parse_cn_republic_year(title)
    if year:
        return year
    # 匹配 四位数字年份
    match = re.search(r'(19|20)\d{2}', title)
    if match:
        return int(match.group())
    return None

def extract_dynasty(title):
    """从标题中提取朝代"""
    if not title:
        return None
    dynasties = ['秦', '汉', '三国', '晋', '南北朝', '隋', '唐', '五代', '宋', '元', '明', '清', '中华民国', '民国']
    for dynasty in dynasties:
        if dynasty in title:
            return dynasty
    return None

def extract_province(title):
    """从标题中提取省份"""
    if not title:
        return None
    provinces = [
        '北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
        '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
        '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾',
        '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门'
    ]
    for province in provinces:
        if province in title:
            return province
    return None

def extract_grade(title):
    """从标题中提取级别"""
    if not title:
        return None
    # 常见钱币级别
    grades = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
    grade_patterns = [
        r'([一二三四五六七八九十]+)级',
        r'第([一二三四五六七八九十]+)级',
        r'([一二三四五六七八九十]+)品'
    ]
    for pattern in grade_patterns:
        match = re.search(pattern, title)
        if match:
            grade_text = match.group(1)
            # 简化处理，直接返回匹配到的文本
            return grade_text
    return None

def to_artifact_view(item):
    """将数据库记录转换为视图格式"""
    text_data = json.loads(item['text'])
    # 使用字典访问方式获取Row对象的属性
    url = ''
    try:
        url = item['url']
    except KeyError:
        pass
    return {
        'pid': item['pid'],
        'url': url,
        'category': text_data.get('category', ''),
        'title': text_data.get('title', ''),
        'text_data': text_data,
        'year': extract_year(text_data.get('title', '')),
        'dynasty': extract_dynasty(text_data.get('title', '')),
        'province': extract_province(text_data.get('title', '')),
        'grade': extract_grade(text_data.get('title', ''))
    }