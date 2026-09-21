"""用户认证路由测试"""
import json


class TestRegister:
    def test_register_missing_username(self, client):
        resp = client.post("/api/users/register", json={"password": "123456"})
        assert resp.status_code == 400
        assert "必填" in resp.json["message"]

    def test_register_missing_password(self, client):
        resp = client.post("/api/users/register", json={"username": "test_user"})
        assert resp.status_code == 400
        assert "必填" in resp.json["message"]

    def test_register_success(self, client):
        import uuid

        uname = f"test_{uuid.uuid4().hex[:8]}"
        resp = client.post("/api/users/register", json={"username": uname, "password": "123456"})
        assert resp.status_code == 201
        assert "成功" in resp.json["message"]


class TestLogin:
    def test_login_empty_credentials(self, client):
        resp = client.post("/api/users/login", json={})
        assert resp.status_code == 401

    def test_login_wrong_password(self, client):
        resp = client.post("/api/users/login", json={"username": "nonexistent", "password": "wrong"})
        assert resp.status_code == 401
        assert "无效" in resp.json["message"] or "错误" in resp.json.get("error", "")
