"""AI 预测路由测试"""


class TestPredictCapabilities:
    def test_get_capabilities(self, client):
        resp = client.get("/api/predict/capabilities")
        assert resp.status_code == 200
        data = resp.json
        assert "ready" in data
        assert "yolo1_ready" in data
        assert "onnx_ready" in data

    def test_get_classes(self, client):
        resp = client.get("/api/predict/classes")
        assert resp.status_code == 200
        data = resp.json
        assert "classes" in data
        assert isinstance(data["classes"], list)
        assert data["count"] > 0  # 92 classes


class TestPredictValidation:
    def test_predict_without_files(self, client):
        resp = client.post("/predict", data={}, content_type="multipart/form-data")
        # 模型未就绪会返回 503，文件缺失返回 400
        assert resp.status_code in (400, 422, 503)

    def test_predict_with_invalid_extension(self, client):
        resp = client.post(
            "/predict",
            data={"image1": (open(__file__, "rb"), "test.txt")},
            content_type="multipart/form-data",
        )
        # 模型未就绪 503，文件格式不对 400
        assert resp.status_code in (400, 422, 503)
