# ADR-001: 选择 Flask 作为后端框架

## 状态

已采纳（2025 年 10 月）

## 背景

项目需要一个后端框架来提供 REST API，支持：
- 文件上传（钱币图片）
- SSE 流式响应（问答）
- 与 Python ML 生态（PyTorch、ONNX Runtime）紧密集成
- 轻量级，适合小团队快速开发

## 决策

选择 **Flask 3.x** 而非 FastAPI / Django。

## 理由

1. **生态兼容**：YOLO (ultralytics) 和 ONNX Runtime 在 Flask 线程模型中稳定运行
2. **学习成本**：团队成员熟悉 Flask，快速上手
3. **灵活性**：蓝图模块化组织，按需加载
4. **足够性能**：单个请求处理耗时主要在模型推理（秒级），框架开销可忽略

## 代价

- 无原生异步支持（通过 SSE + generator 模式弥补）
- 缺少自动 API 文档（需手动维护）
- 蓝图注册需注意部署方式（已修复：register_blueprints() 移到模块级）

## 备选方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| **FastAPI** | 自动 Swagger、原生 async | ML 库线程安全问题，迁移成本高 |
| **Django** | 完整 ORM、admin | 过重，ML 集成不友好 |
