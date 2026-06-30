# ==============================================================================
# 鉴定报告导出 + 批量鉴定 + 历史行情
# ==============================================================================
import io
import json
import logging
import time
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file
from fpdf import FPDF

from utils.database import item_db, user_db
from utils.decorators import token_required

logger = logging.getLogger('routes.report')

report_bp = Blueprint('report', __name__)


# ==============================================================================
# 1. 鉴定报告导出
# ==============================================================================

class CoinReportPDF(FPDF):
    """钱币鉴定报告PDF生成器"""

    def header(self):
        self.set_font('msyh', 'B', 18)
        self.cell(0, 12, '鉴泉识珍 - 钱币鉴定报告', 0, 1, 'C')
        self.set_font('msyh', '', 10)
        self.cell(0, 8, f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
        self.ln(5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('msyh', '', 8)
        self.cell(0, 10, f'鉴泉识珍 - 古钱币智能鉴定平台 | 第 {self.page_no()} 页', 0, 0, 'C')

    def add_section(self, title, content):
        self.set_font('msyh', 'B', 13)
        self.set_fill_color(245, 240, 230)
        self.cell(0, 10, title, 0, 1, 'L', fill=True)
        self.ln(3)
        self.set_font('msyh', '', 11)
        if isinstance(content, list):
            for item in content:
                self.multi_cell(0, 7, f'• {item}')
                self.ln(1)
        else:
            self.multi_cell(0, 7, content)
        self.ln(5)


def get_font_path():
    """获取中文字体路径，按优先级跨平台搜索"""
    import os
    import platform
    font_paths = [
        # Windows
        'C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/simsun.ttc',
        'C:/Windows/Fonts/simhei.ttf',
        # Linux
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        # macOS
        '/System/Library/Fonts/PingFang.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    # 最后尝试系统搜索
    try:
        import subprocess
        if platform.system() == 'Linux':
            result = subprocess.run(['fc-list', ':lang=zh', '-f', '%{file}\n'],
                                    capture_output=True, text=True, timeout=5)
            if result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
    except Exception:
        pass
    return None


@report_bp.route('/api/report/identify', methods=['POST'])
def generate_identify_report():
    """生成鉴定报告PDF"""
    data = request.get_json() or {}

    coin_name = data.get('coinName', '未知钱币')
    confidence = data.get('confidence', 0)
    top3 = data.get('top3', [])
    image_base64 = data.get('imageBase64')  # 可选

    try:
        pdf = CoinReportPDF()
        font_path = get_font_path()
        if font_path:
            pdf.add_font('msyh', '', font_path, uni=True)
            pdf.add_font('msyh', 'B', font_path, uni=True)
        else:
            pdf.add_font('msyh', '', 'Helvetica')
            pdf.add_font('msyh', 'B', 'Helvetica')

        pdf.add_page()

        # 鉴定结果
        pdf.add_section('鉴定结果', f'钱币分类: {coin_name}')
        pdf.add_section('置信度', f'{confidence:.1f}%')

        # Top-3候选
        if top3:
            lines = []
            for i, item in enumerate(top3, 1):
                name = item.get('name', '未知')
                conf = item.get('confidence', 0)
                lines.append(f'{i}. {name} (置信度: {conf:.1f}%)')
            pdf.add_section('候选分类', lines)

        # 鉴定说明
        pdf.add_section('鉴定说明', [
            '本报告由AI系统自动生成，仅供参考。',
            '鉴定结果基于YOLOv8目标检测 + ONNX双图配对分类模型。',
            '如需权威鉴定，请联系专业鉴定机构（如PCGS、NGC、GBCA等）。',
        ])

        # 免责声明
        pdf.add_section('免责声明', [
            '本报告不构成任何投资建议。',
            '钱币市场波动较大，价格仅供参考。',
            '最终鉴定结果以专业机构为准。',
        ])

        # 输出PDF
        pdf_bytes = pdf.output()
        return send_file(
            io.BytesIO(bytes(pdf_bytes)),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'鉴定报告_{coin_name}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )

    except Exception as e:
        logger.error(f"生成PDF报告失败: {e}", exc_info=True)
        return jsonify({'error': f'生成报告失败: {str(e)}'}), 500


@report_bp.route('/api/report/valuation', methods=['POST'])
def generate_valuation_report():
    """生成估价报告PDF"""
    data = request.get_json() or {}

    coin_name = data.get('coinName', '未知钱币')
    grade = data.get('grade', '未知品相')
    valuation_text = data.get('valuationText', '')

    try:
        pdf = CoinReportPDF()
        font_path = get_font_path()
        if font_path:
            pdf.add_font('msyh', '', font_path, uni=True)
            pdf.add_font('msyh', 'B', font_path, uni=True)

        pdf.add_page()

        pdf.add_section('钱币信息', f'名称: {coin_name}\n品相: {grade}')
        pdf.add_section('估价报告', valuation_text)
        pdf.add_section('免责声明', [
            '本估价基于AI分析和网络数据，仅供参考。',
            '实际交易价格受市场供需、品相、稀缺性等因素影响。',
            '建议以专业鉴定机构和拍卖行估价为准。',
        ])

        pdf_bytes = pdf.output()
        return send_file(
            io.BytesIO(bytes(pdf_bytes)),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'估价报告_{coin_name}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )

    except Exception as e:
        logger.error(f"生成估价PDF失败: {e}", exc_info=True)
        return jsonify({'error': f'生成报告失败: {str(e)}'}), 500


# ==============================================================================
# 2. 批量鉴定
# ==============================================================================

@report_bp.route('/api/predict/batch', methods=['POST'])
def batch_predict():
    """批量鉴定：接收多组图片，返回所有鉴定结果"""
    from routes.predict import run_optional_yolo_pipeline, load_class_names, CLASS_NAMES
    from services.yolo_service import detect_yolo
    from services.onnx_service import run_onnx_pair_inference
    from models.model_loader import ensure_onnx_session_ready
    import cv2
    import numpy as np

    ok, errs = ensure_onnx_session_ready()
    if not ok:
        return jsonify({'error': '模型未就绪', 'details': errs}), 503

    load_class_names()

    # 获取所有图片组
    groups = {}
    for key in request.files:
        if key.startswith('image1_') or key.startswith('image2_'):
            parts = key.split('_')
            if len(parts) == 2:
                idx = parts[1]
                if idx not in groups:
                    groups[idx] = {}
                groups[idx][parts[0]] = request.files[key]

    if not groups:
        return jsonify({'error': '未收到图片'}), 400

    results = []
    for idx in sorted(groups.keys()):
        group = groups[idx]
        f1 = group.get('image1')
        f2 = group.get('image2')

        if not f1 or not f2:
            results.append({'index': int(idx), 'error': '缺少正面或反面图片'})
            continue

        try:
            img1 = cv2.imdecode(np.frombuffer(f1.read(), np.uint8), cv2.IMREAD_COLOR)
            img2 = cv2.imdecode(np.frombuffer(f2.read(), np.uint8), cv2.IMREAD_COLOR)

            if img1 is None or img2 is None:
                results.append({'index': int(idx), 'error': '图片解码失败'})
                continue

            # YOLO检测
            det1 = detect_yolo(img1)
            det2 = detect_yolo(img2)

            if not (det1 and len(det1)) and not (det2 and len(det2)):
                results.append({'index': int(idx), 'error': '未检测到钱币'})
                continue

            # 预处理
            proc1 = run_optional_yolo_pipeline(img1)
            proc2 = run_optional_yolo_pipeline(img2)

            from services.inference_service import run_multi_candidate_inference, extract_top_k

            # 4候选推理
            best_probs, best_conf, _ = run_multi_candidate_inference(
                images_a=[proc1, img1],
                images_b=[proc2, img2],
                onnx_infer_fn=run_onnx_pair_inference,
            )

            if best_probs is None:
                results.append({'index': int(idx), 'error': '推理失败'})
                continue

            top3 = extract_top_k(best_probs, CLASS_NAMES, k=3)

            results.append({
                'index': int(idx),
                'success': True,
                'top1': top3[0] if top3 else None,
                'top3': top3
            })

        except Exception as e:
            logger.error(f"批量鉴定第{idx}组失败: {e}")
            results.append({'index': int(idx), 'error': str(e)})

    return jsonify({'results': results, 'total': len(results)})


# ==============================================================================
# 3. 历史行情追踪
# ==============================================================================

def init_price_history_table():
    """初始化价格历史表"""
    with user_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                coin_name TEXT NOT NULL,
                grade TEXT,
                price REAL,
                source TEXT,
                note TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')


# 启动时初始化表
init_price_history_table()


@report_bp.route('/api/price-history', methods=['POST'])
@token_required
def add_price_record(current_user):
    """添加价格记录"""
    data = request.get_json() or {}
    coin_name = data.get('coinName')
    grade = data.get('grade', '')
    price = data.get('price')
    source = data.get('source', '手动记录')
    note = data.get('note', '')

    if not coin_name:
        return jsonify({'error': '钱币名称不能为空'}), 400

    username = current_user['username']

    try:
        with user_db() as conn:
            conn.execute(
                'INSERT INTO price_history (username, coin_name, grade, price, source, note) VALUES (?, ?, ?, ?, ?, ?)',
                (username, coin_name, grade, price, source, note)
            )
        return jsonify({'message': '记录成功'}), 201
    except Exception as e:
        logger.error(f"添加价格记录失败: {e}")
        return jsonify({'error': '记录失败'}), 500


@report_bp.route('/api/price-history', methods=['GET'])
@token_required
def get_price_history(current_user):
    """获取价格历史"""
    username = current_user['username']

    coin_name = request.args.get('coinName', '')

    try:
        with user_db() as conn:
            if coin_name:
                rows = conn.execute(
                    'SELECT * FROM price_history WHERE username = ? AND coin_name = ? ORDER BY timestamp DESC',
                    (username, coin_name)
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM price_history WHERE username = ? ORDER BY timestamp DESC LIMIT 50',
                    (username,)
                ).fetchall()

        records = []
        for row in rows:
            records.append({
                'id': row['id'],
                'coinName': row['coin_name'],
                'grade': row['grade'],
                'price': row['price'],
                'source': row['source'],
                'note': row['note'],
                'timestamp': row['timestamp']
            })

        return jsonify(records)
    except Exception as e:
        logger.error(f"获取价格历史失败: {e}")
        return jsonify({'error': '查询失败'}), 500


@report_bp.route('/api/price-history/<int:record_id>', methods=['DELETE'])
@token_required
def delete_price_record(current_user, record_id):
    """删除价格记录"""
    username = current_user['username']

    try:
        with user_db() as conn:
            conn.execute(
                'DELETE FROM price_history WHERE id = ? AND username = ?',
                (record_id, username)
            )
        return jsonify({'message': '删除成功'})
    except Exception as e:
        logger.error(f"删除价格记录失败: {e}")
        return jsonify({'error': '删除失败'}), 500
