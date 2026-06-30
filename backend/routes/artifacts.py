# ==============================================================================
# 钱币文物数据库路由
# ==============================================================================
import os
import json
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify
from utils.database import item_db
from utils.helpers import to_artifact_view
from config import DATA_DIR

logger = logging.getLogger('routes.artifacts')

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

    conditions = []
    params = []

    if search_query:
        conditions.append("text LIKE ?")
        params.append(f'%{search_query}%')
    if category_c0:
        conditions.append("c0 = ?")
        params.append(category_c0)
    # JSON字段在text列中，用LIKE做近似过滤，减少Python层处理量
    if dynasty:
        conditions.append("text LIKE ?")
        params.append(f'%{dynasty}%')
    if province:
        conditions.append("text LIKE ?")
        params.append(f'%{province}%')
    if grade:
        conditions.append("text LIKE ?")
        params.append(f'%{grade}%')

    where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit

    with item_db() as conn:
        # 先获取总数用于分页
        count_sql = f"SELECT COUNT(*) FROM item{where_clause}"
        total = conn.execute(count_sql, tuple(params)).fetchone()[0]

        # 带分页的查询
        data_sql = f"SELECT url, pid, text, c0 FROM item{where_clause} LIMIT ? OFFSET ?"
        items = conn.execute(data_sql, tuple(params) + (limit, offset)).fetchall()

    result = []
    for item in items:
        try:
            record = to_artifact_view(item)
            record['url'] = convert_image_url(record.get('url'))
            # 精确过滤（SQL LIKE可能有误匹配）
            if dynasty and record.get('dynasty') != dynasty:
                continue
            if province and record.get('province') != province:
                continue
            if grade and record.get('grade') != grade:
                continue
            if year_start is not None and (record.get('year') is None or record['year'] < year_start):
                continue
            if year_end is not None and (record.get('year') is None or record['year'] > year_end):
                continue
            result.append(record)
        except Exception:
            continue

    return jsonify(result)

@artifacts_bp.route('/api/artifacts/filters', methods=['GET'])
def get_artifact_filters():
    """获取筛选条件选项"""
    with item_db() as conn:
        # 只取需要的字段，减少数据传输
        items = conn.execute("SELECT text FROM item").fetchall()

    dynasties, provinces, grades, years = set(), set(), set(), set()
    for item in items:
        try:
            record = json.loads(item['text'])
        except Exception:
            continue
        if record.get('dynasty'):
            dynasties.add(record['dynasty'])
        if record.get('province'):
            provinces.add(record['province'])
        if record.get('grade'):
            grades.add(record['grade'])
        if record.get('year') is not None:
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

    with item_db() as conn:
        item = conn.execute("SELECT * FROM item WHERE pid = ?", (pid,)).fetchone()

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
        logger.error(f"解析text字段失败: {e}")

    return jsonify(item_dict)

@artifacts_bp.route('/api/kg/graph', methods=['GET'])
def get_kg_graph():
    """获取知识图谱数据，优先从Neo4j读取，降级到SQLite"""
    limit = request.args.get('limit', 320, type=int)

    # 尝试从Neo4j读取真实图谱数据
    try:
        from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n)-[r]->(m)
                RETURN n, r, m
                LIMIT $limit
                """,
                limit=limit
            )
            nodes_map = {}
            edges = []
            for record in result:
                n, rel, m = record['n'], record['r'], record['m']
                for node in (n, m):
                    nid = str(node.element_id)
                    if nid not in nodes_map:
                        props = dict(node)
                        label = props.get('name') or props.get('title') or props.get('id') or nid
                        node_type = list(node.labels)[0] if node.labels else 'Entity'
                        nodes_map[nid] = {
                            'id': nid,
                            'label': str(label)[:40],
                            'type': node_type,
                            'description': props.get('description', '')
                        }
                edges.append({
                    'from': str(n.element_id),
                    'to': str(m.element_id),
                    'label': rel.type
                })
        driver.close()
        return jsonify({'nodes': list(nodes_map.values()), 'edges': edges})
    except Exception as e:
        logger.error(f"Neo4j图谱读取失败，降级到SQLite: {e}")

    # 降级：从SQLite构建简单图谱
    with item_db() as conn:
        rows = conn.execute("SELECT pid, text FROM item LIMIT ?", (min(limit, 100),)).fetchall()

    formatted_nodes = []
    edges = []
    for i, node in enumerate(rows):
        try:
            text_data = json.loads(node['text'])
            title = text_data.get('title', f'Item {node["pid"]}')
            dynasty = text_data.get('dynasty', '')
            node_type = 'COIN'
        except Exception:
            title = f'Item {node["pid"]}'
            dynasty = ''
            node_type = 'COIN'

        formatted_nodes.append({
            'id': node['pid'],
            'label': title[:40],
            'type': node_type,
            'description': dynasty
        })
        if i > 0:
            edges.append({
                'from': rows[i - 1]['pid'],
                'to': node['pid'],
                'label': 'RELATED_TO'
            })

    return jsonify({'nodes': formatted_nodes, 'edges': edges})