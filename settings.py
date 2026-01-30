# settings.py
# Blueprint cho cài đặt người dùng

from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from connect import get_connection
from models import UserSettings
import os

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/", methods=["GET", "POST"])
def settings():
    """Trang cài đặt"""
    if not session.get("user_id"):
        flash("Vui lòng đăng nhập để truy cập cài đặt.", "warning")
        return redirect(url_for("login.login"))
    
    user_id_any = session.get("user_id")
    if user_id_any is None:
        flash("Vui lòng đăng nhập để truy cập cài đặt.", "warning")
        return redirect(url_for("login.login"))
    try:
        user_id = int(user_id_any)
    except Exception:
        flash("Phiên đăng nhập không hợp lệ.", "error")
        return redirect(url_for("login.login"))
    
    if request.method == "POST":
        try:
            conn = get_connection()
            theme = request.form.get('theme', 'light').strip()
            
            # Validate theme
            if theme not in ('light', 'dark', 'auto'):
                theme = 'light'
            
            settings_data = {
                'theme': theme,
                'language': request.form.get('language', 'vi'),
                'notifications': request.form.get('notifications') == 'on',
                'email_notifications': request.form.get('email_notifications') == 'on'
            }
            
            UserSettings.update(conn, user_id, settings_data)
            conn.close()
            
            # Lưu theme vào session để apply ngay
            session['theme'] = theme
            
            flash("Cài đặt đã được lưu thành công!", "success")
            return redirect(url_for("settings.settings"))
        except Exception as e:
            print(f"Error saving settings: {e}")
            flash(f"Không thể lưu cài đặt: {e}", "error")
    
    try:
        conn = get_connection()
        user_settings = UserSettings.get_or_create(conn, user_id)
        conn.close()
        
        return render_template("settings.html", settings=user_settings)
    except Exception as e:
        print(f"Error loading settings: {e}")
        flash(f"Không thể tải cài đặt: {e}", "error")
        return redirect(url_for("dashboard.dashboard"))


@settings_bp.route("/clear-history", methods=["POST"])
def clear_history():
    """Xóa toàn bộ lịch sử nhận diện của user hiện tại."""
    if not session.get("user_id"):
        flash("Vui lòng đăng nhập để thực hiện thao tác này.", "warning")
        return redirect(url_for("login.login"))

    user_id_any = session.get("user_id")
    if user_id_any is None:
        flash("Vui lòng đăng nhập để thực hiện thao tác này.", "warning")
        return redirect(url_for("login.login"))
    try:
        user_id = int(user_id_any)
    except Exception:
        flash("Phiên đăng nhập không hợp lệ.", "error")
        return redirect(url_for("login.login"))

    conn = None
    try:
        conn = get_connection()
        # Lấy danh sách file để xóa (nếu có)
        image_paths: list[str] = []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT image_path FROM prediction_history WHERE user_id = %s",
                    (user_id,),
                )
                rows = cur.fetchall() or []
                image_paths = [r[0] for r in rows if r and r[0]]
        except Exception:
            image_paths = []

        with conn.cursor() as cur:
            cur.execute("DELETE FROM prediction_history WHERE user_id = %s", (user_id,))
        conn.commit()

        # Xóa file ảnh trong static/uploads nếu trỏ đúng thư mục (an toàn)
        upload_root = os.path.abspath(os.path.join(os.getcwd(), "static", "uploads"))
        deleted_files = 0
        for p in image_paths:
            try:
                # normalize path; allow both relative and absolute
                abs_path = os.path.abspath(os.path.join(os.getcwd(), p)) if not os.path.isabs(p) else os.path.abspath(p)
                if abs_path.startswith(upload_root) and os.path.exists(abs_path):
                    os.remove(abs_path)
                    deleted_files += 1
            except Exception:
                pass

        flash(f"Đã xóa lịch sử nhận diện. (Đã xóa {deleted_files} ảnh lưu trữ)", "success")
        return redirect(url_for("settings.settings"))
    except Exception as e:
        print(f"[SETTINGS] clear history error: {e}")
        flash("Không thể xóa lịch sử. Vui lòng thử lại.", "error")
        return redirect(url_for("settings.settings"))
    finally:
        if conn:
            conn.close()
