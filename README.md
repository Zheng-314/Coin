# 知识图谱智能问答系统

## 项目简介

一个基于知识图谱的智能问答系统，支持文物知识查询、图像识别和预测分析。该系统利用Neo4j图数据库存储文物相关知识，结合自然语言处理和计算机视觉技术，为用户提供智能化的文物信息服务。

## 技术栈

- **后端**: Python 3.11+, Flask, Neo4j
- **前端**: Vue 3, Element Plus, Vite
- **数据库**: Neo4j 图数据库
- **AI模型**: YOLO (目标检测), ONNX (模型推理)
- **其他**: OpenAI API, Tavily API

## 系统要求

- **操作系统**: Windows / Ubuntu 系统
- **硬件要求**: 支持CPU模式运行，可选华为昇腾NPU加速
- **数据库**: Neo4j 图数据库 5.0+
- **Python**: 3.11+
- **Node.js**: 16+
- **Conda**: 4.10+ (推荐)

## 环境配置

### 1. 后端环境配置

```bash
# 创建conda环境
conda env create -f backend/environment.yml

# 激活环境
conda activate rag_env

# 安装额外依赖
pip install -r requirements.txt
```

### 2. 前端环境配置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install
```

### 3. 环境变量配置

在 `backend/.env` 文件中配置以下环境变量：

```
# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=your_openai_api_base (可选)

# Tavily API配置
TAVILY_API_KEY=your_tavily_api_key

# Neo4j数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

## 运行步骤

### 1. 启动Neo4j数据库

```bash
# 启动Neo4j服务
# Windows: 打开Neo4j Desktop并启动数据库
# Ubuntu: sudo systemctl start neo4j

# 访问 http://localhost:7474 进行数据库配置
# 默认用户名: neo4j
# 首次登录需要设置新密码
```

### 2. 导入数据

```bash
# 运行数据导入脚本
python import_neo4j.py
```

### 3. 启动后端服务

```bash
# 进入后端目录
cd backend

# 启动Flask应用
python app_new.py
```

后端服务将在 `http://localhost:5000` 启动

### 4. 启动前端服务

```bash
# 进入前端目录
cd frontend

# 启动开发服务器
npm run dev
```

前端服务将在 `http://localhost:5173` 启动

## 项目结构

```
knowledge-graph-qa-system/
├── backend/                 # 后端服务
│   ├── app_new.py          # Flask主应用
│   ├── environment.yml     # Conda环境配置
│   ├── models/             # 数据模型
│   ├── routes/             # API路由
│   ├── services/           # 业务逻辑
│   ├── utils/              # 工具函数
│   └── instance/           # 实例文件
├── frontend/               # 前端Vue应用
│   ├── src/
│   │   ├── components/     # Vue组件
│   │   ├── views/          # 页面视图
│   │   ├── router/         # 路由配置
│   │   └── stores/         # 状态管理
│   └── package.json        # 前端依赖
├── data/                   # 数据文件
│   └── artifacts/          # 知识图谱数据
├── import_neo4j.py         # Neo4j数据导入脚本
├── requirements.txt        # Python依赖
└── README.md               # 项目说明
```

## 主要功能

- **知识图谱查询**: 基于Neo4j的图数据库查询，支持复杂关系检索
- **智能问答**: 支持自然语言问答，结合RAG技术提供准确回答
- **图像识别**: 基于YOLO模型的文物识别，支持多种文物类型
- **用户管理**: 用户注册、登录、权限管理
- **数据可视化**: 知识图谱可视化展示，直观呈现文物关系
- **文物估值**: 基于历史数据的文物价值评估

## API文档

### 后端API端点

- `GET /api/health` - 健康检查
- `POST /api/users/login` - 用户登录
- `POST /api/users/register` - 用户注册
- `GET /api/artifacts` - 获取文物列表
- `GET /api/artifacts/:id` - 获取文物详情
- `POST /api/qa` - 智能问答
- `POST /predict` - 图像识别预测
- `POST /api/valuation` - 文物估值

## 注意事项

1. **首次运行**：需要先启动Neo4j数据库并执行数据导入脚本
2. **环境变量**：确保正确配置 `backend/.env` 文件中的API密钥
3. **依赖安装**：前端和后端依赖都需要安装
4. **服务启动顺序**：Neo4j → 后端 → 前端
5. **硬件加速**：如使用华为昇腾NPU，请确保安装了相应驱动
6. **性能优化**：对于大规模数据，建议配置适当的Neo4j内存设置

## 故障排除

### 常见问题

1. **Neo4j连接失败**：检查Neo4j服务是否启动，连接信息是否正确
2. **API密钥错误**：确保 `.env` 文件中的API密钥有效
3. **依赖安装失败**：尝试使用 `pip install --upgrade pip` 后重新安装
4. **端口占用**：确保5000和5173端口未被占用

### 日志查看

- 后端日志：后端服务控制台输出
- 前端日志：前端服务控制台输出
- Neo4j日志：Neo4j安装目录下的logs文件夹

## 访问地址

- **前端界面**: http://localhost:5173
- **后端API**: http://localhost:5000
- **Neo4j数据库**: http://localhost:7474

## 贡献指南

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

## 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

