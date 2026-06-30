#!/bin/bash
# 鉴泉识珍 — 一键环境配置脚本
set -e

echo "=== 鉴泉识珍 环境配置 ==="

# Python 虚拟环境
if [ ! -d "venv" ]; then
    echo "[1/4] 创建 Python 虚拟环境..."
    python3.11 -m venv venv
fi

echo "[2/4] 安装 Python 依赖..."
source venv/bin/activate
pip install -r requirements.txt -q
pip install -e ".[dev]" -q

echo "[3/4] 安装前端依赖..."
cd frontend && npm ci --silent && cd ..

echo "[4/4] 配置环境变量..."
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo "  [!] 请编辑 backend/.env 填入你的 API Key"
fi

echo ""
echo "=== 配置完成 ==="
echo "启动后端: make run-backend"
echo "启动前端: make run-frontend"
echo "运行测试: make test"
