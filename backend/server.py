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

# ------------------------------------------------------------------------------
# 同源伺服 Web 前端：若项目根存在 web/（frontend 构建产物），则由 Flask 直接提供
# 优点：一个端口同时服务页面与 API，无需 CORS，无需额外静态托管
# ------------------------------------------------------------------------------
from flask import send_from_directory, jsonify  # noqa: E402

WEB_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'web'))

if os.path.isfile(os.path.join(WEB_DIR, 'index.html')):
    @app.route('/')
    @app.route('/<path:subpath>')
    def _spa(subpath=''):
        # API 前缀不走静态兑底，保持 JSON 404 语义
        if subpath.startswith(('api/', 'uploads/')):
            return jsonify({'error': 'not found'}), 404
        full = os.path.join(WEB_DIR, subpath)
        if subpath and os.path.isfile(full):
            return send_from_directory(WEB_DIR, subpath)
        # SPA history 路由兑底：任意前端路径返回 index.html
        return send_from_directory(WEB_DIR, 'index.html')

    import logging as _logging
    _logging.getLogger('server').info(f"同源前端已启用: {WEB_DIR}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=False)
