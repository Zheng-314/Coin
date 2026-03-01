# ==============================================================================
# 用户认证路由
# ==============================================================================
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from utils.database import get_user_db_connection
from utils.helpers import json_response
from config import SECRET_KEY

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/users/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    username, password = data.get('username'), data.get('password')
    user_role = data.get('userRole', 'user')

    if not username or not password:
        return json_response({"message": "用户名和密码是必填项"}, 400)

    conn = get_user_db_connection()
    try:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn.execute("INSERT INTO users (username, password, userRole) VALUES (?, ?, ?)",
                     (username, hashed_password, user_role))
        conn.commit()
    except Exception as e:
        if "UNIQUE constraint" in str(e) or "already exists" in str(e):
            return json_response({"message": "用户名已存在"}, 409)
        raise
    finally:
        conn.close()

    return json_response({"message": "用户注册成功"}, 201)

@auth_bp.route('/api/users/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username, password = data.get('username'), data.get('password')

    conn = get_user_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        payload = {
            'username': user['username'],
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return json_response({
            "id": user['id'],
            "message": "登录成功",
            "token": token,
            "username": user['username']
        })

    return json_response({"message": "用户名或密码无效"}, 401)
