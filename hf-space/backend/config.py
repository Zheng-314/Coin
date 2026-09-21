# ==============================================================================
# 配置和常量
# ==============================================================================
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger('config')

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Flask配置
SECRET_KEY = os.getenv('SECRET_KEY') or 'your-super-secret-key-change-this-in-production'
JSON_AS_ASCII = False

# 路径配置
BASE_DIR = os.path.dirname(__file__)
USER_DB_PATH = os.path.join(BASE_DIR, 'instance', 'user.db')
ITEM_DB_PATH = os.path.join(BASE_DIR, 'instance', 'item.db')
PROJECT_ROOT_DIR = Path(BASE_DIR).parent
DATA_DIR = PROJECT_ROOT_DIR / "data"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
VECTOR_STORES_DIR = DATA_DIR / "vectors_stores"

# Neo4j配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# LLM配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_EMBED_API_BASE = os.getenv("OPENAI_EMBED_API_BASE", OPENAI_API_BASE)
OPENAI_EMBED_API_KEY = os.getenv("OPENAI_EMBED_API_KEY", OPENAI_API_KEY)
EMBED_PROVIDER_BLOCKED = "deepseek" in (OPENAI_EMBED_API_BASE or "").lower()

# 模型路径
YOLO_MODEL_PATH_1 = os.path.join(BASE_DIR, "best1.pt")
YOLO_MODEL_PATH_2 = os.path.join(BASE_DIR, "best2.pt")
ONNX_MODEL_PATH = os.path.join(BASE_DIR, "best_model.onnx")

# 导入状态
YOLO = None
YOLO_IMPORT_ERROR = None

def get_yolo():
    """延迟导入YOLO"""
    global YOLO, YOLO_IMPORT_ERROR
    if YOLO is None and YOLO_IMPORT_ERROR is None:
        try:
            from ultralytics import YOLO as _YOLO
            YOLO = _YOLO
            logger.info("YOLO导入成功")
        except Exception as e:
            YOLO_IMPORT_ERROR = str(e)
            logger.warning(f"YOLO导入失败，相关功能将不可用: {e}")
    return YOLO

# 暂时不导入YOLO，避免应用启动时的依赖问题

# LangChain / GraphRAG 可用性检查
RAG_IMPORTS_AVAILABLE = True
WEB_SEARCH_IMPORTS_AVAILABLE = True

try:
    import langchain_community  # noqa: F401 — 联网搜索依赖
except ImportError:
    WEB_SEARCH_IMPORTS_AVAILABLE = False

try:
    import langchain_graphrag  # noqa: F401 — 知识图谱搜索依赖
except ImportError:
    RAG_IMPORTS_AVAILABLE = False
    logger.warning("GraphRAG 相关依赖未完整安装，相关功能将降级")