# -*- coding: utf-8 -*-
"""
真伪鉴定服务

设计定位
--------
本模块负责「真伪初筛」的全部系统逻辑，**模型部分留出接入点**：

    有模型  -> 调用模型给出风险分与部位级判断
    无模型  -> 返回 status="model_not_installed"，但仍然给出部位级提示
               （即"该看哪里、正品什么样、仿品什么样"），保证产品可用

产品原则
--------
1. 不做真伪判决。输出为「风险等级 + 待核查部位」，措辞一律为提示。
2. 拿不准就说拿不准，绝不返回一个漂亮的假分数。
3. 每条提示都要能追到出处。

模型接入约定
------------
放置文件：backend/authenticity.onnx
输入：input1、input2，shape [batch, 3, 224, 224]，float32，RGB，ImageNet 标准化
输出：二分类 logits [batch, 2]，index 1 = 存疑概率
若输出维度不符，视为未接入并回落到提示模式。

训练方案见 docs/真伪鉴定与多模态方案.md
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger("services.authenticity")

BACKEND_DIR = Path(__file__).resolve().parent.parent
HINTS_PATH = BACKEND_DIR.parent / "data" / "authenticity" / "part_hints.json"
MODEL_PATH = BACKEND_DIR / "authenticity.onnx"

PARTS = ["边齿", "珠圈", "字口", "包浆", "重量", "声音"]

DISCLAIMER = (
    "本功能为初筛提示，不构成真伪结论。系统只提示应当核查的部位与特征，"
    "高风险或高价值藏品请送专业评级机构出具正式结论。"
)

_session = None
_session_loaded = False

_hints_cache = None


def load_hints() -> dict:
    """加载部位级提示库（缺失时返回空结构，不影响接口可用）"""
    global _hints_cache
    if _hints_cache is not None:
        return _hints_cache
    if not HINTS_PATH.exists():
        logger.warning("未找到提示库 %s，将返回空提示", HINTS_PATH)
        _hints_cache = {"parts": PARTS, "hints": [], "by_part": {p: [] for p in PARTS}}
        return _hints_cache
    try:
        with open(HINTS_PATH, encoding="utf-8") as f:
            _hints_cache = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.error("提示库读取失败: %s", exc)
        _hints_cache = {"parts": PARTS, "hints": [], "by_part": {p: [] for p in PARTS}}
    return _hints_cache


def model_status() -> dict:
    """返回模型接入状态，供 capabilities 与前端展示使用"""
    installed = MODEL_PATH.exists()
    dim = None
    if installed and get_session() is not None:
        try:
            shape = _session.get_outputs()[0].shape
            dim = int(shape[-1]) if shape and isinstance(shape[-1], int) else None
        except Exception:  # noqa: BLE001
            dim = None
    return {
        "installed": installed,
        "path": str(MODEL_PATH),
        "output_dim": dim,
        "expected_output_dim": 2,
        "ready": installed and dim == 2,
        "note": (
            "模型已接入" if installed and dim == 2
            else ("模型文件存在但输出维度不是 2，按未接入处理" if installed
                  else "未接入模型，当前仅提供部位级提示")
        ),
    }


def get_session():
    """懒加载 ONNX 会话；失败返回 None（不抛异常，保证接口可用）"""
    global _session, _session_loaded
    if _session_loaded:
        return _session
    _session_loaded = True
    if not MODEL_PATH.exists():
        return None
    try:
        import onnxruntime as ort
        _session = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])
        logger.info("真伪鉴定模型已加载: %s", MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        logger.error("真伪鉴定模型加载失败: %s", exc)
        _session = None
    return _session


def _preprocess(bgr: np.ndarray) -> np.ndarray:
    """BGR ndarray -> [1,3,224,224] float32（与版式模型保持同一套预处理）"""
    import cv2
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_LANCZOS4)
    arr = resized.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std
    arr = np.transpose(arr, (2, 0, 1))
    return np.expand_dims(arr, axis=0)


def run_model(img_front: np.ndarray, img_back: np.ndarray):
    """调用真伪模型。未接入或失败返回 None。"""
    session = get_session()
    if session is None:
        return None
    try:
        inputs = {
            session.get_inputs()[0].name: _preprocess(img_front),
            session.get_inputs()[1].name: _preprocess(img_back),
        }
        out = session.run(None, inputs)[0]
        logits = np.asarray(out).flatten()
        if logits.size != 2:
            logger.error("真伪模型输出维度 %d，期望 2", logits.size)
            return None
        exp = np.exp(logits - logits.max())
        probs = exp / exp.sum()
        return {"suspicious_prob": float(probs[1]), "genuine_prob": float(probs[0])}
    except Exception as exc:  # noqa: BLE001
        logger.error("真伪模型推理失败: %s", exc)
        return None


def _risk_from_prob(p: float) -> str:
    if p >= 0.75:
        return "高"
    if p >= 0.5:
        return "中"
    return "低"


def build_checks(variety: str | None = None, limit_per_part: int = 2) -> list[dict]:
    """按部位组织提示。variety 命中时优先返回相关条目（当前按全文匹配）。"""
    data = load_hints()
    hints = data.get("hints", [])
    if variety:
        key = variety.split(">")[-1].strip() or variety
        related = [h for h in hints if key and key in h["text"]]
        if related:
            hints = related + [h for h in hints if h not in related]

    checks = []
    for part in PARTS:
        items = [h for h in hints if h["part"] == part][:limit_per_part]
        checks.append({
            "part": part,
            "hints": [{"text": i["text"], "judged": bool(i.get("judged")),
                       "source": i.get("source", "")} for i in items],
            "result": "未评估" if not items else "待人工核查",
        })
    return checks


def check(img_front: np.ndarray, img_back: np.ndarray, variety: str | None = None) -> dict:
    """真伪初筛主入口

    Returns:
        dict，字段见模块文档。status 取值：
            ok                  模型给出风险等级
            model_not_installed 无模型，仅返回部位提示
            rejected            输入不可用
    """
    if img_front is None or img_back is None:
        return {
            "status": "rejected",
            "message": "图片无法解析，请上传清晰的钱币正反面照片",
            "checks": [],
        }

    status = model_status()
    result = run_model(img_front, img_back)

    payload = {
        "variety": variety,
        "checks": build_checks(variety),
        "model": status,
        "disclaimer": DISCLAIMER,
    }

    if result is None:
        payload.update({
            "status": "model_not_installed",
            "risk_level": "unknown",
            "score": None,
            "message": ("真伪模型尚未接入，当前仅提供应当核查的部位与特征。"
                        "请在生产环境放置 backend/authenticity.onnx 后启用风险评级。"),
        })
        return payload

    payload.update({
        "status": "ok",
        "risk_level": _risk_from_prob(result["suspicious_prob"]),
        "score": round(result["suspicious_prob"], 4),
        "message": "已给出风险等级，请结合部位提示人工核查。",
    })
    return payload


def build_hint_context(variety: str | None = None, max_items: int = 4) -> str:
    """为多模态问答生成「部位提示」上下文文本"""
    checks = build_checks(variety)
    lines = []
    for c in checks:
        for h in c["hints"]:
            lines.append(f"[{c['part']}] {h['text']}")
            if len(lines) >= max_items:
                break
        if len(lines) >= max_items:
            break
    if not lines:
        return ""
    return "【鉴别要点（按部位）】\n" + "\n".join(lines)
