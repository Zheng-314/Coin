# ==============================================================================
# Flask应用主入口 - 重构版
# ==============================================================================
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 加载环境变量（必须在配置之前）
from dotenv import load_dotenv
load_dotenv()

# 配置全局日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('app')

# 创建Flask应用
app = Flask(__name__)
_secret = os.getenv('SECRET_KEY')
if not _secret:
    raise RuntimeError("SECRET_KEY 环境变量未设置，请检查 backend/.env 文件")
app.config['SECRET_KEY'] = _secret
app.config['JSON_AS_ASCII'] = False

# CORS：开发环境允许本地前端，生产环境通过环境变量指定
_allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174').split(',')
CORS(app, supports_credentials=True, origins=_allowed_origins)

# Rate limiting：基于IP限流，防止API滥用
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per minute", "50 per second"],
    storage_uri="memory://",
)

# 延迟导入路由，避免启动时的导入错误
def register_blueprints():
    """
    注册所有可用的 Flask 蓝图到应用

    该函数负责初始化路由系统，并将各个功能模块的蓝图注册到 Flask 应用中。
    包括认证、知识图谱构建、问答、预测、用户行为和估值等模块的路由。

    Raises:
        ImportError: 当路由模块导入失败时抛出
    """
    # 导入路由模块
    from routes import (
        auth_bp,
        artifacts_bp,
        qa_bp,
        predict_bp,
        user_actions_bp,
        valuation_bp,
        report_bp
    )

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(artifacts_bp)
    app.register_blueprint(qa_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(user_actions_bp)
    app.register_blueprint(valuation_bp)
    app.register_blueprint(report_bp)

# 健康检查端点（不限流）
@app.route('/api/health', methods=['GET'])
@limiter.exempt
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'message': '服务正常运行'
    })

# 根路由
@app.route('/', methods=['GET'])
@limiter.exempt
def index():
    """根路由"""
    return jsonify({
        'name': '钱币智能鉴定系统',
        'version': '2.0',
        'endpoints': {
            'auth': '/api/users/*',
            'artifacts': '/api/artifacts/*',
            'qa': '/api/ask',
            'predict': '/predict',
            'user_actions': '/api/user-actions/*',
            'valuation': '/api/valuation'
        }
    })

# 注册所有蓝图（在模块级调用，确保 flask run / gunicorn 等部署方式也能注册路由）
register_blueprints()

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("钱币智能鉴定系统 - 后端服务")
    logger.info("=" * 60)
    logger.info("访问地址: http://0.0.0.0:5001")
    logger.info("=" * 60)
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    logger.info(f"启动模式: {'DEBUG' if debug_mode else 'PRODUCTION'}")
    app.run(host="0.0.0.0", port=5001, debug=debug_mode)
