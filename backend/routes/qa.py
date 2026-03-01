# ==============================================================================
# Q&A问答路由
# ==============================================================================
import os
import traceback
from flask import Blueprint, request, jsonify
from services.rag_service import (
    execute_local_search, execute_global_search, execute_keyword_fallback_payload,
    execute_web_search, build_question_with_history
)
from config import WEB_SEARCH_IMPORTS_AVAILABLE, EMBED_PROVIDER_BLOCKED

qa_bp = Blueprint('qa', __name__)

@qa_bp.route('/api/ask', methods=['POST'])
def ask():
    """问答接口"""
    from services import local_search_chain, global_search_engine, llm

    data = request.get_json()
    question = data.get('question', '')
    history = data.get('history', [])
    search_type = data.get('searchType', 'local')
    question_with_history = build_question_with_history(question, history)

    print(f"收到问题: '{question}', 搜索类型: {search_type}")

    if not question:
        return jsonify({'answer': "请输入问题。"}), 400

    try:
        sources = []
        if search_type == 'local':
            answer = execute_local_search(question_with_history, local_search_chain)
            sources = [{"type": "engine", "name": "GraphRAG Local"}]
            if "暂不可用" in answer:
                answer, sources = execute_keyword_fallback_payload(question)
        elif search_type == 'global':
            answer = execute_global_search(question_with_history, global_search_engine)
            sources = [{"type": "engine", "name": "GraphRAG Global"}]
            if "暂不可用" in answer:
                answer, sources = execute_keyword_fallback_payload(question)
        elif search_type == 'web':
            print(f"开始执行联网搜索: {question_with_history}")
            answer = execute_web_search(question_with_history)
            print(f"联网搜索结果: {answer}")
            sources = [{"type": "engine", "name": "Web Search Summary"}]
            # 暂时禁用自动回退，以便查看完整的错误信息
            # if "错误：" in answer or "失败" in answer:
            #     answer, sources = execute_keyword_fallback_payload(question)
        else:
            answer = "未知的搜索类型。请使用 'local', 'global', 或 'web'。"
            return jsonify({'answer': answer}), 400

    except Exception as e:
        print(f"处理问题 '{question}' 时发生严重错误: {e}")
        traceback.print_exc()
        return jsonify({'answer': "处理您的问题时发生内部错误，请查看服务器日志。"}), 500

    return jsonify({'answer': answer, 'sources': sources, 'searchType': search_type})

@qa_bp.route('/api/ask/capabilities', methods=['GET'])
def ask_capabilities():
    """获取问答系统能力信息"""
    from services import local_search_chain, global_search_engine, llm

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