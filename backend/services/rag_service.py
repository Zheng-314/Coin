# ==============================================================================
# RAG问答服务
# ==============================================================================
import json
import logging
import base64
import os
from utils.database import get_item_db_connection
from services import llm as global_llm

logger = logging.getLogger('services.rag')


def analyze_image_with_qwen_vl(image_files, question=""):
    """
    用Qwen-VL视觉大模型直接看图分析，返回图片描述

    Args:
        image_files: 图片文件列表
        question: 用户问题

    Returns:
        分析结果文本，失败返回None
    """
    api_key = os.getenv('QWEN_API_KEY')
    api_base = os.getenv('QWEN_API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    model = os.getenv('QWEN_VL_MODEL', 'qwen-vl-max')

    if not api_key:
        logger.warning("QWEN_API_KEY未配置，跳过视觉分析")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=api_base)

        # 构建多模态消息
        content = []
        for f in image_files:
            img_data = f.read()
            img_b64 = base64.b64encode(img_data).decode()
            # 根据文件名判断格式
            fmt = 'jpeg'
            if f.filename and f.filename.lower().endswith('.png'):
                fmt = 'png'
            elif f.filename and f.filename.lower().endswith('.webp'):
                fmt = 'webp'
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{fmt};base64,{img_b64}"}
            })

        # 添加文字提示
        prompt = (
            "你是一个古钱币鉴定专家。请仔细观察这张图片，回答以下问题：\n"
            "1. 这是不是一枚钱币？如果不是，请说明图片内容。\n"
            "2. 如果是钱币，请识别：朝代、铸造省份、币种、面值、版别\n"
            "3. 描述钱币的品相特征（磨损、包浆、文字清晰度等）\n"
            "4. 如果能看到评级信息（PCGS、NGC等），请记录\n"
        )
        if question:
            prompt += f"\n用户具体问题：{question}"

        content.append({"type": "text", "text": prompt})

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            max_tokens=1000
        )

        result = resp.choices[0].message.content
        logger.info(f"Qwen-VL分析结果: {result[:200]}...")
        return result

    except Exception as e:
        logger.error(f"Qwen-VL调用失败: {e}", exc_info=True)
        return None

def execute_local_search(question: str, local_search_chain) -> str:
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

def execute_global_search(question: str, global_search_engine) -> str:
    """执行全局搜索。"""
    if global_search_engine is None:
        return "全局搜索暂不可用：请检查 OPENAI_API_KEY 和 GraphRAG 构件文件。"
    try:
        result = global_search_engine.invoke(question)
        return str(result.content)
    except Exception as e:
        logger.error(f"全局搜索执行失败: {str(e)}", exc_info=True)
        return f"全局搜索暂不可用：{str(e)}"

def execute_keyword_fallback_payload(question: str):
    """
    当 GraphRAG 不可用时的兜底问答：
    基于本地 item.db 做关键词检索，再用 LLM 合成回答。
    """
    q = (question or "").strip()
    if not q:
        return "请输入问题。", []

    tokens = extract_query_tokens(q)
    if not tokens:
        return "请输入有效问题。", []

    conn = None
    try:
        conn = get_item_db_connection()
        conditions = " OR ".join(["text LIKE ?" for _ in tokens[:5]])
        params = [f"%{t}%" for t in tokens[:5]]
        rows = conn.execute(
            f"SELECT pid, text, url FROM item WHERE {conditions} LIMIT 20",
            params
        ).fetchall()
    except Exception:
        rows = []
    finally:
        if conn:
            conn.close()

    if not rows:
        # 数据库没搜到，用LLM直接回答
        if global_llm is not None:
            try:
                from langchain_core.prompts import ChatPromptTemplate
                prompt = ChatPromptTemplate.from_template(
                    "你是一个古钱币知识问答助手。请直接简洁地回答用户的问题，不要问候、寒暄或说\"你好\"。\n"
                    "如果问题与古钱币无关，也可以正常回答，但可以适当引导用户提问钱币相关问题。\n\n"
                    "用户问题：{question}\n\n"
                    "直接回答："
                )
                response = global_llm.invoke(prompt.format(question=q))
                return response.content, [{"type": "engine", "name": "LLM"}]
            except Exception as e:
                logger.error(f"LLM直接回答失败: {e}")
        return "当前离线知识库中未检索到直接相关条目。请换个关键词，或稍后启用联网/大模型能力后再试。", []

    # 按命中token数量排序
    scored_rows = []
    for row in rows:
        try:
            text_data = json.loads(row["text"])
            title = (text_data.get("title") or "").strip()
            desc = (text_data.get("describe") or "").replace("\n", " ").strip()
        except Exception:
            title, desc = "", ""
        haystack = f"{title} {desc}".lower()
        score = sum(1 for t in tokens if t in haystack)
        if q.lower() in haystack:
            score += 5
        scored_rows.append((score, row, title, desc))

    scored_rows.sort(key=lambda x: x[0], reverse=True)
    top_rows = scored_rows[:5]

    # 构建来源列表
    sources = []
    context_parts = []
    for i, (_score, row, title, desc) in enumerate(top_rows, 1):
        title = title or f"文物#{row['pid']}"
        short_desc = desc[:300] + ("..." if len(desc) > 300 else "")
        context_parts.append(f"{i}. {title}：{short_desc}")
        sources.append({
            "type": "artifact",
            "title": title,
            "pid": row["pid"],
            "url": row["url"]
        })

    context_text = "\n".join(context_parts)

    # 用 LLM 合成回答
    if global_llm is not None:
        try:
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_template(
                "你是一个古钱币知识问答助手。根据以下检索到的文物信息，直接回答用户的问题，不要问候或寒暄。\n"
                "如果检索到的信息不足以回答问题，请基于你的知识补充回答，但要明确区分检索结果和补充知识。\n"
                "回答要准确、简洁、有条理。\n\n"
                "检索来源：\n{context}\n\n"
                "用户问题：{question}\n\n"
                "直接回答："
            )
            response = global_llm.invoke(prompt.format(context=context_text, question=q))
            answer = response.content
            return answer, sources
        except Exception as e:
            logger.error(f"LLM合成回答失败，降级为列表模式: {e}")
            # 降级为列表模式
            pass

    # LLM不可用时，返回列表
    lines = ["当前为离线检索模式，已为你找到以下相关文物："]
    for i, (_score, row, title, desc) in enumerate(top_rows, 1):
        title = title or f"文物#{row['pid']}"
        short_desc = desc[:120] + ("..." if len(desc) > 120 else "")
        lines.append(f"{i}. {title}（ID: {row['pid']}）{('：' + short_desc) if short_desc else ''}")
    lines.append('你可以去"首页"或"详情页"查看完整信息。')
    return "\n".join(lines), sources

