# ==============================================================================
# 平台部署入口 — Hugging Face Spaces / Render 等直接运行此文件
# 与 app_new.py 的区别：蓝图注册和模型加载不依赖 __main__，且端口读环境变量
# 本地用法：python server.py   （PORT 缺省 5001）
# 平台用法：PORT=7860 python server.py
# gunicorn：gunicorn -w 1 -b 0.0.0.0:7860 server:app
# ==============================================================================
import os

from app_new import app, register_blueprints  # noqa: F401 — app 供 gunicorn 引用

# 注册全部路由蓝图（必须在导入 app_new 之后，避免循环导入）
register_blueprints()

# 加载 YOLO + ONNX 模型（启动时完成，首请求即可推理）
from models.model_loader import init_models  # noqa: E402
init_models()

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=False)
