# ==============================================================================
# 鉴泉识珍 — 后端 Docker 镜像
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

# 系统依赖（OpenCV 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir langchain-graphrag

# 应用代码
COPY backend/ ./backend/

# 数据文件（模型和知识图谱不在镜像中，需挂载）
# COPY best1.pt best2.pt best_model.onnx ./backend/
# COPY data/ ./data/

WORKDIR /app/backend
EXPOSE 5001

CMD ["python", "app_new.py"]