def execute_keyword_fallback(question: str) -> str:
    answer, _ = execute_keyword_fallback_payload(question)
    return answer

def extract_query_tokens(question: str):
    """
    将用户问题拆分为更易命中的检索 token。
    例如"湖北钱币"会拆出"湖北""钱币"等，以提升离线兜底召回率。
    """
    import re
    q = (question or "").strip()
    if not q:
        return []

    # 移除标点符号
    q = re.sub(r'[^\w\u4e00-\u9fff]', ' ', q)

    # 按空格分词
    tokens = q.split()

    # 对于中文，尝试按2字切分
    chinese_tokens = []
    for token in tokens:
        if re.match(r'[\u4e00-\u9fff]+', token):
            # 对于纯中文，尝试按2字切分
            for i in range(len(token) - 1):
                chinese_tokens.append(token[i:i+2])
            # 添加3字切分（如果够长）
            if len(token) >= 3:
                for i in range(len(token) - 2):
                    chinese_tokens.append(token[i:i+3])

    tokens.extend(chinese_tokens)
    return list(set(tokens))  # 去重

def execute_web_search(question: str):
    """执行联网搜索（如果可用）"""
    from config import WEB_SEARCH_IMPORTS_AVAILABLE, OPENAI_API_KEY
    from services import llm as global_llm

    if not WEB_SEARCH_IMPORTS_AVAILABLE:
        return "联网搜索功能未启用。"
    if not OPENAI_API_KEY:
        return "未配置 OPENAI_API_KEY，无法使用联网搜索。"

    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        from langchain_core.prompts import ChatPromptTemplate

        search = TavilySearchResults(max_results=3)
        search_results = search.run(question)

        prompt = ChatPromptTemplate.from_template(
            "基于以下搜索结果回答问题，不要编造：\n\n搜索结果：\n{search_results}\n\n问题：{question}\n\n回答："
        )
        _llm = global_llm
        if _llm is None:
            from config import OPENAI_API_BASE, OPENAI_CHAT_MODEL
            from langchain_openai import ChatOpenAI
            _llm = ChatOpenAI(temperature=0, model_name=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

        response = _llm.invoke(prompt.format(search_results=search_results, question=question))
        return response.content
    except Exception as e:
        logger.error(f"联网搜索失败: {str(e)}", exc_info=True)
        return f"联网搜索失败: {str(e)}"

def build_question_with_history(question: str, history):
    """
    将当前问题与历史对话合并，构建完整上下文
    """
    if not history or not isinstance(history, list) or len(history) == 0:
        return question

    # 获取最近的3轮对话
    recent_history = history[-6:] if len(history) >= 6 else history

    # 构建历史对话字符串
    history_text = []
    for i in range(0, len(recent_history), 2):
        if i + 1 < len(recent_history):
            user_msg = recent_history[i]
            assistant_msg = recent_history[i + 1]
            
            # 提取文本内容，处理可能的对象格式
            user_text = user_msg.get('text', '') if isinstance(user_msg, dict) else str(user_msg)
            assistant_text = assistant_msg.get('text', '') if isinstance(assistant_msg, dict) else str(assistant_msg)
            
            history_text.append(f"用户: {user_text}")
            history_text.append(f"助手: {assistant_text}")

    # 如果历史对话很长，只保留最近的
    if len(history_text) > 1000:
        history_text = history_text[-10:]

    # 合并历史和当前问题
    if history_text:
        full_question = "\n".join(history_text) + f"\n用户: {question}\n助手: "
    else:
        full_question = f"用户: {question}\n助手: "

    return full_question