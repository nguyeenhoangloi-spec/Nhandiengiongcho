# analytics.py
# Blueprint cho thống kê nhận diện
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from connect import get_connection
from models import PredictionHistory

stats_bp = Blueprint("statistics", __name__)


@stats_bp.route("/")
def statistics():
    """Trang thống kê"""
    user_id_any = session.get("user_id")
    if user_id_any is None:
        flash("Vui lòng đăng nhập để xem thống kê.", "warning")
        return redirect(url_for("login.login"))

    try:
        conn = get_connection()
        user_id = int(user_id_any)
        stats = PredictionHistory.get_stats(conn, user_id)
        recent_predictions = PredictionHistory.get_by_user(conn, user_id, limit=10)
        conn.close()

        return render_template(
            "statistics.html", stats=stats, recent_predictions=recent_predictions
        )
    except Exception as e:
        print(f"Error loading statistics: {e}")
        flash("Không thể tải thống kê. Vui lòng thử lại.", "error")
        return redirect(url_for("dashboard.dashboard"))


@stats_bp.route("/api/stats")
def api_stats():
    """API lấy thống kê"""
    user_id_any = session.get("user_id")
    if user_id_any is None:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        conn = get_connection()
        user_id = int(user_id_any)
        stats = PredictionHistory.get_stats(conn, user_id)
        conn.close()

        return jsonify(stats)
    except Exception as e:
        print(f"Error in API: {e}")
        return jsonify({"error": str(e)}), 500
