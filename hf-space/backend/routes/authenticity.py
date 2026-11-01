# -*- coding: utf-8 -*-
"""
真伪初筛接口

    POST /api/authenticity/check        上传正反面，返回风险等级 + 部位级提示
    GET  /api/authenticity/capabilities 模型接入状态与部位清单
    GET  /api/authenticity/parts        部位级提示库（供前端展示）

说明：本接口在模型未接入时仍返回可用结果（部位提示），status 为 model_not_installed。
"""
import logging

import cv2
import numpy as np
from flask import Blueprint, jsonify, request

from app_new import limiter
from services import authenticity_service as svc

logger = logging.getLogger("routes.authenticity")

authenticity_bp = Blueprint("authenticity", __name__)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def _read_image(file_storage):
    """校验并解码上传文件，返回 (ndarray|None, 错误信息|None)"""
    if file_storage is None or not file_storage.filename:
        return None, "缺少图片文件"

    name = file_storage.filename.lower()
    if not any(name.endswith(ext) for ext in ALLOWED_EXT):
        return None, "不支持的文件格式，请上传 JPG、PNG、WebP 或 BMP 图片"

    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_FILE_SIZE:
        return None, "图片文件过大，请上传 10MB 以内的图片"

    data = np.frombuffer(file_storage.read(), np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        return None, "图片无法解析，请更换清晰图片后重试"
    return img, None


@authenticity_bp.route("/api/authenticity/capabilities", methods=["GET"])
def capabilities():
    status = svc.model_status()
    hints = svc.load_hints()
    return jsonify({
        "status": "ok",
        "model": status,
        "parts": svc.PARTS,
        "hint_count": len(hints.get("hints", [])),
        "by_part_count": {p: len(v) for p, v in hints.get("by_part", {}).items()},
        "disclaimer": svc.DISCLAIMER,
    })


@authenticity_bp.route("/api/authenticity/parts", methods=["GET"])
def parts():
    """返回部位级提示库；支持 ?part=边齿 过滤"""
    part = request.args.get("part", "").strip()
    hints = svc.load_hints()
    items = hints.get("hints", [])
    if part:
        items = [h for h in items if h.get("part") == part]
    return jsonify({
        "status": "ok",
        "parts": svc.PARTS,
        "total": len(items),
        "items": items,
    })


@authenticity_bp.route("/api/authenticity/check", methods=["POST"])
@limiter.limit("20 per minute")
def check():
    """真伪初筛（不构成真伪结论）"""
    img_front, err1 = _read_image(request.files.get("image1"))
    img_back, err2 = _read_image(request.files.get("image2"))

    if err1 or err2:
        return jsonify({
            "status": "rejected",
            "message": err1 or err2,
            "checks": [],
        }), 400

    # 可选的版式提示，用于优先返回该币种相关条目
    variety = (request.form.get("variety") or "").strip() or None

    result = svc.check(img_front, img_back, variety)

    if result["status"] == "rejected":
        return jsonify(result), 400

    logger.info(
        "真伪初筛: status=%s risk=%s variety=%s",
        result["status"], result.get("risk_level"), variety,
    )
    return jsonify(result)
