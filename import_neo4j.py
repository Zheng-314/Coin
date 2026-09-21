"""
Neo4j 知识图谱导入脚本 v2.0
=============================
从 GraphRAG 构件（entities.parquet + relationships.parquet）导入 Neo4j，
完整保留所有字段：degree、weight、rank、communities、description 等。

产品逻辑：
- 节点 type 直接使用 GraphRAG 产出的 entity_type，不再用关键词猜测覆盖
- 关系类型从 description 中提取关键词（英文描述 → 中文关系标签）
- degree/weight/rank 写入 Neo4j，供前端实现视觉分层

运行前需设置环境变量：NEO4J_PASSWORD（必填）、NEO4J_URI、NEO4J_USER（可选）。
"""

import os
import pandas as pd
import sys
import logging
from pathlib import Path
from py2neo import Graph, Node, Relationship

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# ========================== 配置区域 ==========================
# 连接信息从环境变量读取，避免把口令写进版本库
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_PASSWORD:
    logger.error("未设置环境变量 NEO4J_PASSWORD，无法连接 Neo4j。")
    logger.error("请先设置，例如：set NEO4J_PASSWORD=你的密码（Windows）")
    sys.exit(1)

ARTIFACTS_PATH = Path("./data/artifacts/")

# ========================== 关系类型映射 ==========================
# 从 GraphRAG relationship description（英文）中提取关键词，映射为中文关系标签
# 产品逻辑：用户看到的是有语义的中文标签，不是空格，不是英文术语
RELATION_KEYWORD_MAP = [
    # (英文关键词, 中文标签, 优先级，数字越小越优先)
    ("coin-related terms", "同类术语", 1),
    ("both are coin", "同类术语", 2),
    ("proof coin", "精制币概念", 3),
    ("mint mark", "铸币标识", 3),
    ("same dynasty", "同期铸造", 1),
    ("same province", "同省铸造", 1),
    ("derived from", "版别演变", 1),
    ("variety of", "版别包含", 1),
    ("contrast", "概念对比", 2),
    ("visual effect", "视觉效果", 3),
    ("grading term", "评级术语", 1),
    ("coin grading", "评级相关", 2),
    ("numismatic", "钱币学术语", 2),
    ("minted in", "铸造于", 1),
    ("issued by", "发行机构", 1),
    ("designed by", "设计者", 1),
    ("related to", "相关概念", 5),
    ("associated with", "关联概念", 5),
    ("part of", "包含关系", 2),
    ("similar to", "近似概念", 3),
    ("also known as", "别称", 1),
    ("refers to", "指代", 3),
    ("emphasizes", "强调", 4),
    ("indicates", "表示", 4),
    ("describes", "描述", 4),
]


def extract_relation_type(description: str) -> str:
    """
    从关系描述文本中提取中文关系标签。

    产品逻辑：
    - 优先匹配精确关键词（如 "same dynasty" → "同期铸造"）
    - 未匹配到任何关键词时，根据文本长度启发式判断：
      短描述 → "相关概念"，长描述 → 取前 6 个字作为标签
    - 绝不返回空字符串或空格
    """
    if not isinstance(description, str) or not description.strip():
        return "关联关系"

    text_lower = description.lower()

    # 按优先级排序匹配
    matches = []
    for keyword, label, priority in RELATION_KEYWORD_MAP:
        if keyword in text_lower:
            matches.append((priority, label))

    if matches:
        matches.sort(key=lambda x: x[0])
        return matches[0][1]

    # 没有匹配到关键词，启发式处理
    # 英文描述 → 直接标记为"关联概念"
    if description[:1].isascii():
        return "关联概念"

    # 中文描述 → 截取前6个字符
    return description[:6] if len(description) >= 6 else description


def extract_node_label(entity_type: str) -> str:
    """
    将 GraphRAG 的 entity_type 映射为 Neo4j 节点标签。
    直接使用原始类型，不做关键词猜测。

    产品逻辑：GraphRAG 输出的 type 字段已经完成了实体分类，
    不需要自己再猜一遍（猜得没它准）。
    """
    if not isinstance(entity_type, str) or not entity_type.strip():
        return "Entity"

    # 标准化：全大写，去空格
    normalized = entity_type.strip().upper()
    if normalized in ("EVENT", "ORGANIZATION", "PERSON", "GEO"):
        return normalized
    return "Entity"


