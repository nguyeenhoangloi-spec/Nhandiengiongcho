# history.py
# Blueprint cho lịch sử nhận diện

from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from connect import get_connection
from models import PredictionHistory

history_bp = Blueprint("history", __name__)


@history_bp.route("/")
def history():
    """Trang lịch sử nhận diện với phân trang"""
    if not session.get("user_id"):
        flash("Vui lòng đăng nhập để xem lịch sử.", "warning")
        return redirect(url_for("login.login"))
    
    try:
        conn = get_connection()
        user_id_any = session.get("user_id")
        if user_id_any is None:
            flash("Vui lòng đăng nhập để xem lịch sử.", "warning")
            return redirect(url_for("login.login"))
        user_id = int(user_id_any)
        
        # Phân trang
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        
        # Lấy tổng số bản ghi và dữ liệu trang hiện tại
        total_records = PredictionHistory.count_by_user(conn, user_id)
        predictions = PredictionHistory.get_by_user(conn, user_id, limit=per_page, offset=offset)
        
        # Tính tổng số trang
        import math
        total_pages = math.ceil(total_records / per_page) if total_records > 0 else 1
        
        conn.close()
        
        return render_template("history.html", 
                             predictions=predictions,
                             page=page,
                             total_pages=total_pages,
                             total_records=total_records)
    except Exception as e:
        print(f"Error loading history: {e}")
        flash("Không thể tải lịch sử. Vui lòng thử lại.", "error")
        return redirect(url_for("dashboard.dashboard"))


@history_bp.route("/api/recent")
def api_recent():
    """API lấy lịch sử gần đây"""
    if not session.get("user_id"):
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        conn = get_connection()
        user_id_any = session.get("user_id")
        if user_id_any is None:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = int(user_id_any)
        limit = int(request.args.get('limit', 10))
        predictions = PredictionHistory.get_by_user(conn, user_id, limit=limit)
        conn.close()
        
        # Convert datetime to string
        for p in predictions:
            if p['created_at']:
                p['created_at'] = p['created_at'].isoformat()
        
        return jsonify({"predictions": predictions})
    except Exception as e:
        print(f"Error in API: {e}")
        return jsonify({"error": str(e)}), 500
