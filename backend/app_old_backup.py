from email import message
import sqlite3
import bcrypt
import jwt
import os
import json
import pandas as pd
import pickle
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import functools
from pathlib import Path
from typing import cast, Any
import sys
import importlib.util
import io
import cv2
import numpy as np
from PIL import Image
from scipy.special import softmax
import base64
import subprocess
from werkzeug.utils import secure_filename
import traceback
import re

YOLO = None
YOLO_IMPORT_ERROR = None
try:
    from ultralytics import YOLO as _YOLO
    YOLO = _YOLO
except Exception as e:
    YOLO_IMPORT_ERROR = str(e)

# LangChain / GraphRAG 相关依赖采用可选导入，避免环境不完整时直接启动失败
RAG_IMPORTS_AVAILABLE = True
WEB_SEARCH_IMPORTS_AVAILABLE = True
try:
    from langchain_graphrag.query.global_search import GlobalSearch
    from langchain_graphrag.query.global_search.community_weight_calculator import (
        CommunityWeightCalculator
    )
    from langchain_graphrag.query.global_search.key_points_aggregator import (
        KeyPointsAggregator,
        KeyPointsAggregatorPromptBuilder,
        KeyPointsContextBuilder
    )
    from langchain_graphrag.query.global_search.key_points_generator import (
        CommunityReportContextBuilder,
        KeyPointsGenerator,
        KeyPointsGeneratorPromptBuilder
    )
    from langchain_graphrag.query.local_search import LocalSearch, LocalSearchPromptBuilder, LocalSearchRetriever
    from langchain_graphrag.query.local_search.context_builders import ContextBuilder
    from langchain_graphrag.query.local_search.context_selectors import ContextSelector
    from langchain_graphrag.types.graphs.community import CommunityLevel
    from langchain_graphrag.utils import TiktokenCounter
    from langchain_graphrag.indexing.artifacts import IndexerArtifacts
    from langchain_chroma.vectorstores import Chroma as ChromaVectorStore
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
except ImportError as e:
    RAG_IMPORTS_AVAILABLE = False
    WEB_SEARCH_IMPORTS_AVAILABLE = False
    print(f"GraphRAG 相关依赖未完整安装，相关功能将降级: {e}")

try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
except ImportError as e:
    WEB_SEARCH_IMPORTS_AVAILABLE = False
    print(f"联网搜索相关依赖未完整安装，web search 将不可用: {e}")


# ==============================================================================
# 初始化设置 (Flask 应用与环境)
# ==============================================================================
# 固定加载 backend 目录下的 .env，避免 Windows reloader 下工作目录漂移导致读取失败
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*")

# 来自 app.py 的配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or 'your-super-secret-key-change-this-in-production'
app.config['JSON_AS_ASCII'] = False

# 数据库路径
BASE_DIR = os.path.dirname(__file__)
USER_DB_PATH = os.path.join(BASE_DIR, 'instance', 'user.db')
ITEM_DB_PATH = os.path.join(BASE_DIR, 'instance', 'item.db')
PROJECT_ROOT_DIR = Path(BASE_DIR).parent
DATA_DIR = PROJECT_ROOT_DIR / "data"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
VECTOR_STORES_DIR = DATA_DIR / "vectors_stores"

# LLM 配置（必须从环境变量读取，禁止硬编码）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_EMBED_API_BASE = os.getenv("OPENAI_EMBED_API_BASE", OPENAI_API_BASE)
OPENAI_EMBED_API_KEY = os.getenv("OPENAI_EMBED_API_KEY", OPENAI_API_KEY)
EMBED_PROVIDER_BLOCKED = "deepseek" in (OPENAI_EMBED_API_BASE or "").lower()

print("正在加载所有模型，请稍候...")
# 使用绝对路径，避免从不同工作目录启动时加载失败
YOLO_MODEL_PATH_1 = os.path.join(BASE_DIR, "best1.pt")
YOLO_MODEL_PATH_2 = os.path.join(BASE_DIR, "best2.pt")
ONNX_MODEL_PATH = os.path.join(BASE_DIR, "best_model.onnx")

yolo_model1 = None
yolo_model2 = None
onnx_session = None
onnx_input_names = []
onnx_output_names = []
predict_model_errors = []

try:
    import onnxruntime
except Exception as e:
    onnxruntime = None
    predict_model_errors.append(f"onnxruntime 导入失败: {e}")

if YOLO is None:
    predict_model_errors.append(f"ultralytics 导入失败，将跳过 YOLO 预处理: {YOLO_IMPORT_ERROR}")

try:
    if YOLO is None:
        raise RuntimeError("YOLO 不可用")
    if os.path.exists(YOLO_MODEL_PATH_1):
        yolo_model1 = YOLO(YOLO_MODEL_PATH_1)
    else:
        predict_model_errors.append(f"缺少 YOLO 模型文件: {YOLO_MODEL_PATH_1}")
except Exception as e:
    predict_model_errors.append(f"加载 YOLO1 失败: {e}")

try:
    if YOLO is None:
        raise RuntimeError("YOLO 不可用")
    if os.path.exists(YOLO_MODEL_PATH_2):
        yolo_model2 = YOLO(YOLO_MODEL_PATH_2)
    else:
        predict_model_errors.append(f"缺少 YOLO 模型文件: {YOLO_MODEL_PATH_2}")
except Exception as e:
    predict_model_errors.append(f"加载 YOLO2 失败: {e}")

try:
    if onnxruntime is None:
        raise RuntimeError("onnxruntime 不可用")
    if not os.path.exists(ONNX_MODEL_PATH):
        raise FileNotFoundError(f"缺少 ONNX 模型文件: {ONNX_MODEL_PATH}")
    onnx_session = onnxruntime.InferenceSession(ONNX_MODEL_PATH)
    onnx_input_names = [x.name for x in onnx_session.get_inputs()]
    onnx_output_names = [x.name for x in onnx_session.get_outputs()]
except Exception as e:
    predict_model_errors.append(f"加载 ONNX 失败: {e}")

if onnx_session is not None:
    print("推理核心模型 ONNX 加载成功")
else:
    print("推理核心模型 ONNX 未就绪，将返回可诊断错误")

if predict_model_errors:
    print("模型加载告警:")
    for err in predict_model_errors:
        print(f" - {err}")


def ensure_onnx_session_ready():
    """
    运行时兜底：如果启动阶段未成功加载 ONNX，会在请求阶段再尝试一次。
    """
    global onnx_session, onnxruntime, onnx_input_names, onnx_output_names
    if onnx_session is not None:
        return True, ""

    try:
        if onnxruntime is None:
            import onnxruntime as ort
            onnxruntime = ort

        if not os.path.exists(ONNX_MODEL_PATH):
            return False, f"缺少 ONNX 模型文件: {ONNX_MODEL_PATH}"

        onnx_session = onnxruntime.InferenceSession(ONNX_MODEL_PATH)
        onnx_input_names = [x.name for x in onnx_session.get_inputs()]
        onnx_output_names = [x.name for x in onnx_session.get_outputs()]
        return True, ""
    except Exception as e:
        return False, str(e)




