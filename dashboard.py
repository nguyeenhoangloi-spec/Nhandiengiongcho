# dashboard.py
# Blueprint trang quản trị

from flask import Blueprint, render_template, session, redirect, url_for, flash

from connect import get_connection
from models import PredictionHistory

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def dashboard():
    if not session.get("user_id"):
        flash("Vui lòng đăng nhập để truy cập dashboard.", "warning")
        return redirect(url_for("login.login"))

    user_id_raw = session.get("user_id")
    try:
        user_id = int(user_id_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("login.login"))
    conn = None
    try:
        conn = get_connection()
        recent_predictions = PredictionHistory.get_by_user(conn, user_id, limit=6, offset=0)
        return render_template("dashboard.html", recent_predictions=recent_predictions)
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        flash("Không thể tải dashboard. Vui lòng thử lại.", "error")
        return render_template("dashboard.html", recent_predictions=[])
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
