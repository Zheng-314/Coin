# 知识图谱智能问答系统

一个基于知识图谱的智能问答系统，支持文物知识查询、图像识别和预测分析。

## 系统要求

- **操作系统**: Ubuntu 系统
- **硬件要求**: 华为昇腾NPU（后端包含ACL编程）
- **数据库**: Neo4j 图数据库
- **Python**: 3.11+
- **Node.js**: 16+

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

## 运行步骤

### 1. 启动Neo4j数据库

```bash
# 下载并安装Neo4j
# 启动Neo4j服务
neo4j start

# 访问 http://localhost:7474 进行数据库配置
# 默认用户名: neo4j
# 密码: 请使用您本地安全密码（不要写入前端代码）
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
python app.py
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
MyApplication/
├── backend/                 # 后端服务
│   ├── app.py              # Flask主应用
│   ├── environment.yml     # Conda环境配置
│   ├── models/             # 数据模型
│   ├── routes/             # API路由
│   └── services/              # 业务逻辑
├── frontend/               # 前端Vue应用
│   ├── src/
│   │   ├── components/     # Vue组件
│   │   ├── views/          # 页面视图
│   │   └── router/         # 路由配置
│   └── package.json
├── data/                   # 数据文件
│   └── artifacts/          # 知识图谱数据
├── import_neo4j.py         # Neo4j数据导入脚本
└── requirements.txt        # Python依赖
```

## 主要功能

- **知识图谱查询**: 基于Neo4j的图数据库查询
- **智能问答**: 支持自然语言问答
- **图像识别**: 基于YOLO模型的文物识别
- **用户管理**: 用户注册、登录、权限管理
- **数据可视化**: 知识图谱可视化展示

## 注意事项

1. 确保系统已安装华为昇腾NPU驱动
2. Neo4j数据库需要先启动并配置好连接信息
3. 首次运行需要执行数据导入脚本
4. 后端和前端服务需要同时运行才能正常使用
5. OpenAI / Tavily 密钥请放在 `backend/.env`（例如 `OPENAI_API_KEY`、`OPENAI_API_BASE`、`TAVILY_API_KEY`）

## 访问地址

- 前端界面: http://localhost:5173
- 后端API: http://localhost:5000
- Neo4j数据库: http://localhost:7474
