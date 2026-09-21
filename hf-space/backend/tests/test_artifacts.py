"""文物/钱币数据库路由测试"""


class TestArtifacts:
    def test_get_classification(self, client):
        resp = client.get("/api/artifacts/classification")
        assert resp.status_code == 200
        data = resp.json
        assert isinstance(data, dict)
        assert "jizhiyinbi" in data

    def test_search_items_without_params(self, client):
        resp = client.get("/api/artifacts/searchItems")
        assert resp.status_code == 200
        assert isinstance(resp.json, list)

    def test_search_items_with_pagination(self, client):
        resp = client.get("/api/artifacts/searchItems?page=1&limit=5")
        assert resp.status_code == 200
        assert isinstance(resp.json, list)
        assert len(resp.json) <= 5

    def test_get_filters(self, client):
        resp = client.get("/api/artifacts/filters")
        assert resp.status_code == 200
        assert "dynasties" in resp.json
        assert "provinces" in resp.json

    def test_kg_graph(self, client):
        resp = client.get("/api/kg/graph")
        assert resp.status_code == 200
        data = resp.json
        assert "nodes" in data
        assert "edges" in data
