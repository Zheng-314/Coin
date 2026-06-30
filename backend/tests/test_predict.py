"""AI 预测路由测试"""


class TestPredictCapabilities:
    def test_get_capabilities(self, client):
        resp = client.get("/api/predict/capabilities")
        assert resp.status_code == 200
        assert "yolo_available" in resp.json
        assert "onnx_available" in resp.json

    def test_get_classes(self, client):
        resp = client.get("/api/predict/classes")
        assert resp.status_code == 200
        assert isinstance(resp.json, list)
        assert len(resp.json) > 0  # 92 classes


class TestPredictValidation:
    def test_predict_without_files(self, client):
        resp = client.post("/predict", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_predict_with_invalid_extension(self, client):
        resp = client.post(
            "/predict",
            data={"image1": (open(__file__, "rb"), "test.txt")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