# ==============================================================================
# GraphRAG 问答系统设置 (来自 KQapp.py)
# ==============================================================================
print("正在初始化 GraphRAG 问答系统...")

def load_artifacts(path: Path) -> Any:
    """从指定路径读取 GraphRAG 的构件 (artifacts)。"""
    print(f"正在从以下路径加载构件: {path}")
    entities = pd.read_parquet(path / "artifacts/entities.parquet")
    relationships = pd.read_parquet(path / "artifacts/relationships.parquet")
    text_units = pd.read_parquet(path / "artifacts/text_units.parquet")
    communities_reports = pd.read_parquet(path / "artifacts/communities_reports.parquet")

    merged_graph, summarized_graph, communities = None, None, None

    merged_graph_pickled = path / "merged-graph.pickle"
    if merged_graph_pickled.exists():
        with merged_graph_pickled.open("rb") as fp:
            merged_graph = pickle.load(fp)

    summarized_graph_pickled = path / "summarized-graph.pickle"
    if summarized_graph_pickled.exists():
        with summarized_graph_pickled.open("rb") as fp:
            summarized_graph = pickle.load(fp)

    community_info_pickled = path / "community_info.pickle"
    if community_info_pickled.exists():
        with community_info_pickled.open("rb") as fp:
            communities = pickle.load(fp)

    return IndexerArtifacts(
        entities=entities,
        relationships=relationships,
        text_units=text_units,
        communities_reports=communities_reports,
        merged_graph=merged_graph,
        summarized_graph=summarized_graph,
        communities=communities,
    )

# --- 加载构件并初始化组件 ---
llm = None
artifacts = None
global_search_engine = None
local_search_chain = None

if not OPENAI_API_KEY:
    print("未检测到 OPENAI_API_KEY，GraphRAG 和联网总结功能将不可用。")
elif not RAG_IMPORTS_AVAILABLE:
    print("GraphRAG 依赖未安装，local/global 搜索将不可用。")
else:
    try:
        artifacts = load_artifacts(DATA_DIR)

        llm = ChatOpenAI(
            temperature=0,
            model_name=OPENAI_CHAT_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE
        )

        # 全局搜索组件（与本地解耦，避免本地失败拖垮全局）
        try:
            report_context_builder = CommunityReportContextBuilder(
                community_level=cast(CommunityLevel, 0),
                weight_calculator=CommunityWeightCalculator(),
                artifacts=artifacts,
                token_counter=TiktokenCounter(),
            )

            kp_generator = KeyPointsGenerator(
                llm=llm,
                prompt_builder=KeyPointsGeneratorPromptBuilder(show_references=True, repeat_instructions=True),
                context_builder=report_context_builder,
            )

            kp_aggregator = KeyPointsAggregator(
                llm=llm,
                prompt_builder=KeyPointsAggregatorPromptBuilder(show_references=True, repeat_instructions=True),
                context_builder=KeyPointsContextBuilder(token_counter=TiktokenCounter()),
                output_raw=True,
            )

            global_search_engine = GlobalSearch(
                kp_generator=kp_generator,
                kp_aggregator=kp_aggregator,
                generation_chain_config={"tags": ["kp-generation"]},
                aggregation_chain_config={"tags": ["kp-aggregation"]},
            )
            print("GraphRAG 全局搜索初始化成功。")
        except Exception as e:
            global_search_engine = None
            print(f"GraphRAG 全局搜索初始化失败: {e}")

        # 本地搜索组件（单独失败不影响全局与联网）
        try:
            if EMBED_PROVIDER_BLOCKED:
                raise RuntimeError(
                    "当前 Embedding API 指向 DeepSeek，未提供 OpenAI embeddings 兼容端点；已禁用 local search。"
                )

            entities_vector_store = ChromaVectorStore(
                collection_name="entity-embedding",
                persist_directory=str(VECTOR_STORES_DIR),
                embedding_function=OpenAIEmbeddings(
                    model=OPENAI_EMBED_MODEL,
                    openai_api_base=OPENAI_EMBED_API_BASE,
                    openai_api_key=OPENAI_EMBED_API_KEY
                )
            )

            context_selector = ContextSelector.build_default(
                entities_vector_store=entities_vector_store,
                entities_top_k=10,
                community_level=cast(CommunityLevel, 2),
            )

            context_builder = ContextBuilder.build_default(token_counter=TiktokenCounter())

            retriever = LocalSearchRetriever(
                context_selector=context_selector,
                context_builder=context_builder,
                artifacts=artifacts,
            )

            local_search_engine = LocalSearch(
                prompt_builder=LocalSearchPromptBuilder(show_references=True, repeat_instructions=True),
                llm=llm,
                retriever=retriever,
            )
            local_search_chain = local_search_engine()
            print("GraphRAG 本地搜索初始化成功。")
        except Exception as e:
            local_search_chain = None
            print(f"GraphRAG 本地搜索初始化失败: {e}")

        if global_search_engine is not None or local_search_chain is not None:
            print("GraphRAG 问答系统部分可用。")
        else:
            print("GraphRAG 问答系统初始化失败，将使用离线兜底。")
    except Exception as e:
        print(f"GraphRAG 初始化失败，系统将继续以降级模式运行: {e}")

# ==============================================================================
# 辅助函数
# ==============================================================================

# --- JSON 响应辅助函数 ---
def json_response(data, status_code=200):
    """返回一个正确编码的 JSON 响应。"""
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        status=status_code,
        mimetype='application/json; charset=utf-8'
    )

