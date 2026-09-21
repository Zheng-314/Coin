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
    """
    获取知识图谱数据，优先从Neo4j读取，降级到 parquet/SQLite。

    产品逻辑：
    - 返回节点含 degree（用于大小映射）和 communities（用于分组配色）
    - 返回边含 weight/rank/description（用于粗细筛选和 tooltip）
    - 前端可通过 min_rank 参数过滤低质量边，默认显示全部
    """
    limit = request.args.get('limit', 80, type=int)
    min_rank = request.args.get('min_rank', None, type=int)

    # --- 路径1：从 Neo4j 读取 ---
    try:
        from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # 按 rank 排序取最重要的边
            result = session.run(
                """
                MATCH (n)-[r]->(m)
                RETURN n, r, m
                ORDER BY r.rank DESC
                LIMIT $limit
                """,
                limit=limit
            )
            nodes_map = {}
            edges = []
            for record in result:
                n, rel, m = record['n'], record['r'], record['m']

                # rank 过滤
                rel_rank = rel.get('rank', 0) or 0
                if min_rank is not None and rel_rank < min_rank:
                    continue

                for node in (n, m):
                    nid = str(node.element_id)
                    if nid not in nodes_map:
                        props = dict(node)
                        node_label = props.get('node_label') or props.get('name') or props.get('title') or props.get('id') or nid
                        node_type = list(node.labels)[0] if node.labels else 'Entity'
                        node_degree = props.get('degree', 1) or 1
                        try:
                            node_degree = int(node_degree)
                        except (ValueError, TypeError):
                            node_degree = 1

                        nodes_map[nid] = {
                            'id': nid,
                            'label': str(node_label)[:40],
                            'type': node_type,
                            'description': props.get('description', ''),
                            'degree': node_degree,
                            'communities': props.get('communities', '[]'),
                        }

                rel_weight = rel.get('weight', 1.0) or 1.0
                try:
                    rel_weight = float(rel_weight)
                except (ValueError, TypeError):
                    rel_weight = 1.0

                edges.append({
                    'from': str(n.element_id),
                    'to': str(m.element_id),
                    'label': rel.type,                          # 中文关系标签（来自 import_neo4j.py）
                    'description': rel.get('description', ''),  # 完整描述，hover tooltip 用
                    'weight': rel_weight,
                    'rank': rel_rank,
                })
        driver.close()
        logger.info(f"Neo4j 图谱查询完成：{len(nodes_map)} 节点，{len(edges)} 边")
        return jsonify({'nodes': list(nodes_map.values()), 'edges': edges})
    except Exception as e:
        logger.warning(f"Neo4j图谱读取失败，降级到 parquet/SQLite: {e}")

    # --- 路径2（降级）：从 Parquet 直接读取 ---
    # 产品逻辑：不依赖 Neo4j，GraphRAG 的 parquet 文件本身就够用
    try:
        from config import ARTIFACTS_DIR
        entities_path = ARTIFACTS_DIR / "entities.parquet"
        relationships_path = ARTIFACTS_DIR / "relationships.parquet"
        if entities_path.exists() and relationships_path.exists():
            import pandas as pd
            df_e = pd.read_parquet(entities_path)
            df_r = pd.read_parquet(relationships_path)

            nodes = []
            for _, row in df_e.iterrows():
                entity_name = str(row.get('title', ''))
                degree_val = int(row.get('degree', 1)) if pd.notna(row.get('degree')) else 1
                # 使用实体名称（title）作为节点 ID，与边的 source/target 匹配
                nodes.append({
                    'id': str(entity_name),
                    'label': str(entity_name)[:40],
                    'type': str(row.get('type', 'Entity')),
                    'description': str(row.get('description', '')) if pd.notna(row.get('description')) else '',
                    'degree': degree_val,
                    'communities': str(row.get('communities', '[]')),
                })

            edges = []
            for _, row in df_r.head(limit).iterrows():
                rank_val = int(row.get('rank', 0)) if pd.notna(row.get('rank')) else 0
                if min_rank is not None and rank_val < min_rank:
                    continue
                edges.append({
                    'from': str(row.get('source', '')),
                    'to': str(row.get('target', '')),
                    'label': '关联概念',
                    'description': str(row.get('description', '')) if pd.notna(row.get('description')) else '',
                    'weight': float(row.get('weight', 1.0)) if pd.notna(row.get('weight')) else 1.0,
                    'rank': rank_val,
                })

            logger.info(f"Parquet 降级读取完成：{len(nodes)} 节点，{len(edges)} 边")
            return jsonify({'nodes': nodes, 'edges': edges})
    except Exception as e2:
        logger.warning(f"Parquet 降级也失败，回退到 SQLite: {e2}")

    # --- 路径3（最终兜底）：SQLite ---
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
            'description': dynasty,
            'degree': 1
        })
        if i > 0:
            edges.append({
                'from': rows[i - 1]['pid'],
                'to': node['pid'],
                'label': '相关条目',
                'description': '',
                'weight': 1.0,
                'rank': 0
            })

    return jsonify({'nodes': formatted_nodes, 'edges': edges})