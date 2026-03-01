# ==============================================================================
# RAG问答服务
# ==============================================================================
import json
from utils.database import get_item_db_connection

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
        print(f"全局搜索执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"全局搜索暂不可用：{str(e)}"

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
        # 添加 LIMIT 限制，提高性能
        rows = conn.execute("SELECT pid, text, url FROM item LIMIT 1000").fetchall()
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
    """
    执行联网搜索（如果可用）
    """
    from config import WEB_SEARCH_IMPORTS_AVAILABLE, OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_CHAT_MODEL
    from langchain_community.tools.tavily_search import TavilySearchResults
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    from langchain_openai import ChatOpenAI

    if not WEB_SEARCH_IMPORTS_AVAILABLE:
        return "联网搜索功能未启用。"

    if not OPENAI_API_KEY:
        return "未配置 OPENAI_API_KEY，无法使用联网搜索。"

    try:
        # 使用环境变量中的配置
        llm = ChatOpenAI(
            temperature=0,
            model_name=OPENAI_CHAT_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE
        )

        # 使用LangChain的TavilySearchResults工具
        search = TavilySearchResults(max_results=3)

        # 执行搜索
        search_results = search.run(question)
        print(f"搜索结果: {search_results}")

        # 构建提示
        prompt = ChatPromptTemplate.from_template(
            """基于以下搜索结果回答问题，不要编造：

搜索结果：
{search_results}

问题：{question}

回答："""
        )

        # 直接使用LLM处理搜索结果
        response = llm.invoke(
            prompt.format(
                search_results=search_results,
                question=question
            )
        )

        return response.content
    except Exception as e:
        print(f"联网搜索失败: {str(e)}")
        import traceback
        traceback.print_exc()
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