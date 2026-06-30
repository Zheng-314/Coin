import json
import logging

from flask import Blueprint, Response, jsonify, request, stream_with_context

logger = logging.getLogger('routes.qa')

from config import EMBED_PROVIDER_BLOCKED, WEB_SEARCH_IMPORTS_AVAILABLE
from services.rag_service import (
    build_question_with_history,
    execute_global_search,
    execute_keyword_fallback_payload,
    execute_local_search,
    execute_web_search,
    analyze_image_with_qwen_vl,
)

qa_bp = Blueprint("qa", __name__)


def _needs_fallback(answer: str) -> bool:
    text = (answer or "")
    lowered = text.lower()
    cn_markers = ["暂不可用", "不可用", "失败"]
    en_markers = ["unavailable", "failed", "error"]
    return any(marker in text for marker in cn_markers) or any(marker in lowered for marker in en_markers)


def _identify_coin_from_images(image_files, question=""):
    """
    多模态图片分析：优先用Qwen-VL直接看图，降级用YOLO+ONNX

    Returns:
        (results_list, context_text)
    """
    # 优先：Qwen-VL真正的多模态分析
    logger.info("尝试Qwen-VL视觉分析...")
    qwen_result = analyze_image_with_qwen_vl(image_files, question)
    if qwen_result:
        logger.info("Qwen-VL分析成功")
        # 重新读取文件（因为已经被Qwen-VL消费了）
        for f in image_files:
            f.seek(0)
        return [{"type": "qwen-vl", "description": qwen_result}], f"【图片分析结果】\n{qwen_result}"

    # 降级：YOLO+ONNX分类
    logger.info("Qwen-VL不可用，降级到YOLO+ONNX...")
    import cv2
    import numpy as np
    from services.yolo_service import detect_yolo
    from services.onnx_service import run_onnx_pair_inference
    from models.model_loader import ensure_onnx_session_ready
    from routes.predict import load_class_names, run_optional_yolo_pipeline

    ok, _ = ensure_onnx_session_ready()
    if not ok:
        return None, "鉴定模型未就绪"

    load_class_names()

    # 重置文件指针
    for f in image_files:
        f.seek(0)

    images = []
    for f in image_files:
        data = np.frombuffer(f.read(), np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is not None:
            images.append(img)

    if len(images) < 2:
        if len(images) == 1:
            images.append(images[0])
        else:
            return None, "无法解析图片"

    det1 = detect_yolo(images[0])
    det2 = detect_yolo(images[1])

    if not (det1 and len(det1)) and not (det2 and len(det2)):
        return None, "图片中未检测到钱币"

    processed1 = run_optional_yolo_pipeline(images[0])
    processed2 = run_optional_yolo_pipeline(images[1])

    from routes.predict import CLASS_NAMES
    candidate_pairs = [
        ('processed', 'normal', processed1, processed2),
        ('processed', 'swapped', processed2, processed1),
        ('raw', 'normal', images[0], images[1]),
        ('raw', 'swapped', images[1], images[0]),
    ]

    best = None
    for _, _, img_a, img_b in candidate_pairs:
        probs = run_onnx_pair_inference(img_a, img_b)
        if probs is not None:
            if len(probs.shape) == 2:
                probs = probs[0]
            top1_idx = int(np.argmax(probs))
            top1_conf = float(probs[top1_idx])
            if best is None or top1_conf > best['top1_confidence']:
                best = {'probs': probs, 'top1_idx': top1_idx, 'top1_confidence': top1_conf}

    if best is None:
        return None, "鉴定失败"

    sorted_indices = np.argsort(best['probs'])[::-1][:3]
    results = []
    for idx in sorted_indices:
        idx_int = int(idx)
        conf = float(best['probs'][idx_int])
        name = CLASS_NAMES[idx_int] if idx_int < len(CLASS_NAMES) else f'类别#{idx_int}'
        results.append({'name': name, 'confidence': round(conf * 100, 1)})

    lines = ["【图片鉴定结果（YOLO+ONNX）】"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['name']}（置信度: {r['confidence']}%）")

    return results, "\n".join(lines)


def _resolve_answer(search_type, question, question_with_history, global_search_engine, local_search_chain, image_context=None):
    """统一的问答逻辑，返回 (answer, sources)"""
    sources = []

    # 如果有图片鉴定结果，加到问题前面
    if image_context:
        enhanced_question = f"{image_context}\n\n用户问题：{question}"
        enhanced_with_history = f"{image_context}\n\n{question_with_history}"
    else:
        enhanced_question = question
        enhanced_with_history = question_with_history

    if search_type == "local":
        if local_search_chain is None:
            return execute_keyword_fallback_payload(enhanced_question)
        answer = execute_local_search(enhanced_with_history, local_search_chain)
        sources = [{"type": "engine", "name": "GraphRAG Local"}]
        if _needs_fallback(answer):
            return execute_keyword_fallback_payload(enhanced_question)
        return answer, sources
    elif search_type == "global":
        if global_search_engine is None:
            return execute_keyword_fallback_payload(enhanced_question)
        answer = execute_global_search(enhanced_with_history, global_search_engine)
        sources = [{"type": "engine", "name": "GraphRAG Global"}]
        if _needs_fallback(answer):
            return execute_keyword_fallback_payload(enhanced_question)
        return answer, sources
    elif search_type == "web":
        answer = execute_web_search(enhanced_with_history)
        sources = [{"type": "engine", "name": "Web Search Summary"}]
        if _needs_fallback(answer):
            fallback_answer, fallback_sources = execute_keyword_fallback_payload(enhanced_question)
            answer = f"{answer}\n\n{fallback_answer}"
            sources.extend(fallback_sources)
        return answer, sources
    else:
        return "unknown searchType: use local, global, or web", []


@qa_bp.route("/api/ask", methods=["POST"])
def ask():
    from services import global_search_engine, local_search_chain

    # 支持JSON和multipart/form-data（带图片）
    if request.content_type and 'multipart' in request.content_type:
        question = request.form.get("question", "")
        history = request.form.get("history", "[]")
        search_type = request.form.get("searchType", "local")
        stream = request.form.get("stream", "false").lower() == "true"
        try:
            history = json.loads(history) if isinstance(history, str) else history
        except:
            history = []
        image_files = request.files.getlist("images")
    else:
        data = request.get_json() or {}
        question = data.get("question", "")
        history = data.get("history", [])
        search_type = data.get("searchType", "local")
        stream = data.get("stream", False)
        image_files = []

    if not question and not image_files:
        return jsonify({"answer": "请输入问题。"}), 400

    # 如果有图片，先做鉴定
    image_context = None
    image_identification = None
    if image_files and len(image_files) >= 1:
        logger.info(f"收到 {len(image_files)} 张图片，开始多模态分析...")
        image_identification, image_context = _identify_coin_from_images(image_files, question)
        if image_context and "未检测到" not in image_context and "失败" not in image_context:
            logger.info(f"分析成功: {image_context[:100]}")
        elif image_context:
            logger.warning(f"分析问题: {image_context}")

    # 如果只有图片没有问题，自动生成问题
    if not question:
        if image_identification:
            question = "请详细介绍一下这个钱币的历史背景、版别特征和市场价值。"
        else:
            question = "请帮我看看这是什么钱币。"

    question_with_history = build_question_with_history(question, history)

    try:
        answer, sources = _resolve_answer(
            search_type, question, question_with_history,
            global_search_engine, local_search_chain, image_context
        )
    except Exception as e:
        logger.error(f"QA request failed for question={question!r}: {e}")
        logger.error("QA request exception", exc_info=True)
        if stream:
            def _err_gen():
                yield f"data: {json.dumps({'error': True, 'answer': '处理您的问题时发生内部错误。'}, ensure_ascii=False)}\n\n"
            return Response(stream_with_context(_err_gen()), mimetype="text/event-stream", status=500)
        return jsonify({"answer": "处理您的问题时发生内部错误。"}), 500

    # 如果有鉴定结果，加到sources里
    if image_identification:
        sources.insert(0, {"type": "identification", "results": image_identification})

    if stream:
        def _generate():
            for char in answer:
                yield f"data: {json.dumps({'delta': char}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': sources, 'searchType': search_type}, ensure_ascii=False)}\n\n"

        return Response(
            stream_with_context(_generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    return jsonify({"answer": answer, "sources": sources, "searchType": search_type})


@qa_bp.route("/api/ask/capabilities", methods=["GET"])
def ask_capabilities():
    from services import (
        global_search_engine,
        global_search_reason,
        llm,
        local_search_chain,
        local_search_reason,
    )

    local_engine_available = local_search_chain is not None and not EMBED_PROVIDER_BLOCKED
    global_engine_available = global_search_engine is not None
    web_engine_available = WEB_SEARCH_IMPORTS_AVAILABLE and llm is not None

    return jsonify(
        {
            "local": {
                "available": True,
                "engineAvailable": local_engine_available,
                "reason": "" if local_engine_available else (local_search_reason or "local mode will use offline fallback"),
            },
            "global": {
                "available": True,
                "engineAvailable": global_engine_available,
                "reason": "" if global_engine_available else (global_search_reason or "global mode will use offline fallback"),
            },
            "web": {
                "available": True,
                "engineAvailable": web_engine_available,
                "reason": "" if web_engine_available else "web mode will use offline fallback",
            },
            "multimodal": {
                "available": True,
                "description": "支持上传图片进行钱币鉴定+知识问答"
            }
        }
    )