def main():
    """主函数：加载 GraphRAG 构件并导入 Neo4j"""

    # --- 步骤 1: 检查文件 ---
    entities_file = ARTIFACTS_PATH / "entities.parquet"
    relationships_file = ARTIFACTS_PATH / "relationships.parquet"

    if not entities_file.exists() or not relationships_file.exists():
        logger.error(f"找不到 GraphRAG 构件文件:\n  - {entities_file}\n  - {relationships_file}")
        sys.exit(1)

    logger.info("正在加载 entities 和 relationships ...")
    df_entities = pd.read_parquet(entities_file)
    df_relationships = pd.read_parquet(relationships_file)
    logger.info(f"加载完成：{len(df_entities)} 个实体，{len(df_relationships)} 条关系")

    # --- 步骤 2: 连接 Neo4j 并清空 ---
    try:
        graph_db = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        logger.info("成功连接到 Neo4j 数据库")
        graph_db.delete_all()
        logger.info("数据库已清空，准备导入")
    except Exception as e:
        logger.error(f"无法连接 Neo4j: {e}")
        sys.exit(1)

    # --- 步骤 3: 导入节点 ---
    # 产品逻辑：
    # - type 直接用 entity_type，不自己猜
    # - 完整写入 degree、communities、description，供前端分层和 tooltip 使用
    logger.info(f"正在导入 {len(df_entities)} 个节点...")
    node_map = {}

    # 计算 max_degree 用于归一化（前端节点大小映射）
    degrees = df_entities['degree'].dropna()
    max_degree = int(degrees.max()) if len(degrees) > 0 else 1

    for _, row in df_entities.iterrows():
        entity_name = str(row.get('title', ''))
        if not entity_name:
            continue

        entity_type = str(row.get('type', '')) if pd.notna(row.get('type')) else ''
        node_label = extract_node_label(entity_type)
        degree_val = int(row.get('degree', 1)) if pd.notna(row.get('degree')) else 1

        # 社区信息：用于前端分组配色
        communities_raw = row.get('communities')
        if pd.notna(communities_raw) and communities_raw is not None:
            communities_str = str(communities_raw)
        else:
            communities_str = "[]"

        properties = {
            'name': entity_name,
            'title': entity_name,
            'type': entity_type,                    # GraphRAG 原始类型，不做修改
            'description': str(row.get('description', '')) if pd.notna(row.get('description')) else '',
            'degree': degree_val,
            'max_degree': max_degree,               # 全局最大 degree，供前端归一化
            'communities': communities_str,
            'human_readable_id': int(row.get('human_readable_id', 0)) if pd.notna(row.get('human_readable_id')) else 0,
            'node_label': entity_name[:40],          # 短标签，前端显示用
        }

        node = Node(node_label, **properties)
        graph_db.create(node)
        node_map[entity_name] = node

    logger.info(f"节点导入完成（max_degree={max_degree}）")

    # --- 步骤 4: 导入关系 ---
    # 产品逻辑：
    # - 关系类型使用 extract_relation_type() 从 description 提取中文标签
    # - 完整写入 weight、rank、description，供前端边粗细筛选和 tooltip 使用
    logger.info(f"正在导入 {len(df_relationships)} 条关系...")

    skipped = 0
    max_rank = int(df_relationships['rank'].max()) if 'rank' in df_relationships.columns and len(df_relationships) > 0 else 1
    max_weight = float(df_relationships['weight'].max()) if 'weight' in df_relationships.columns and len(df_relationships) > 0 else 1.0

    for _, row in df_relationships.iterrows():
        source_name = str(row.get('source', ''))
        target_name = str(row.get('target', ''))

        if source_name not in node_map or target_name not in node_map:
            skipped += 1
            continue

        source_node = node_map[source_name]
        target_node = node_map[target_name]

        # 核心改动：从 description 提取有意义的中文关系标签
        description = str(row.get('description', '')) if pd.notna(row.get('description')) else ''
        relation_type = extract_relation_type(description)

        weight_val = float(row.get('weight', 1.0)) if pd.notna(row.get('weight')) else 1.0
        rank_val = int(row.get('rank', 0)) if pd.notna(row.get('rank')) else 0

        rel_properties = {
            'description': description,
            'weight': weight_val,
            'max_weight': max_weight,
            'rank': rank_val,
            'max_rank': max_rank,
            'source_degree': int(row.get('source_degree', 0)) if pd.notna(row.get('source_degree')) else 0,
            'target_degree': int(row.get('target_degree', 0)) if pd.notna(row.get('target_degree')) else 0,
        }

        rel = Relationship(source_node, relation_type, target_node, **rel_properties)
        graph_db.create(rel)

    if skipped:
        logger.warning(f"跳过了 {skipped} 条关系（源或目标节点不存在）")
    logger.info(f"关系导入完成（max_rank={max_rank}, max_weight={max_weight:.1f}）")

    # --- 步骤 5: 创建索引 ---
    logger.info("正在创建索引...")
    try:
        graph_db.run("CREATE INDEX entity_name_index IF NOT EXISTS FOR (n:Entity) ON (n.name)")
        graph_db.run("CREATE INDEX event_name_index IF NOT EXISTS FOR (n:EVENT) ON (n.name)")
        graph_db.run("CREATE INDEX org_name_index IF NOT EXISTS FOR (n:ORGANIZATION) ON (n.name)")
        graph_db.run("CREATE INDEX person_name_index IF NOT EXISTS FOR (n:PERSON) ON (n.name)")
        graph_db.run("CREATE INDEX geo_name_index IF NOT EXISTS FOR (n:GEO) ON (n.name)")
        logger.info("索引创建完成")
    except Exception as e:
        logger.warning(f"索引创建跳过（可能 Neo4j 版本不支持 IF NOT EXISTS）: {e}")

    logger.info("=" * 60)
    logger.info("知识图谱导入完成！")
    logger.info(f"  节点: {len(df_entities)}")
    logger.info(f"  关系: {len(df_relationships) - skipped} / {len(df_relationships)}")
    logger.info(f"  节点类型: {df_entities['type'].dropna().unique().tolist()}")
    logger.info(f"  max_degree: {max_degree}, max_rank: {max_rank}, max_weight: {max_weight:.1f}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
