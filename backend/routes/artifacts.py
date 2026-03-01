# ==============================================================================
# 钱币文物数据库路由
# ==============================================================================
import os
import json
from pathlib import Path
from flask import Blueprint, request, jsonify
from utils.database import get_item_db_connection
from utils.helpers import to_artifact_view
from config import DATA_DIR

artifacts_bp = Blueprint('artifacts', __name__)

def convert_image_url(original_url):
    """
    将本地文件路径转换为API访问路径
    例如: d:/code/data/artifacts/xxx.jpg -> http://localhost:5001/api/images/artifacts/xxx.jpg
    """
    if not original_url:
        return original_url

    try:
        # 如果已经是http URL，直接返回
        if original_url.startswith('http://') or original_url.startswith('https://'):
            return original_url

        # 尝试解析为Path对象
        original_path = Path(original_url)

        # 检查是否是绝对路径且在DATA_DIR下
        try:
            relative_path = original_path.relative_to(DATA_DIR)
            # 转换为API路径
            return f'/api/images/{relative_path.as_posix()}'
        except ValueError:
            # 不在DATA_DIR下，返回原URL
            return original_url
    except Exception:
        return original_url

@artifacts_bp.route('/api/artifacts/classification', methods=['GET'])
def get_classification():
    """获取文物分类"""
    try:
        classification_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'classification.json')
        with open(classification_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"message": "分类文件未找到"}), 404

@artifacts_bp.route('/api/artifacts/searchItems', methods=['GET'])
def get_artifacts():
    """搜索文物列表（分页）"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search_query = request.args.get('q', None)
    category_c0 = request.args.get('c0', None)
    dynasty = request.args.get('dynasty', '').strip()
    province = request.args.get('province', '').strip()
    grade = request.args.get('grade', '').strip()
    year_start = request.args.get('year_start', type=int)
    year_end = request.args.get('year_end', type=int)

    print(f"DEBUG: 请求参数 - page: {page}, limit: {limit}, q: {search_query}, c0: {category_c0}")
    print(f"DEBUG: 筛选参数 - dynasty: {dynasty}, province: {province}, grade: {grade}")
    print(f"DEBUG: 年份参数 - year_start: {year_start}, year_end: {year_end}")

    query = "SELECT url, pid, text, c0 FROM item"
    params = []
    conditions = []

    if search_query:
        conditions.append("text LIKE ?")
        params.append(f'%{search_query}%')

    if category_c0:
        conditions.append("c0 = ?")
        params.append(category_c0)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    print(f"DEBUG: 执行SQL: {query}")
    print(f"DEBUG: SQL参数: {params}")

    conn = None
    try:
        conn = get_item_db_connection()
        items = conn.execute(query, tuple(params)).fetchall()
        print(f"DEBUG: 数据库查询结果: {len(items)} 条记录")
    finally:
        if conn:
            conn.close()

    # 后处理筛选
    filtered = []
    exception_count = 0
    dynasty_filter_count = 0
    province_filter_count = 0
    grade_filter_count = 0
    year_filter_count = 0

    for item in items:
        try:
            record = to_artifact_view(item)
            # 转换图片URL
            record['url'] = convert_image_url(record.get('url'))
        except Exception as e:
            exception_count += 1
            continue

        # 应用筛选条件
        if dynasty and record['dynasty'] != dynasty:
            dynasty_filter_count += 1
            continue
        if province and record['province'] != province:
            province_filter_count += 1
            continue
        if grade and record['grade'] != grade:
            grade_filter_count += 1
            continue
        if year_start is not None and (record['year'] is None or record['year'] < year_start):
            year_filter_count += 1
            continue
        if year_end is not None and (record['year'] is None or record['year'] > year_end):
            year_filter_count += 1
            continue
        filtered.append(record)

    print(f"DEBUG: 后处理筛选结果 - 总记录: {len(items)}, 成功处理: {len(filtered) + exception_count + dynasty_filter_count + province_filter_count + grade_filter_count + year_filter_count}")
    print(f"DEBUG: 筛选详情 - 异常: {exception_count}, 朝代筛选: {dynasty_filter_count}, 省份筛选: {province_filter_count}, 等级筛选: {grade_filter_count}, 年份筛选: {year_filter_count}")
    print(f"DEBUG: 最终筛选结果: {len(filtered)} 条记录")

    offset = (page - 1) * limit
    paged = filtered[offset: offset + limit]
    print(f"DEBUG: 分页结果 - 偏移: {offset}, 限制: {limit}, 返回: {len(paged)} 条记录")
    
    return jsonify(paged)

@artifacts_bp.route('/api/artifacts/filters', methods=['GET'])
def get_artifact_filters():
    """获取筛选条件选项"""
    conn = None
    try:
        conn = get_item_db_connection()
        items = conn.execute("SELECT url, pid, text, c0 FROM item").fetchall()
    finally:
        if conn:
            conn.close()

    dynasties = set()
    provinces = set()
    grades = set()
    years = set()

    for item in items:
        try:
            record = to_artifact_view(item)
        except Exception:
            continue
        if record['dynasty']:
            dynasties.add(record['dynasty'])
        if record['province']:
            provinces.add(record['province'])
        if record['grade']:
            grades.add(record['grade'])
        if record['year'] is not None:
            years.add(record['year'])

    sorted_years = sorted(years)
    return jsonify({
        'dynasties': sorted(dynasties),
        'provinces': sorted(provinces),
        'grades': sorted(grades),
        'years': sorted_years,
        'year_min': sorted_years[0] if sorted_years else None,
        'year_max': sorted_years[-1] if sorted_years else None
    })

@artifacts_bp.route('/api/artifacts/search', methods=['GET'])
def get_artifact_by_id():
    """根据ID获取单个文物详情"""
    pid = request.args.get('id')
    if not pid:
        return jsonify({"message": "需要提供文物ID"}), 400

    conn = get_item_db_connection()
    item = conn.execute("SELECT * FROM item WHERE pid = ?", (pid,)).fetchone()
    conn.close()

    if not item:
        return jsonify({"message": "文物未找到"}), 404

    item_dict = dict(item)
    # 转换图片URL
    item_dict['url'] = convert_image_url(item_dict.get('url'))

    # 解析text字段中的JSON数据
    try:
        text_data = json.loads(item_dict.get('text', '{}'))
        # 将text_data中的字段添加到item_dict中
        for key, value in text_data.items():
            item_dict[key] = value
        # 可以选择删除原始的text字段，或者保留它
        # del item_dict['text']
    except Exception as e:
        print(f"解析text字段失败: {e}")

    return jsonify(item_dict)

@artifacts_bp.route('/api/kg/graph', methods=['GET'])
def get_kg_graph():
    """获取知识图谱数据"""
    conn = None
    try:
        conn = get_item_db_connection()
        nodes = conn.execute("SELECT pid, text FROM item LIMIT 100").fetchall()
    finally:
        if conn:
            conn.close()

    formatted_nodes = []
    edges = []

    for i, node in enumerate(nodes):
        try:
            text_data = json.loads(node['text'])
            title = text_data.get('title', f'Item {node["pid"]}')
            category = text_data.get('category', 'unknown')
        except Exception:
            title = f'Item {node["pid"]}'
            category = 'unknown'

        formatted_nodes.append({
            'id': node['pid'],
            'label': title[:30],  # 截断标题
            'category': category
        })

        # 简单的边生成（实际应用中应从关系中获取）
        if i > 0:
            edges.append({
                'source': nodes[i-1]['pid'],
                'target': node['pid'],
                'label': 'related'
            })

    return jsonify({
        'nodes': formatted_nodes,
        'edges': edges
    })