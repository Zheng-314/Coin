.PHONY: help install install-dev test lint format run-backend run-frontend clean docker-build docker-up

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# 安装
# ============================================================================
install: ## 安装生产依赖
	pip install -r requirements.txt
	pip install langchain-graphrag
	cd frontend && npm ci

install-dev: install ## 安装开发依赖
	pip install -e ".[dev]"

# ============================================================================
# 测试和代码质量
# ============================================================================
test: ## 运行后端测试
	pytest backend/tests/ -v

test-cov: ## 运行测试并输出覆盖率
	pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term

lint: ## 代码检查
	ruff check backend/
	cd frontend && npm run lint

format: ## 代码格式化
	ruff format backend/
	cd frontend && npm run format

# ============================================================================
# 运行
# ============================================================================
run-backend: ## 启动后端开发服务器
	cd backend && python app_new.py

run-frontend: ## 启动前端开发服务器
	cd frontend && npm run dev

# ============================================================================
# Docker
# ============================================================================
docker-build: ## 构建 Docker 镜像
	docker-compose build

docker-up: ## 启动 Docker 服务
	docker-compose up -d

docker-down: ## 停止 Docker 服务
	docker-compose down

# ============================================================================
# 清理
# ============================================================================
clean: ## 清理缓存和构建产物
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf frontend/dist/
	rm -rf .pytest_cache/
