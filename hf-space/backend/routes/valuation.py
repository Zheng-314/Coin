# ==============================================================================
# 钱币估值路由
# ==============================================================================
import logging
from flask import Blueprint, request, jsonify
from services import global_search_engine

logger = logging.getLogger('routes.valuation')

valuation_bp = Blueprint('valuation', __name__)

@valuation_bp.route('/api/valuation', methods=['POST'])
def get_valuation():
    """
    接收钱币名称和品相，结合全局搜索（知识库）和联网搜索（市场行情）
    生成一个综合估值报告。
    """
    from services.rag_service import execute_global_search, execute_web_search, build_question_with_history

    data = request.get_json()
    coin_name = data.get('coinName')
    coin_grade = data.get('coinGrade')

    if not coin_name or not coin_grade:
        return jsonify({'error': '钱币名称和品相是必填项。'}), 400

    logger.info(f"开始为 '{coin_name}' (品相: {coin_grade}) 进行估值...")

    try:
        # 全局搜索 - 获取历史背景和设计特点
        global_prompt = (
            f'根据你的知识库，请提供关于 "{coin_name}" 的详细信息，侧重于其历史背景、设计特点、主要版别和收藏要点。'
            f'请将分析聚焦在品相等级 "{coin_grade}" 附近，但不要提供实时市场价格或成交记录。'
        )

        # 联网搜索 - 获取市场信息
        web_prompt = (
            f'请为我查找关于"{coin_name} {coin_grade}"的市场信息。'
            f'搜索重点是 PCGS, NGC、首都公博、Stack\'s Bowers、GBCA、中国钱币、中国钱币网等专业网站。'
            f'你需要总结出两点：1. 评级总数（现存量）。2. 近期拍卖成交价。'
            f'直接提供搜索到的核心数据和来源。'
        )

        # 执行全局搜索
        global_answer = "（知识库搜索暂不可用）"
        if global_search_engine is not None:
            try:
                global_answer = execute_global_search(build_question_with_history(global_prompt, []), global_search_engine)
            except Exception as e:
                logger.error(f"全局搜索失败: {e}")
                global_answer = f"知识库搜索失败: {str(e)}"

        # 执行联网搜索
        web_answer = "（联网搜索暂不可用）"
        try:
            web_answer = execute_web_search(build_question_with_history(web_prompt, []))
        except Exception as e:
            logger.error(f"联网搜索失败: {e}")
            web_answer = f"联网搜索失败: {str(e)}"

        # 组合结果
        valuation_report = f"""
# 钱币估值报告

## 基本信息
- 钱币名称：{coin_name}
- 品相等级：{coin_grade}

## 历史背景与设计特点（来自知识库）
{global_answer}

## 市场行情参考（来自联网搜索）
{web_answer}

---
*注：本报告仅供参考，实际价值请以专业机构鉴定和实时市场交易为准。*
""".strip()

        return jsonify({
            'coinName': coin_name,
            'coinGrade': coin_grade,
            'valuation': valuation_report,
            'globalAnswer': global_answer,
            'webAnswer': web_answer
        })

    except Exception as e:
        logger.error("估值生成异常", exc_info=True)
        return jsonify({'error': f'估值生成失败: {str(e)}'}), 500
