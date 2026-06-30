"""测试配置和共享 fixtures"""
import os
import sys
import pytest

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 加载环境变量
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
def app():
    """创建测试用 Flask 应用"""
    from app_new import app

    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "test-secret-key")
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def auth_headers():
    """生成认证请求头（用于需要登录的端点）"""
    import jwt
    from datetime import datetime, timedelta, timezone

    secret = os.getenv("SECRET_KEY", "test-secret-key")
    token = jwt.encode(
        {"username": "testuser", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}