# --- 数据库连接辅助函数 ---
def get_user_db_connection():
    conn = sqlite3.connect(USER_DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def get_item_db_connection():
    conn = sqlite3.connect(ITEM_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

PROVINCES = [
    '安徽', '北京', '福建', '甘肃', '广东', '广西', '贵州', '海南', '河北', '河南',
    '黑龙江', '湖北', '湖南', '吉林', '江苏', '江西', '辽宁', '内蒙古', '宁夏', '青海',
    '山东', '山西', '陕西', '上海', '四川', '天津', '西藏', '新疆', '云南', '浙江', '江南'
]

DYNASTY_KEYWORDS = [
    ('民国', ['民国', '中华民国']),
    ('清朝', ['清', '宣统', '光绪', '同治', '咸丰', '道光', '嘉庆', '乾隆', '雍正', '康熙', '顺治']),
    ('明朝', ['明', '洪武', '永乐', '宣德', '崇祯']),
    ('元朝', ['元', '至元', '大元']),
    ('宋朝', ['宋', '北宋', '南宋']),
    ('唐朝', ['唐', '开元', '贞观']),
    ('汉朝', ['汉', '五铢', '半两']),
    ('先秦', ['战国', '先秦', '刀币', '布币'])
]

REPUBLIC_CN_NUM = {'元': 1, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}

def parse_cn_republic_year(cn: str):
    if not cn:
        return None
    cn = cn.strip()
    if cn.isdigit():
        return int(cn)
    if cn in REPUBLIC_CN_NUM:
        return REPUBLIC_CN_NUM[cn]
    if '十' in cn:
        left, _, right = cn.partition('十')
        left_v = REPUBLIC_CN_NUM.get(left, 1 if left == '' else 0)
        right_v = REPUBLIC_CN_NUM.get(right, 0)
        if left_v == 0:
            return None
        return left_v * 10 + right_v
    total = 0
    for ch in cn:
        val = REPUBLIC_CN_NUM.get(ch)
        if val is None:
            return None
        total = total * 10 + val
    return total if total > 0 else None

def extract_year(title: str):
    if not title:
        return None
    year_match = re.search(r'(1[0-9]{3}|20[0-2][0-9])年?', title)
    if year_match:
        year = int(year_match.group(1))
        if 1000 <= year <= 2029:
            return year

    republic_match = re.search(r'民国\s*([元一二三四五六七八九十0-9]{1,4})年', title)
    if republic_match:
        republic_year = parse_cn_republic_year(republic_match.group(1))
        if republic_year:
            return 1911 + republic_year
    return None

def extract_dynasty(title: str):
    if not title:
        return ''
    for dynasty, keywords in DYNASTY_KEYWORDS:
        if any(k in title for k in keywords):
            return dynasty
    return ''

def extract_province(title: str):
    if not title:
        return ''
    for province in PROVINCES:
        if province in title:
            return province

    english_alias = {
        'Hubei': '湖北', 'Hupeh': '湖北', 'Hunan': '湖南', 'Jiangnan': '江南',
        'Kiangnan': '江南', 'Yunnan': '云南', 'Szechuan': '四川', 'Sichuan': '四川',
        'Shantung': '山东', 'Shanxi': '山西', 'Shensi': '陕西'
    }
    for alias, province in english_alias.items():
        if alias.lower() in title.lower():
            return province
    return ''

def extract_grade(title: str):
    if not title:
        return ''
    m = re.search(r'\b(PCGS|NGC)\s*([A-Z]{1,4}(?:[-\s]?(?:DETAILS|\d{1,3}))?)', title, re.IGNORECASE)
    if m:
        vendor = m.group(1).upper()
        level = re.sub(r'\s+', ' ', m.group(2).upper().replace('-', ' ')).strip()
        return f'{vendor} {level}'.strip()
    if 'GBCA真品' in title:
        return 'GBCA真品'
    grade_m = re.search(r'\b(MS|AU|XF|VF|F|G|PF|SP|UNC)\s*[- ]?(\d{1,3})?\b', title, re.IGNORECASE)
    if grade_m:
        prefix = grade_m.group(1).upper()
        number = grade_m.group(2)
        return f'{prefix} {number}'.strip() if number else prefix
    return ''

def to_artifact_view(item):
    text_data = json.loads(item['text'])
    title = text_data.get('title', '')
    year = extract_year(title)
    return {
        'pid': item['pid'],
        'title': title,
        'url': item['url'],
        'c0': item['c0'],
        'dynasty': extract_dynasty(title),
        'year': year,
        'province': extract_province(title),
        'grade': extract_grade(title)
    }

# --- 问答系统执行函数 (来自 KQapp.py, 为清晰起见已重命名) ---
def execute_local_search(question: str) -> str:
    """执行本地搜索并流式传输响应。"""
    if local_search_chain is None:
        return "本地搜索暂不可用：请检查 OPENAI_API_KEY 和 GraphRAG 构件文件。"
    try:
        answer = ""
        for chunk in local_search_chain.stream(question, config={"tags": ["local-search"]}):
            answer += str(chunk)
        return answer
    except Exception:
        return "本地搜索暂不可用：embedding 接口未就绪或请求失败。"

def execute_global_search(question: str) -> str:
    """执行全局搜索。"""
    if global_search_engine is None:
        return "全局搜索暂不可用：请检查 OPENAI_API_KEY 和 GraphRAG 构件文件。"
    try:
        result = global_search_engine.invoke(question)
        return str(result.content)
    except Exception:
        return "全局搜索暂不可用：LLM 请求失败或模型配置不兼容。"

def execute_keyword_fallback_payload(question: str):
    """
    当 LLM/RAG 不可用时的兜底问答：
    基于本地 item.db 做关键词检索，返回可阅读摘要和来源。
    """
    q = (question or "").strip()
    if not q:
        return "请输入问题。", []

    conn = None
    try:
        conn = get_item_db_connection()
        rows = conn.execute("SELECT pid, text, url FROM item").fetchall()
    except Exception:
        rows = []
    finally:
        if conn:
            conn.close()

    tokens = extract_query_tokens(q)
    scored_rows = []
    for row in rows:
        try:
            text_data = json.loads(row["text"])
            title = (text_data.get("title") or "").strip()
            desc = (text_data.get("describe") or "").replace("\n", " ").strip()
        except Exception:
            title = ""
            desc = ""

        haystack = f"{title} {desc}".lower()
        if not haystack:
            continue

        score = 0
        if q.lower() in haystack:
            score += 5
        for token in tokens:
            if token in haystack:
                score += 1

        if score > 0:
            scored_rows.append((score, row, title, desc))

    scored_rows.sort(key=lambda x: x[0], reverse=True)
    top_rows = scored_rows[:5]

    if not top_rows:
        return "当前离线知识库中未检索到直接相关条目。请换个关键词，或稍后启用联网/大模型能力后再试。", []

    lines = ["当前为离线检索模式，已为你找到以下相关文物："]
    sources = []
    for i, (_score, row, title, desc) in enumerate(top_rows, 1):
        title = title or f"文物#{row['pid']}"
        short_desc = desc[:120] + ("..." if len(desc) > 120 else "")
        lines.append(f"{i}. {title}（ID: {row['pid']}）{('：' + short_desc) if short_desc else ''}")
        sources.append({
            "type": "artifact",
            "title": title,
            "pid": row["pid"],
            "url": row["url"]
        })

    lines.append("你可以去“首页”或“详情页”查看完整信息。")
    return "\n".join(lines), sources


def execute_keyword_fallback(question: str) -> str:
    answer, _ = execute_keyword_fallback_payload(question)
    return answer


def extract_query_tokens(question: str):
    """
    将用户问题拆分为更易命中的检索 token。
    例如“湖北钱币”会拆出“湖北”“钱币”等，以提升离线兜底召回率。
    """
    q = (question or "").strip()
    if not q:
        return []

    tokens = set([q])
    parts = re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', q)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        tokens.add(part)

        # 中文长词按 2-3 字窗口补充切分，提升“组合词”命中概率
        if re.search(r'[\u4e00-\u9fff]', part) and len(part) >= 3:
            max_n = min(3, len(part))
            for n in range(2, max_n + 1):
                for i in range(0, len(part) - n + 1):
                    tokens.add(part[i:i + n])

    # 省份词作为高价值 token
    for p in PROVINCES:
        if p in q:
            tokens.add(p)

    filtered = []
    for t in tokens:
        t = t.strip().lower()
        if len(t) < 2:
            continue
        filtered.append(t)
    return list(dict.fromkeys(filtered))


def build_question_with_history(question: str, history: Any) -> str:
    """
    将最近若干轮聊天历史拼接到问题中，提升多轮对话的上下文理解能力。
    history 预期是 [{"type":"user|bot","text":"..."}, ...]
    """
    q = (question or "").strip()
    if not q:
        return ""

    if not isinstance(history, list) or len(history) == 0:
        return q

    max_turns = 6
    messages = []
    for item in history[-max_turns:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("type", "")).strip().lower()
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        if role == "user":
            messages.append(f"用户：{text}")
        elif role == "bot":
            messages.append(f"助手：{text}")

    if not messages:
        return q

    history_block = "\n".join(messages)
    return (
        "以下是最近对话上下文（供理解问题语境）：\n"
        f"{history_block}\n\n"
        f"当前用户问题：{q}"
    )

# ==============================================================================
# 认证装饰器
# ==============================================================================
def token_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': '未提供Token!'}), 401

        conn = None
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            conn = get_user_db_connection()
            current_user = conn.execute('SELECT * FROM users WHERE username = ?', (data['username'],)).fetchone()
            if current_user is None:
                return jsonify({'message': '无效的Token!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token已过期!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': '无效的Token!'}), 401
        except Exception as e:
            # 增加一个通用的异常捕获，以便调试
            print(f"Token decorator error: {e}")
            return jsonify({'message': '服务器认证时发生错误'}), 500
        finally:
            if conn:
                conn.close()

        return f(current_user, *args, **kwargs)
    return decorated

# ==============================================================================
# API 端点 / 路由
# ==============================================================================

# --- 用户管理 API (来自 app.py) ---
@app.route('/api/users/register', methods=['POST'])
def register():
    data = request.get_json()
    username, password = data.get('username'), data.get('password')
    user_role = data.get('userRole', 'user')
    if not username or not password:
        return json_response({"message": "用户名和密码是必填项"}, 400)

    conn = get_user_db_connection()
    try:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn.execute("INSERT INTO users (username, password, userRole) VALUES (?, ?, ?)", (username, hashed_password, user_role))
        conn.commit()
    except sqlite3.IntegrityError:
        return json_response({"message": "用户名已存在"}, 409)
    finally:
        conn.close()
    return json_response({"message": "用户注册成功"}, 201)


@app.route('/api/users/login', methods=['POST'])
def login():
    data = request.get_json()
    username, password = data.get('username'), data.get('password')
    conn = get_user_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        payload = {'username': user['username'], 'exp': datetime.now(timezone.utc) + timedelta(hours=24)}
        token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
        return json_response({
            "id": user['id'],
            "message": "登录成功",
            "token": token,
            "username": user['username']
        })
    return json_response({"message": "用户名或密码无效"}, 401)

# --- 文物 API (来自 app.py) ---
@app.route('/api/artifacts/classification', methods=['GET'])
def get_classification():
    try:
        classification_path = os.path.join(BASE_DIR, 'instance', 'classification.json')
        with open(classification_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"message": "分类文件未找到"}), 404

@app.route('/api/artifacts/searchItems', methods=['GET'])
def get_artifacts():
    page = request.args.get('page',1,type =int)
    limit = request.args.get('limit',20,type = int)
    search_query =request.args.get('q',None)
    category_c0 = request.args.get('c0', None)
    dynasty = request.args.get('dynasty', '').strip()
    province = request.args.get('province', '').strip()
    grade = request.args.get('grade', '').strip()
    year_start = request.args.get('year_start', type=int)
    year_end = request.args.get('year_end', type=int)

    query = "SELECT url,pid,text,c0 FROM item"
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

    conn = None
    try:
        conn = get_item_db_connection()
        items = conn.execute(query,tuple(params)).fetchall()
    finally:
        if conn:
            conn.close()

    filtered = []
    for item in items:
        try:
            record = to_artifact_view(item)
        except Exception:
            continue

        if dynasty and record['dynasty'] != dynasty:
            continue
        if province and record['province'] != province:
            continue
        if grade and record['grade'] != grade:
            continue
        if year_start is not None and (record['year'] is None or record['year'] < year_start):
            continue
        if year_end is not None and (record['year'] is None or record['year'] > year_end):
            continue
        filtered.append(record)

    offset = (page - 1) * limit
    paged = filtered[offset: offset + limit]
    return jsonify(paged)

@app.route('/api/artifacts/filters', methods=['GET'])
def get_artifact_filters():
    conn = None
    try:
        conn = get_item_db_connection()
        items = conn.execute("SELECT url,pid,text,c0 FROM item").fetchall()
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



    
@app.route('/api/artifacts/search', methods=['GET'])
def get_artifact_by_id():
    pid = request.args.get('id')
    if not pid:
        return jsonify({"message": "需要提供文物ID"}), 400

    conn = get_item_db_connection()
    item = conn.execute("SELECT * FROM item WHERE pid = ?", (pid,)).fetchone()
    conn.close()

    if not item:
        return jsonify({"message": "未找到文物"}), 404

    text_data = json.loads(item['text'])
    artifact_data = {
        "url": item['url'], "pid": item['pid'], "c0": item['c0'],
        "title": text_data.get('title'), "describe": text_data.get('describe')
    }
    return jsonify(artifact_data)

@app.route('/api/kg/graph', methods=['GET'])
def get_kg_graph():
    """
    从 artifacts 文件构建图谱数据，前端通过该接口获取，避免浏览器直连 Neo4j。
    """
    limit = request.args.get('limit', 300, type=int)
    limit = max(50, min(limit, 1000))

    entities_file = ARTIFACTS_DIR / "entities.parquet"
    relationships_file = ARTIFACTS_DIR / "relationships.parquet"

    if not entities_file.exists() or not relationships_file.exists():
        return jsonify({"message": "图谱数据文件不存在"}), 404

    try:
        entities_df = pd.read_parquet(entities_file)
        relationships_df = pd.read_parquet(relationships_file)

        if relationships_df.empty:
            return jsonify({"nodes": [], "edges": []})

        rel_subset = relationships_df.head(limit)
        related_names = set(rel_subset['source'].tolist()) | set(rel_subset['target'].tolist())

        # entities.parquet 的标题列用于与 relationships 的 source/target 对齐
        entity_name_col = 'title' if 'title' in entities_df.columns else entities_df.columns[0]
        entities_subset = entities_df[entities_df[entity_name_col].isin(related_names)]

        nodes = []
        for _, row in entities_subset.iterrows():
            name = str(row.get(entity_name_col, '')).strip()
            if not name:
                continue
            node_type = str(row.get('type', 'Entity')) if not pd.isna(row.get('type', None)) else "Entity"
            desc = row.get('description', '')
            nodes.append({
                "id": name,
                "label": name,
                "type": node_type,
                "description": "" if pd.isna(desc) else str(desc)
            })

        edges = []
        for _, row in rel_subset.iterrows():
            source = str(row.get('source', '')).strip()
            target = str(row.get('target', '')).strip()
            if not source or not target:
                continue
            desc = row.get('description', '')
            relation_label = "RELATED_TO" if pd.isna(desc) or not str(desc).strip() else str(desc)[:60]
            edges.append({
                "from": source,
                "to": target,
                "label": relation_label
            })

        return jsonify({"nodes": nodes, "edges": edges})
    except Exception as e:
        print(f"加载图谱数据失败: {e}")
        traceback.print_exc()
        return jsonify({"message": "加载图谱失败"}), 500

# --- 用户操作 API (来自 app.py) ---
# 请用这个版本替换 add_favorite 函数
@app.route('/api/user-actions/favorite', methods=['POST'])
@token_required
def add_favorite(current_user):
    pid = request.get_json().get('pid')
    username = current_user['username']
    
    conn = None
    try:
        conn = get_user_db_connection()
        conn.execute("INSERT INTO favorites (username, pid, timestamp) VALUES (?, ?, ?)", (username, pid, int(datetime.now().timestamp())))
        conn.commit()
        return jsonify({"message": "收藏成功"}), 201
    except sqlite3.IntegrityError:
        # 专门处理“重复收藏”的错误，返回一个不同的状态码和信息
        return jsonify({"error": "您已经收藏过该物品"}), 409 # 409 Conflict
    except Exception as e:
        # 处理其他可能的错误
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/user-actions/favorite', methods=['GET'])
@token_required
def get_favorites(current_user):
    username = current_user['username']
    # 这个查询需要跨两个不同的数据库文件进行 JOIN 操作。
    # 一个简单的方法是先从一个库查询，再查另一个，但对于一个健壮的系统，
    # 如果需要执行复杂的 JOIN，可以考虑使用 SQLite 的 ATTACH DATABASE。
    # 目前的实现是先获取收藏夹，再查询文物详情。
    user_conn = get_user_db_connection()
    favorite_pids = user_conn.execute("SELECT pid FROM favorites WHERE username = ?", (username,)).fetchall()
    user_conn.close()
    
    pids = [row['pid'] for row in favorite_pids]
    favorites_details = []
    if pids:
        item_conn = get_item_db_connection()
        # 为 IN 子句使用占位符字符串
        placeholders = ', '.join(['?'] * len(pids))
        items_raw = item_conn.execute(f"SELECT pid, text FROM item WHERE pid IN ({placeholders})", pids).fetchall()
        item_conn.close()
        for item in items_raw:
            favorites_details.append({'pid': item['pid'], 'title': json.loads(item['text']).get('title')})
            
    return jsonify(favorites_details)


# 新增：检查特定物品的收藏状态
@app.route('/api/user-actions/favorite/status', methods=['GET'])
@token_required
def get_favorite_status(current_user):
    pid = request.args.get('pid')
    if not pid:
        return jsonify({"error": "PID is required"}), 400

    username = current_user['username']
    conn = get_user_db_connection()
    item = conn.execute(
        "SELECT pid FROM favorites WHERE username = ? AND pid = ?",
        (username, pid)
    ).fetchone()
    conn.close()

    is_favorited = True if item else False
    return jsonify({"isFavorited": is_favorited})




# --- 【最终正确版】使用 Tavily 的联网搜索 ---

def execute_web_search(question: str) -> str:
    """
    执行一个直接的“搜索-总结”链，取代容易出错的Agent。
    这个方法更稳定、更节省Token，并能处理特定的网络错误。
    """
    print(f"正在执行直接的联网搜索: '{question}'")

    if not WEB_SEARCH_IMPORTS_AVAILABLE:
        return "错误：联网搜索依赖未安装（langchain_community/langchain_openai 等）。"

    if llm is None:
        return "错误：OPENAI_API_KEY 未配置，无法进行联网搜索总结。"

    if not os.getenv("TAVILY_API_KEY"):
        return "错误：Tavily API 密钥未设置。"

    try:
        # 1. 初始化搜索工具
        search = TavilySearchResults(max_results=5) # 可以稍微多获取一些结果

        # 2. 定义我们的“搜索-总结”链
        #    a. 定义一个模板，将搜索结果和原始问题结合起来
        prompt_template = ChatPromptTemplate.from_template(
            "你是一个钱币收藏专家。请根据以下搜索结果，清晰地回答用户的问题。\n"
            "搜索结果:\n---\n{context}\n---\n"
            "用户问题: {question}"
        )
        
        #    b. 使用LCEL（LangChain表达式语言）构建链
        #       - 首先，调用Tavily搜索 (`search.invoke`)
        #       - 然后，将问题和搜索结果传入模板
        #       - 最后，将填充好的模板交给LLM (`llm`) 并解析出字符串结果 (`StrOutputParser`)
        chain = (
            {"context": search, "question": RunnablePassthrough()}
            | prompt_template
            | llm
            | StrOutputParser()
        )
        
        # 3. 执行链
        answer = chain.invoke(question)
        return answer

    except Exception as e:
        # 专门处理 SSL 错误，给出明确的解决方案
        if "SSL" in str(e) or "CERTIFICATE_VERIFY_FAILED" in str(e):
            print(f"!!! 发生SSL网络错误: {e}")
            traceback.print_exc()
            return ("网络连接出现SSL错误。这通常是您本地环境问题。"
                    "请尝试以下步骤：\n"
                    "1. 在您的Conda环境中运行 `pip install --upgrade certifi`\n"
                    "2. 检查您的系统代理或防火墙设置是否拦截了对 api.tavily.com 的访问。")
        
        # 处理其他错误
        print(f"联网搜索过程中发生未知错误: {e}")
        traceback.print_exc()
        return "联网搜索时出错，请查看服务器日志。"


# --- 问答系统 API (这部分完全无需修改) ---
@app.route('/api/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '')
    history = data.get('history', [])
    # 允许的 searchType 包括 'local', 'global', 或 'web'
    search_type = data.get('searchType', 'local')
    question_with_history = build_question_with_history(question, history)

    print(f"收到问题: '{question}', 搜索类型: {search_type}")

    if not question:
        return jsonify({'answer': "请输入问题。"}), 400

    try:
        sources = []
        if search_type == 'local':
            answer = execute_local_search(question_with_history)
            sources = [{"type": "engine", "name": "GraphRAG Local"}]
            if "暂不可用" in answer:
                answer, sources = execute_keyword_fallback_payload(question)
        elif search_type == 'global':
            answer = execute_global_search(question_with_history)
            sources = [{"type": "engine", "name": "GraphRAG Global"}]
            if "暂不可用" in answer:
                answer, sources = execute_keyword_fallback_payload(question)
        elif search_type == 'web': # <-- 这个分支现在会调用我们修改后的函数
            answer = execute_web_search(question_with_history) # <-- 调用新的 Tavily 搜索函数
            sources = [{"type": "engine", "name": "Web Search Summary"}]
            if "错误：" in answer:
                answer, sources = execute_keyword_fallback_payload(question)
        else:
            answer = "未知的搜索类型。请使用 'local', 'global', 或 'web'。"
            return jsonify({'answer': answer}), 400 # 返回 400 错误码

    except Exception as e:
        print(f"处理问题 '{question}' 时发生严重错误: {e}")
        traceback.print_exc()
        return jsonify({'answer': "处理您的问题时发生内部错误，请查看服务器日志。"}), 500

    return jsonify({'answer': answer, 'sources': sources, 'searchType': search_type})


@app.route('/api/ask/capabilities', methods=['GET'])
def ask_capabilities():
    tavily_api_key = os.getenv("TAVILY_API_KEY")

    local_available = local_search_chain is not None and not EMBED_PROVIDER_BLOCKED
    global_available = global_search_engine is not None
    web_available = WEB_SEARCH_IMPORTS_AVAILABLE and llm is not None and bool(tavily_api_key)

    return jsonify({
        "local": {
            "available": local_available,
            "reason": "" if local_available else (
                "当前 Embedding Provider 不支持 local search（DeepSeek 无 embeddings 兼容端点），已自动降级。"
                if EMBED_PROVIDER_BLOCKED else
                "local_search_chain 未初始化，将使用离线关键词兜底。"
            )
        },
        "global": {
            "available": global_available,
            "reason": "" if global_available else "global_search_engine 未初始化，将使用离线关键词兜底。"
        },
        "web": {
            "available": web_available,
            "reason": "" if web_available else "联网搜索依赖或密钥不完整（检查 OPENAI_API_KEY / TAVILY_API_KEY）。"
        }
    })


@app.route('/api/valuation', methods=['POST'])
def get_valuation():
    """
    接收钱币名称和品相，结合全局搜索（知识库）和联网搜索（市场行情）
    生成一个综合估值报告。
    """
    data = request.get_json()
    coin_name = data.get('coinName')
    coin_grade = data.get('coinGrade')

    if not coin_name or not coin_grade:
        return jsonify({'error': '钱币名称和品相是必填项。'}), 400

    print(f"开始为 '{coin_name}' (品相: {coin_grade}) 进行估值...")

    try:
        # --- 全局搜索的Prompt不变 ---
        global_prompt = (
            f"根据你的知识库，请提供关于 “{coin_name}” 的详细信息，侧重于其历史背景、设计特点、主要版别和收藏要点。"
            f"请将分析聚焦在品相等级 “{coin_grade}” 附近，但不要提供实时市场价格或成交记录。"
        )

        # --- 【重点】修改后的联网搜索Prompt ---
        web_prompt = (
            f"请为我查找关于“{coin_name} {coin_grade}”的市场信息。"
            f"搜索重点是 PCGS, NGC、首都公博、Stack's Bowers、GBCA、中国钱币、中国钱币网等专业网站。"
            f"你需要总结出两点：1. 评级总数（现存量）。2. 近期拍卖成交价。"
            f"直接提供搜索到的核心数据和来源。"
        )

        # --- 3. 并行或串行执行搜索 (这里为了简单使用串行) ---
        print("执行全局搜索...")
        global_answer = execute_global_search(global_prompt)

        print("执行联网搜索...")
        web_answer = execute_web_search(web_prompt)

        # --- 4. 组合结果为 Markdown 格式 ---
        combined_valuation = f"""
### 知识库信息 (Global Search)

{global_answer}

---

### 市场行情参考 (Web Search)

{web_answer}
"""
        return jsonify({'valuation': combined_valuation.strip()})

    except Exception as e:
        print(f"估值过程中发生错误: {e}")
        traceback.print_exc()
        return jsonify({'error': '在生成估值报告时发生内部错误，请查看服务器日志。'}), 500





@app.route('/api/chat/history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    username = current_user['username']
    conn =None

    try:
        conn = get_user_db_connection()

        messages_raw = conn.execute(
            "SELECT message_type, content FROM chat_history WHERE username = ? ORDER BY timestamp ASC",
            (username,)
        ).fetchall()

        history = [{"type": row["message_type"], "text":row["content"]} for row in messages_raw]
        return jsonify(history)

    except Exception as e:
        print(f"获取聊天记录时出错: {e}")
        return jsonify({"error": "无法获取聊天记录"}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/chat/history', methods=['POST'])
@token_required
def save_chat_message(current_user):
    data = request.get_json()
    message_type = data.get('type')
    content = data.get('text')
    username = current_user['username']

    if not message_type or not content:
        return jsonify({"error": "消息类型和内容不能为空"}), 400
    
    conn = None
    try:
        conn = get_user_db_connection()
        conn.execute(
            " INSERT INTO chat_history (username,message_type,content,timestamp) VALUES (?,?,?,?)",
            (username,message_type,content,int(datetime.now().timestamp()))
        )
        conn.commit()
        return jsonify({"message": "消息保存成功"}), 201
        
    except Exception as e:
        print(f"保存聊天消息时出错: {e}")
        return jsonify({"error": "无法保存消息"}), 500
    finally:
        if conn:
            conn.close()

# ==============================================================================
# 鉴别
# ==============================================================================


def detect_yolo(img, confidence_threshold=0.2):
    """
    使用两个YOLO模型检测图像，并返回最高置信度的检测框和类别。
    参数:
        img (numpy.ndarray): OpenCV格式的图像 (BGR)。
    返回:
        (str, tuple, numpy.ndarray): (预测类别名, 裁剪框坐标, 裁剪后的图像区域)
    """
    # Model1推理
    results1 = yolo_model1(img)
    # Model2推理
    results2 = yolo_model2(img)
    
    best_box1, best_confidence1, best_class_name1 = None, 0, None
    best_box2, best_confidence2, best_class_name2 = None, 0, None

    # 查找Model1的最高置信度检测框
    if results1[0].boxes:
        for box in results1[0].boxes:
            confidence = box.conf.item()
            if confidence > best_confidence1 and confidence > confidence_threshold:
                best_confidence1 = confidence
                best_class_name1 = yolo_model1.names[int(box.cls.item())]
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                best_box1 = (int(x1), int(y1), int(x2), int(y2))

    # 查找Model2的最高置信度检测框
    if results2[0].boxes:
        for box in results2[0].boxes:
            confidence = box.conf.item()
            if confidence > best_confidence2 and confidence > confidence_threshold:
                best_confidence2 = confidence
                best_class_name2 = yolo_model2.names[int(box.cls.item())]
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                best_box2 = (int(x1), int(y1), int(x2), int(y2))

    # 比较两个模型的最高置信度，选择更好的结果
    if best_confidence1 > best_confidence2:
        best_box = best_box1
        best_class_name = best_class_name1
    else:
        best_box = best_box2
        best_class_name = best_class_name2
    
    # 裁剪图像
    cropped_image = None
    if best_box:
        x1, y1, x2, y2 = best_box
        cropped_image = img[y1:y2, x1:x2].copy()
        
    return best_class_name, best_box, cropped_image

def segment_circle_from_image(image, box):
    """
    根据给定的框，从图像中分割出圆形区域。
    参数:
        image (numpy.ndarray): 已经经过YOLO裁剪的图像。
        box (tuple): YOLO检测到的原始框坐标 (x_min, y_min, x_max, y_max)。
    返回:
        numpy.ndarray: 分割并缩放为256x256的圆形图像。
    """
    if image is None or box is None:
        return None

    # 使用高斯滤波去噪
    blurred = cv2.GaussianBlur(image, (9, 9), 2, 2)
    
    # 创建一个与图像大小相同的黑色背景掩码
    mask = np.zeros_like(blurred)
    
    # 计算正方形的中心点和半径
    x_min, y_min, x_max, y_max = 0, 0, image.shape[1], image.shape[0] # 在裁剪图内部计算
    center_x = (x_min + x_max) // 2
    center_y = (y_min + y_max) // 2
    radius = min(x_max - x_min, y_max - y_min) // 2
    
    # 在掩码上绘制白色圆形
    cv2.circle(mask, (center_x, center_y), radius, (255, 255, 255), -1)
    
    # 使用掩码将圆形外的部分置为黑色，并缩放
    segmented_image = cv2.bitwise_and(blurred, mask)
    
    return segmented_image

def preprocess_for_onnx(pil_image):
    """
    对图像进行预处理，以适配 ONNX 模型输入。
    输入支持 PIL.Image 或 numpy 数组（RGB）。
    """
    if isinstance(pil_image, Image.Image):
        img = np.array(pil_image.convert("RGB"), dtype=np.float32)
    else:
        img = np.asarray(pil_image, dtype=np.float32)
        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        if img.shape[-1] == 4:
            img = img[..., :3]

    img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
    img = img / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img = (img - mean) / std
    img = np.transpose(img, (2, 0, 1))
    return np.expand_dims(img, axis=0).astype(np.float32)


def run_onnx_pair_inference(image1_np, image2_np):
    """
    对一对图像执行 ONNX 推理，返回 1D 概率向量。
    输入为 OpenCV 图像 (BGR)。
    """
    image1_for_onnx = cv2.resize(image1_np, (224, 224))
    image2_for_onnx = cv2.resize(image2_np, (224, 224))

    image1_rgb = cv2.cvtColor(image1_for_onnx, cv2.COLOR_BGR2RGB)
    image2_rgb = cv2.cvtColor(image2_for_onnx, cv2.COLOR_BGR2RGB)
    input1_tensor = preprocess_for_onnx(image1_rgb)
    input2_tensor = preprocess_for_onnx(image2_rgb)

    # 优先按名称绑定输入，避免依赖输入列表顺序
    input_names = onnx_input_names or ['input1', 'input2']
    if 'input1' in input_names and 'input2' in input_names:
        ort_inputs = {'input1': input1_tensor, 'input2': input2_tensor}
    else:
        ort_inputs = {input_names[0]: input1_tensor, input_names[1]: input2_tensor}

    output_name = onnx_output_names[0] if onnx_output_names else 'output'
    ort_outputs = onnx_session.run([output_name], ort_inputs)
    logits = ort_outputs[0]
    return softmax(logits, axis=1).flatten()

# ==============================================================================
# 全新重写的 predict API 端点
# ==============================================================================
# @app.route('/predict', methods=['POST'])
# def predict():
#     if 'image1' not in request.files or 'image2' not in request.files:
#         return jsonify({'error': '缺少图像文件 (image1 或 image2)'}), 400
#
#     file1, file2 = request.files['image1'], request.files['image2']
#     if file1.filename == '' or file2.filename == '':
#         return jsonify({'error': '没有选择文件'}), 400
#
#     try:
#         # --- 1. 读取原始高清图像 ---
#         image1_data = cv2.imdecode(np.frombuffer(file1.read(), np.uint8), cv2.IMREAD_COLOR)
#         image2_data = cv2.imdecode(np.frombuffer(file2.read(), np.uint8), cv2.IMREAD_COLOR)
#
#         # --- 2. 对第一张图进行分步预处理（不缩放） ---
#         final_image1_for_display = image1_data  # 初始化用于显示的高清图片
#         print("第一张图：开始预处理...")
#         try:
#             _, box1, cropped1 = detect_yolo(image1_data)
#             if cropped1 is not None:
#                 print(" -> 第一张图：YOLO裁剪成功。")
#                 final_image1_for_display = cropped1
#
#                 segmented1 = segment_circle_from_image(cropped1, box1)
#                 if segmented1 is not None:
#                     print(" -> 第一张图：圆形分割成功。")
#                     final_image1_for_display = segmented1 # 这是处理完但未缩放的高清图
#                 else:
#                     print(" -> 第一张图：圆形分割失败，将使用裁剪后的图像。")
#             else:
#                 print(" -> 第一张图：YOLO裁剪失败，将使用原图。")
#         except Exception as e:
#             print(f"第一张图预处理时发生未知异常: {e}，将使用上一步成功的图像。")
#
#         # --- 3. 对第二张图进行分步预处理（不缩放） ---
#         final_image2_for_display = image2_data # 初始化用于显示的高清图片
#         print("第二张图：开始预处理...")
#         try:
#             _, box2, cropped2 = detect_yolo(image2_data)
#             if cropped2 is not None:
#                 print(" -> 第二张图：YOLO裁剪成功。")
#                 final_image2_for_display = cropped2
#
#                 segmented2 = segment_circle_from_image(cropped2, box2)
#                 if segmented2 is not None:
#                     print(" -> 第二张图：圆形分割成功。")
#                     final_image2_for_display = segmented2
#                 else:
#                     print(" -> 第二张图：圆形分割失败，将使用裁剪后的图像。")
#             else:
#                 print(" -> 第二张图：YOLO裁剪失败，将使用原图。")
#         except Exception as e:
#             print(f"第二张图预处理时发生未知异常: {e}，将使用上一步成功的图像。")
#
#         # --- 4. 准备ONNX模型输入（创建缩小的副本） ---
#         # 【关键改动】在这里创建 224x224 的小图专门用于推理
#         image1_for_onnx = cv2.resize(final_image1_for_display, (224, 224))
#         image2_for_onnx = cv2.resize(final_image2_for_display, (224, 224))
#
#         pil_image1 = Image.fromarray(cv2.cvtColor(image1_for_onnx, cv2.COLOR_BGR2RGB))
#         pil_image2 = Image.fromarray(cv2.cvtColor(image2_for_onnx, cv2.COLOR_BGR2RGB))
#
#         # 此处的预处理不再需要Resize
#         input1_tensor = preprocess_for_onnx(pil_image1)
#         input2_tensor = preprocess_for_onnx(pil_image2)
#
#         # --- 5. 执行ONNX推理 ---
#         ort_inputs = {'input1': input1_tensor, 'input2': input2_tensor}
#         ort_outputs = onnx_session.run(['output'], ort_inputs)
#
#         # --- 6. 处理推理结果 ---
#         predictions = softmax(ort_outputs[0], axis=1)
#         predicted_class_index = int(np.argmax(predictions))
#         confidence = float(predictions[0][predicted_class_index])
#
#         # --- 7. 将用于显示的“高清图”编码后返回给前端 ---
#         base64_image1 = encode_image_to_base64(final_image1_for_display)
#         base64_image2 = encode_image_to_base64(final_image2_for_display)
#
#         return jsonify({
#             'predictions': [{'class': predicted_class_index, 'confidence': confidence}],
#             'processedImage1': f"data:image/jpeg;base64,{base64_image1}",
#             'processedImage2': f"data:image/jpeg;base64,{base64_image2}"
#         })
#
#     except Exception as e:
#         print("!!! 在/predict接口中发生严重错误 !!!")
#         traceback.print_exc()
#         return jsonify({'error': f'服务器处理图像时发生内部错误: {str(e)}'}), 500
@app.route('/api/predict/capabilities', methods=['GET'])
def predict_capabilities():
    late_ok, late_err = ensure_onnx_session_ready()
    onnx_spec = importlib.util.find_spec("onnxruntime")
    yolo_spec = importlib.util.find_spec("ultralytics")
    return jsonify({
        "onnx_ready": onnx_session is not None and late_ok,
        "yolo1_ready": yolo_model1 is not None,
        "yolo2_ready": yolo_model2 is not None,
        "onnx_inputs": onnx_input_names,
        "onnx_outputs": onnx_output_names,
        "errors": predict_model_errors,
        "late_init_error": late_err,
        "ready": onnx_session is not None and late_ok,
        "runtime": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "onnxruntime_found": onnx_spec is not None,
            "ultralytics_found": yolo_spec is not None
        }
    })


def run_optional_yolo_pipeline(image_data):
    """
    使用 YOLO + 圆形分割预处理图像。
    若 YOLO 不可用或失败，回退到原图。
    """
    final_image = image_data

    if image_data is None:
        return None

    if yolo_model1 is None or yolo_model2 is None:
        return final_image

    try:
        _, box, cropped = detect_yolo(image_data)
        if cropped is not None:
            final_image = cropped
            segmented = segment_circle_from_image(cropped, box)
            if segmented is not None:
                final_image = segmented
    except Exception as e:
        print(f"YOLO 预处理失败，回退原图: {e}")

    return final_image


@app.route('/predict', methods=['POST'])
def predict():
    late_ok, late_err = ensure_onnx_session_ready()
    if onnx_session is None or not late_ok:
        return jsonify({
            'error': '推理模型未就绪，请检查 backend/best_model.onnx 与 onnxruntime 环境。',
            'details': predict_model_errors,
            'late_init_error': late_err
        }), 503

    if 'image1' not in request.files or 'image2' not in request.files:
        return jsonify({'error': '缺少图像文件 (image1 或 image2)'}), 400

    file1, file2 = request.files['image1'], request.files['image2']
    if file1.filename == '' or file2.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    try:
        image1_data = cv2.imdecode(np.frombuffer(file1.read(), np.uint8), cv2.IMREAD_COLOR)
        image2_data = cv2.imdecode(np.frombuffer(file2.read(), np.uint8), cv2.IMREAD_COLOR)
        if image1_data is None or image2_data is None:
            return jsonify({'error': '上传的图片无法解析，请更换清晰图片后重试。'}), 400

        # 预处理：优先走 YOLO 管线，失败则自动回退原图
        processed1 = run_optional_yolo_pipeline(image1_data)
        processed2 = run_optional_yolo_pipeline(image2_data)

        # 为提升实战准确率，尝试多候选：
        # 1) 处理后图像
        # 2) 原图
        # 每组都尝试正常顺序与交换顺序，选择 top1 置信度最高的一组。
        candidate_pairs = [
            ('processed', 'normal', processed1, processed2),
            ('processed', 'swapped', processed2, processed1),
            ('raw', 'normal', image1_data, image2_data),
            ('raw', 'swapped', image2_data, image1_data),
        ]

        best = None
        for pipeline_name, order_name, img_a, img_b in candidate_pairs:
            probs = run_onnx_pair_inference(img_a, img_b)
            top1_idx = int(np.argmax(probs))
            top1_conf = float(probs[top1_idx])
            if best is None or top1_conf > best['top1_confidence']:
                best = {
                    'pipeline': pipeline_name,
                    'order': order_name,
                    'probs': probs,
                    'top1_confidence': top1_conf
                }

        predictions = best['probs']
        top_k = np.argsort(predictions)[::-1][:3]
        result_predictions = [
            {'class': int(i), 'confidence': float(predictions[i])}
            for i in top_k
        ]

        # 展示图与最终入模策略一致，方便排查“识别错因”
        if best['pipeline'] == 'processed':
            display1, display2 = processed1, processed2
        else:
            display1, display2 = image1_data, image2_data

        if best['order'] == 'swapped':
            display1, display2 = display2, display1

        base64_image1 = encode_image_to_base64(display1)
        base64_image2 = encode_image_to_base64(display2)

        return jsonify({
            'predictions': result_predictions,
            'processedImage1': f"data:image/jpeg;base64,{base64_image1}",
            'processedImage2': f"data:image/jpeg;base64,{base64_image2}",
            'selectedPipeline': best['pipeline'],
            'selectedOrder': best['order']
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'服务器处理图像时发生错误: {str(e)}'}), 500


def encode_image_to_base64(image_np):
    """ 将OpenCV图像(numpy array)编码为Base64字符串 """
    # 将图像编码为JPEG格式的字节流
    _, buffer = cv2.imencode('.jpg', image_np)
    # 将字节流用Base64编码，并转换为utf-8字符串
    return base64.b64encode(buffer).decode('utf-8')



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
