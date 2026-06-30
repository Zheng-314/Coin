# 贡献指南

感谢你对鉴泉识珍项目的关注！

## 开发环境搭建

```bash
# 1. 克隆项目
git clone git@github.com:Zheng-314/Coin.git
cd Coin

# 2. 安装依赖
make install-dev

# 3. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入你的 API Key

# 4. 启动开发服务器
make run-backend   # 终端1
make run-frontend  # 终端2
```

## 代码规范

### Python

```bash
# 格式化
make format

# 检查
make lint
```

- 使用 120 字符行宽
- 遵循 PEP 8
- 新函数必须添加类型标注
- 公共函数必须添加 docstring

### Vue/JavaScript

```bash
cd frontend
npm run lint
npm run format
```

- 使用 Composition API（`<script setup>`）
- 组件超过 300 行需拆分
- 使用 `useXxx` 命名 composables

## 提交规范

```
<类型>: <描述>

类型：
  feat      - 新功能
  fix       - 修复 bug
  docs      - 文档更新
  refactor  - 代码重构
  test      - 添加测试
  chore     - 构建/工具变更

示例：
  feat: 添加批量鉴定功能
  fix: 修复蓝图注册在生产环境 404 的问题
```

## 运行测试

```bash
make test       # 后端测试
make test-cov   # 含覆盖率报告
```

## 项目结构

```
.
├── backend/           # Flask 后端
│   ├── routes/        #   路由（按功能模块）
│   ├── services/      #   业务逻辑
│   ├── models/        #   模型加载
│   ├── utils/         #   工具函数
│   └── tests/         #   测试
├── frontend/          # Vue 3 前端
├── training/          # 训练代码和数据
├── data/              # 数据集
└── docs/              # 文档
    └── adr/           #   架构决策记录
```
