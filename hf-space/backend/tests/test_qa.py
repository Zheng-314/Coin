"""Q&A 路由测试"""
import json


class TestAskEndpoint:
    def test_ask_empty_question(self, client):
        resp = client.post("/api/ask", json={"question": ""})
        assert resp.status_code == 400

    def test_ask_without_question(self, client):
        resp = client.post("/api/ask", json={})
        assert resp.status_code == 400

    def test_ask_with_question(self, client):
        resp = client.post("/api/ask", json={"question": "袁大头", "searchType": "local"})
        assert resp.status_code == 200
        data = resp.json
        assert "answer" in data
        assert "sources" in data

    def test_capabilities(self, client):
        resp = client.get("/api/ask/capabilities")
        assert resp.status_code == 200
        data = resp.json
        assert "local" in data
        assert "global" in data
        assert "web" in data
