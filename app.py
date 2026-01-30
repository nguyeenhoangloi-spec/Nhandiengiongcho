from flask import Flask, render_template, jsonify, session
import os

# Import các Blueprint đã định nghĩa trong các module
from home import home_bp
from login import login_bp
from register import register_bp
from dashboard import dashboard_bp
from upload import predict_bp
from logout import logout_bp
from history import history_bp
from analytics import stats_bp
from settings import settings_bp
from users import users_bp
from account import account_bp


app = Flask(__name__)
app.secret_key = "change-this-secret-key"

# Cấu hình thư mục upload và định dạng cho phép
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg"}

# VietQR (EMVCo) config (có thể override bằng biến môi trường)
# Lưu ý: VIETQR_BANK_BIN là BIN NAPAS 6 số của ngân hàng (bắt buộc để VietQR scan ra đúng).
app.config["VIETQR_BANK_NAME"] = "MB Bank"
app.config["VIETQR_BANK_BIN"] = "970422"
app.config["VIETQR_ACCOUNT_NUMBER"] = "9244424440709"
app.config["VIETQR_ACCOUNT_NAME"] = "NGUYEN HOANG LOI"
app.config["VIETQR_MERCHANT_NAME"] = "DOG AI APP"
app.config["VIETQR_MERCHANT_CITY"] = "HANOI"

# Đăng ký các Blueprint với tiền tố URL
app.register_blueprint(home_bp, url_prefix="")
app.register_blueprint(login_bp, url_prefix="/login")
app.register_blueprint(register_bp, url_prefix="/register")
app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
app.register_blueprint(predict_bp, url_prefix="/predict")
app.register_blueprint(logout_bp, url_prefix="/logout")
app.register_blueprint(history_bp, url_prefix="/history")
app.register_blueprint(stats_bp, url_prefix="/statistics")
app.register_blueprint(settings_bp, url_prefix="/settings")
app.register_blueprint(account_bp, url_prefix="/account")
app.register_blueprint(users_bp, url_prefix="/users")


# Context processor để inject theme vào tất cả templates
@app.context_processor
def inject_ui_prefs():
    """Inject theme cho tất cả templates"""
    current_plan = None
    user_id_raw = session.get("user_id")
    if user_id_raw is not None:
        try:
            from connect import get_connection
            from models import UserQuota

            user_id = int(user_id_raw)
            conn = get_connection()
            try:
                quota = UserQuota.get_or_create(conn, user_id)
                current_plan = (quota or {}).get("plan") or "free"
            finally:
                conn.close()
        except Exception:
            current_plan = None

    return {
        "ui_theme": session.get("theme", "light"),
        "current_plan": current_plan,
    }


# Error handlers
@app.errorhandler(403)
def handle_forbidden(e):
    return render_template("error.html", code=403, message="Bạn không có quyền truy cập chức năng này."), 403


@app.errorhandler(404)
def handle_not_found(e):
    return render_template("error.html", code=404, message="Không tìm thấy trang hoặc tài nguyên yêu cầu."), 404


@app.errorhandler(500)
def handle_server_error(e):
    return render_template("error.html", code=500, message="Lỗi hệ thống. Vui lòng thử lại sau."), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    url = "http://127.0.0.1:5000"
    print(f"\nTruy cập ứng dụng tại: {url}\n")
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=5000)
    except Exception:
        app.run(debug=True)
