# ==============================================================================
# Flask应用主入口 - 重构版
# ==============================================================================
import os
from flask import Flask, jsonify
from flask_cors import CORS

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_long_and_super_secret_random_string_123!'
app.config['JSON_AS_ASCII'] = False

# 启用CORS（允许所有来源）
CORS(app, supports_credentials=True, origins="*", resources={r"/*": {"origins": "*"}})

# 延迟导入路由，避免启动时的导入错误
def register_blueprints():
    from routes import (
        auth_bp,
        artifacts_bp,
        qa_bp,
        predict_bp,
        user_actions_bp,
        valuation_bp
    )
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(artifacts_bp)
    app.register_blueprint(qa_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(user_actions_bp)
    app.register_blueprint(valuation_bp)

# 健康检查端点
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'message': '服务正常运行'
    })

# 根路由
@app.route('/', methods=['GET'])
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

if __name__ == '__main__':
    print("=" * 60)
    print("钱币智能鉴定系统 - 后端服务")
    print("=" * 60)
    print("访问地址: http://0.0.0.0:5001")
    print("=" * 60)
    # 设置 DEBUG 环境变量，启用详细错误信息
    os.environ['FLASK_DEBUG'] = '1'
    # 注册路由
    register_blueprints()
    app.run(host="0.0.0.0", port=5001, debug=True)