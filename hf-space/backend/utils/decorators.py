# ==============================================================================
# 装饰器
# ==============================================================================
import jwt
import functools
from flask import request, jsonify
from config import SECRET_KEY

def token_required(f):
    """JWT token验证装饰器"""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '缺少token'}), 401

        try:
            # 移除 'Bearer ' 前缀（如果有）
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效的token'}), 401

        return f(current_user, *args, **kwargs)
    return decorated
