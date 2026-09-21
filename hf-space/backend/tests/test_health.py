"""健康检查和根路由测试"""


class TestHealth:
    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json["status"] == "ok"
        assert "服务" in resp.json["message"]

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "name" in resp.json
        assert resp.json["version"] == "2.0"
        assert "endpoints" in resp.json


class TestCORS:
    def test_cors_headers(self, client):
        resp = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        assert resp.status_code == 200
