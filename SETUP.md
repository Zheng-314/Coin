# 环境配置指南 — 鉴泉识珍

> 省级大创项目 · 古钱币智能鉴定与知识图谱系统

---

## 一、项目概述

| 层级 | 技术 | 版本要求 |
|------|------|----------|
| 前端 | Vue 3 + Element Plus + Vite | Node.js ≥18 |
| 后端 | Flask | Python 3.11 |
| 检测模型 | YOLOv8 (Ultralytics) | — |
| 分类模型 | ONNX Runtime | — |
| 大模型 | DeepSeek Chat / Qwen-VL | API 调用 |
| 图数据库 | Neo4j (可选) | 5.x |
| 向量库 | ChromaDB | 1.x |
| 关系库 | SQLite | — |

---

## 二、快速启动（Windows / macOS / Linux 通用）

### 前置条件

```bash
# 1. 确认 Python 3.11 已安装
python --version  # 应为 3.11.x

# 2. 确认 Node.js ≥18 已安装
node --version
```

### 步骤1：克隆项目

```bash
git clone git@github.com:Zheng-314/-.git
cd code
```

### 步骤2：安装后端依赖

```bash
# 创建虚拟环境（只需执行一次）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 额外安装 GraphRAG（如果 requirements.txt 未包含）
pip install langchain-graphrag
```

### 步骤3：配置环境变量

```bash
# 复制示例配置
cp backend/.env.example backend/.env

# 编辑 backend/.env，填入你申请到的 API Key：
#   - OPENAI_API_KEY: DeepSeek API (https://platform.deepseek.com)
#   - QWEN_API_KEY:   阿里云百炼 (https://dashscope.aliyun.com)
#   - TAVILY_API_KEY: Tavily 搜索 (https://tavily.com)
#   - NEO4J_*:        Neo4j 数据库（如无则跳过，系统自动降级到 SQLite）
```

### 步骤4：启动后端

```bash
cd backend
python app_new.py
```

后端启动后自动加载模型（首次需15-30秒），输出：
```
访问地址: http://0.0.0.0:5001
ONNX 输入名称: ['input1', 'input2']
已加载 92 个分类名称
```

健康检查：
```bash
curl http://127.0.0.1:5001/api/health
# {"message": "服务正常运行", "status": "ok"}
```

### 步骤5：启动前端

开一个新终端：

```bash
cd frontend
cp .env.example .env   # 如尚未配置

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

访问 `http://localhost:5173`

---

## 三、需要申请的 API Key

| 服务 | 用途 | 获取地址 | 费用 |
|------|------|----------|------|
| DeepSeek | 大模型对话 | https://platform.deepseek.com | 按量付费（极低） |
| 硅基流动 | Embedding 向量化 | https://siliconflow.cn | 免费额度 |
| 阿里云百炼 | Qwen-VL 视觉识别 | https://dashscope.aliyun.com | 免费额度 |
| Tavily | 联网搜索 | https://tavily.com | 免费额度（每月1000次） |
| Neo4j (可选) | 知识图谱存储 | https://neo4j.com | 社区版免费 |

---

## 四、目录结构

```
code/
├── backend/                  # Flask 后端
│   ├── app_new.py           # 入口
│   ├── config.py            # 配置（路径、API Key）
│   ├── .env                 # 环境变量（不上传 Git）
│   ├── .env.example         # 环境变量模板
│   ├── routes/              # API 路由
│   │   ├── auth.py          #   用户登录/注册
│   │   ├── artifacts.py     #   钱币数据库 CRUD
│   │   ├── qa.py            #   智能问答
│   │   ├── predict.py       #   图片鉴定
│   │   ├── valuation.py     #   钱币估值
│   │   ├── report.py        #   PDF报告
│   │   └── user_actions.py  #   收藏/聊天记录
│   ├── services/            # 业务逻辑
│   │   ├── rag_service.py   #   RAG 问答引擎
│   │   ├── yolo_service.py  #   YOLO 检测
│   │   └── onnx_service.py  #   ONNX 分类
│   ├── models/              # 模型加载
│   ├── utils/               # 工具函数
│   └── instance/            # SQLite 数据库
│       ├── item.db          #   钱币数据 (500条)
│       ├── user.db          #   用户数据
│       └── classification.json  # 分类映射
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── router/          # 路由配置
│   │   └── config/          # API 配置
│   └── .env                 # 前端环境变量
├── data/                     # 知识图谱数据
│   └── artifacts/           # GraphRAG 构建产物
├── docs/                     # 项目文档
│   ├── 产品文档.md
│   ├── 技术文档.md
│   └── 钱币分类体系.md
├── requirements.txt          # Python 依赖
└── README.md                 # 项目说明
```

---

## 五、常见问题

### Q: 启动后端报 `No module named 'langchain_graphrag'`
```bash
pip install langchain-graphrag
```
如安装失败，系统会自动降级到 SQLite 关键词检索模式，不影响基本使用。

### Q: 问答功能返回"检索未命中"
当前 `item.db` 包含 500 条钱币记录，覆盖度有限。建议：
- 使用更具体的关键词（如"光绪元宝"、"四川铜币"）
- 切换搜索模式（本地 / 全局 / 联网）

### Q: Neo4j 是否必须装？
不是必须的。未安装 Neo4j 时，知识图谱页面会自动降级到 SQLite 简化版图。
但 **GraphRAG 全局搜索需要 Neo4j**。

### Q: 模型文件在哪里下载？
模型文件（`best1.pt`, `best2.pt`, `best_model.onnx`）不在 Git 仓库中（被 .gitignore 忽略）。
请通过项目内部渠道获取。

### Q: macOS 上用不了 PDF 导出
系统会自动搜索系统中文字体。如果找不到，PDF 中的中文会显示为空白。
可以手动安装 `wqy-microhei` 字体：`brew install wqy-microhei-font`
