# 后端代码重构说明

## 重构完成时间
2026-02-25

## 文件结构

```
backend/
├── app.py                 # 主入口 (新，简化版)
├── app_old_backup.py      # 原始文件备份
├── config.py              # 配置和常量
├── models/                # 模型加载和管理
│   ├── __init__.py
│   └── model_loader.py
├── routes/                # API路由
│   ├── __init__.py
│   ├── auth.py           # 用户认证 (注册/登录)
│   ├── artifacts.py      # 钱币数据库查询
│   ├── qa.py             # Q&A问答 (GraphRAG)
│   ├── predict.py        # AI预测鉴定
│   ├── user_actions.py   # 用户操作 (收藏、历史)
│   └── valuation.py      # 估值功能
├── services/             # 业务逻辑层
│   ├── __init__.py       # RAG系统初始化
│   ├── yolo_service.py   # YOLO检测服务
│   ├── onnx_service.py   # ONNX推理服务
│   ├── rag_service.py    # RAG问答服务
│   └── data_parser.py    # 数据解析工具
└── utils/                # 工具函数
    ├── __init__.py
    ├── database.py       # 数据库连接
    ├── decorators.py     # 装饰器 (token_required)
    └── helpers.py        # 辅助函数
```

## 模块说明

### 1. config.py
- 所有配置变量
- 环境变量加载
- 模型路径配置
- LLM配置

### 2. models/model_loader.py
- YOLO模型加载
- ONNX模型加载
- 模型初始化状态检查

### 3. routes/*.py (API路由)
- **auth.py**: `/api/users/register`, `/api/users/login`
- **artifacts.py**: `/api/artifacts/*` (分类、搜索、筛选)
- **qa.py**: `/api/ask`, `/api/ask/capabilities`
- **predict.py**: `/predict`, `/api/predict/capabilities`
- **user_actions.py**: `/api/user-actions/*`, `/api/chat/*`
- **valuation.py**: `/api/valuation`

### 4. services/*.py (业务逻辑)
- **yolo_service.py**: 钱币检测和圆形分割
- **onnx_service.py**: 图像预处理和模型推理
- **rag_service.py**: 本地/全局搜索、联网搜索、关键词兜底
- **data_parser.py**: 数据解析工具

### 5. utils/*.py (工具函数)
- **database.py**: 数据库连接函数
- **decorators.py**: JWT token验证装饰器
- **helpers.py**: 辅助函数 (json_response, encode_image_to_base64等)

## API端点映射 (保持不变)

| 功能 | 端点 | 文件 |
|------|------|------|
| 注册 | POST /api/users/register | routes/auth.py |
| 登录 | POST /api/users/login | routes/auth.py |
| 分类 | GET /api/artifacts/classification | routes/artifacts.py |
| 搜索 | GET /api/artifacts/searchItems | routes/artifacts.py |
| 筛选 | GET /api/artifacts/filters | routes/artifacts.py |
| 详情 | GET /api/artifacts/search | routes/artifacts.py |
| 问答 | POST /api/ask | routes/qa.py |
| 问答能力 | GET /api/ask/capabilities | routes/qa.py |
| 预测 | POST /predict | routes/predict.py |
| 预测能力 | GET /api/predict/capabilities | routes/predict.py |
| 添加收藏 | POST /api/user-actions/favorite | routes/user_actions.py |
| 获取收藏 | GET /api/user-actions/favorite | routes/user_actions.py |
| 收藏状态 | GET /api/user-actions/favorite/status | routes/user_actions.py |
| 聊天历史 | GET /api/chat/history | routes/user_actions.py |
| 保存消息 | POST /api/chat/history | routes/user_actions.py |
| 估值 | POST /api/valuation | routes/valuation.py |

## 运行方式

```bash
cd backend
python app.py
```

服务将在 `http://0.0.0.0:5001` 启动

## 注意事项

1. 原始 `app.py` 已备份为 `app_old_backup.py`
2. 所有API端点路径保持不变，前端无需修改
3. 模型文件位置不变 (`best1.pt`, `best2.pt`, `best_model.onnx`)
4. 数据库文件位置不变 (`instance/user.db`, `instance/item.db`)
5. 环境变量配置不变 (.env文件)

## 可能的问题

如果遇到导入错误，请确保：
1. 所有依赖已安装 (`pip install -r requirements.txt`)
2. 工作目录在 `backend` 文件夹内
3. 模型文件存在于 `backend` 目录
4. 数据库文件存在于 `backend/instance` 目录
