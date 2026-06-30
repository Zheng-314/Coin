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

# LangChain / GraphRAG 相关依赖
RAG_IMPORTS_AVAILABLE = True
WEB_SEARCH_IMPORTS_AVAILABLE = True

try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    try:
        from langchain_core.output_parsers import StrOutputParser
    except ImportError:
        # 忽略StrOutputParser导入错误，因为在rag_service.py中实际上没有使用它
        pass
except ImportError as e:
    WEB_SEARCH_IMPORTS_AVAILABLE = False
    logger.warning(f"联网搜索相关依赖未完整安装，web search 将不可用: {e}")

try:
    from langchain_graphrag.query.global_search import GlobalSearch
    from langchain_graphrag.query.global_search.community_weight_calculator import CommunityWeightCalculator
    from langchain_graphrag.query.global_search.key_points_aggregator import (
        KeyPointsAggregator, KeyPointsAggregatorPromptBuilder, KeyPointsContextBuilder
    )
    from langchain_graphrag.query.global_search.key_points_generator import (
        CommunityReportContextBuilder, KeyPointsGenerator, KeyPointsGeneratorPromptBuilder
    )
    from langchain_graphrag.query.local_search import LocalSearch, LocalSearchPromptBuilder, LocalSearchRetriever
    from langchain_graphrag.query.local_search.context_builders import ContextBuilder
    from langchain_graphrag.query.local_search.context_selectors import ContextSelector
    from langchain_graphrag.types.graphs.community import CommunityLevel
    from langchain_graphrag.utils import TiktokenCounter
    from langchain_graphrag.indexing.artifacts import IndexerArtifacts
    # 暂时跳过Chroma导入，避免Python 3.13兼容性问题
    # from langchain_chroma.vectorstores import Chroma as ChromaVectorStore
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
except ImportError as e:
    RAG_IMPORTS_AVAILABLE = False
    # 不要将WEB_SEARCH_IMPORTS_AVAILABLE设置为False，这样即使GraphRAG不可用，联网搜索仍然可以使用
    logger.warning(f"GraphRAG 相关依赖未完整安装，相关功能将降级: {e}")