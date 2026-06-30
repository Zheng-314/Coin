# ==============================================================================
# 用户操作路由（收藏、历史等）
# ==============================================================================
import json
import sqlite3
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from utils.database import user_db, item_db
from utils.decorators import token_required

logger = logging.getLogger('routes.user_actions')

user_actions_bp = Blueprint('user_actions', __name__)

@user_actions_bp.route('/api/user-actions/favorite', methods=['POST'])
@token_required
def add_favorite(current_user):
    """添加收藏"""
    pid = request.get_json().get('pid')
    username = current_user['username']

    try:
        with user_db() as conn:
            conn.execute(
                "INSERT INTO favorites (username, pid, timestamp) VALUES (?, ?, ?)",
                (username, pid, int(datetime.now().timestamp()))
            )
        return jsonify({"message": "收藏成功"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "您已经收藏过该物品"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_actions_bp.route('/api/user-actions/favorite', methods=['GET'])
@token_required
def get_favorites(current_user):
    """获取收藏列表"""
    username = current_user['username']

    with user_db() as user_conn:
        favorite_pids = user_conn.execute(
            "SELECT pid FROM favorites WHERE username = ?", (username,)
        ).fetchall()

    pids = [row['pid'] for row in favorite_pids]
    favorites_details = []
    if pids:
        with item_db() as item_conn:
            placeholders = ', '.join(['?'] * len(pids))
            items_raw = item_conn.execute(
                f"SELECT pid, text FROM item WHERE pid IN ({placeholders})",
                pids
            ).fetchall()
        for item in items_raw:
            favorites_details.append({
                'pid': item['pid'],
                'title': json.loads(item['text']).get('title')
            })

    return jsonify(favorites_details)

@user_actions_bp.route('/api/user-actions/favorite/status', methods=['GET'])
@token_required
def get_favorite_status(current_user):
    """检查物品收藏状态"""
    pid = request.args.get('pid')
    if not pid:
        return jsonify({"error": "PID is required"}), 400

    username = current_user['username']
    with user_db() as conn:
        item = conn.execute(
            "SELECT pid FROM favorites WHERE username = ? AND pid = ?",
            (username, pid)
        ).fetchone()

    is_favorited = True if item else False
    return jsonify({"isFavorited": is_favorited})

@user_actions_bp.route('/api/user-actions/favorite', methods=['DELETE'])
@token_required
def remove_favorite(current_user):
    """删除收藏"""
    pid = request.json.get('pid')
    username = current_user['username']

    if not pid:
        return jsonify({"error": "PID is required"}), 400

    try:
        with user_db() as conn:
            conn.execute(
                "DELETE FROM favorites WHERE username = ? AND pid = ?",
                (username, pid)
            )
        return jsonify({"message": "取消收藏成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_actions_bp.route('/api/chat/history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    """获取聊天历史"""
    username = current_user['username']

    with user_db() as conn:
        messages = conn.execute(
            "SELECT message_type, content, sources FROM chat_history WHERE username = ? ORDER BY timestamp ASC",
            (username,)
        ).fetchall()

        history = []
        for msg in messages:
            message = {"type": msg["message_type"], "text": msg["content"]}
            if msg["sources"]:
                try:
                    message["sources"] = json.loads(msg["sources"])
                except:
                    pass
            history.append(message)
        return jsonify(history)

@user_actions_bp.route('/api/chat/history', methods=['POST'])
@token_required
def save_chat_message(current_user):
    """保存聊天消息"""
    data = request.get_json()
    username = current_user['username']
    message_type = data.get('type')  # 'user' or 'bot'
    content = data.get('text')
    sources = data.get('sources')

    if not message_type or not content:
        return jsonify({"error": "type and text are required"}), 400

    try:
        with user_db() as conn:
            conn.execute(
                "INSERT INTO chat_history (username, message_type, content, sources, timestamp) VALUES (?, ?, ?, ?, ?)",
                (username, message_type, content, json.dumps(sources) if sources else None, int(datetime.now().timestamp()))
            )
        return jsonify({"message": "消息保存成功"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500