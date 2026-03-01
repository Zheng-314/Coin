import pandas as pd
import re
from pathlib import Path
from py2neo import Graph, Node, Relationship # 重新导入 Relationship
import sys

# ========================== 1. 配置区域 ==========================
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "wode19741211"

ARTIFACTS_PATH = Path("./data/artifacts/")
ENTITY_NAME_COLUMN = 'title'

# ==============================================================================

def assign_label(row):
    """根据DataFrame行数据中的信息，智能分配一个标签。"""
    title = str(row.get(ENTITY_NAME_COLUMN, ''))
    description = str(row.get('description', ''))
    combined_text = (title + ' ' + description).lower()
    
    if 'coin' in combined_text or '银元' in combined_text or '硬币' in combined_text: return 'Coin'
    if 'price' in combined_text or '价格' in combined_text: return 'Price'
    if 'appearance' in combined_text or '外观' in combined_text: return 'Appearance'
    if 'auction' in combined_text or '拍卖' in combined_text: return 'Auction'
    if 'mint' in combined_text or '造币厂' in combined_text: return 'Mint'
    if 'person' in combined_text or '人' in combined_text: return 'Person'
    if 'year' in combined_text or '年' in combined_text: return 'Year'
    
    node_type = row.get('type')
    if isinstance(node_type, str) and node_type.strip(): return node_type
        
    return 'Entity'

def main():
    """主函数，加载实体和关系并将其导入到Neo4j。"""
    # --- 步骤 1: 检查并加载实体和关系文件 ---
    entities_file = ARTIFACTS_PATH / "entities.parquet"
    relationships_file = ARTIFACTS_PATH / "relationships.parquet"

    if not entities_file.exists() or not relationships_file.exists():
        print(f"错误: 找不到必要的artifact文件。请确保以下文件存在:\n- {entities_file}\n- {relationships_file}")
        sys.exit(1)

    print("正在加载 entities 和 relationships ...")
    df_entities = pd.read_parquet(entities_file)
    df_relationships = pd.read_parquet(relationships_file) # 恢复加载关系
    print("文件加载成功。")

    # --- 步骤 2: 连接数据库并清空 ---
    try:
        graph_db = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print("成功连接到 Neo4j 数据库。")
        graph_db.delete_all()
        print("数据库已清空。")
    except Exception as e:
        print(f"无法连接到 Neo4j 数据库。错误: {e}")
        sys.exit(1)
        
    # --- 步骤 3: 导入节点 (Entities) ---
    print(f"正在导入 {len(df_entities)} 个节点...")
    node_map = {}
    for _, row in df_entities.iterrows():
        node_label = assign_label(row)
        entity_name = row[ENTITY_NAME_COLUMN]
        
        properties = {
            'id': entity_name,
            'name': entity_name,
            'description': row.get('description', ''),
            'community_ids': str(row.get('community_ids', [])),
            'custom_label': node_label
        }
        
        node = Node(node_label, **properties)
        graph_db.create(node)
        node_map[entity_name] = node # 使用实体名称作为映射的键
        
    print("节点导入完成。")
    
    # --- 步骤 4: 恢复关系导入 ---
    print(f"正在导入 {len(df_relationships)} 个关系...")
    for _, row in df_relationships.iterrows():
        source_name = row['source']
        target_name = row['target']
        
        if source_name in node_map and target_name in node_map:
            source_node = node_map[source_name]
            target_node = node_map[target_name]
            
            # 为所有关系设置一个统一、有效的内部类型
            relation_type = " "
            
            rel_properties = {
                'description': row.get('description', ''),
                'weight': row.get('weight', 1.0)
            }
            
            rel = Relationship(source_node, relation_type, target_node, **rel_properties)
            graph_db.create(rel)
            
    print("关系导入完成。")
    print("\n知识图谱（节点和关系）已成功导入 Neo4j！")

if __name__ == "__main__":
    main()