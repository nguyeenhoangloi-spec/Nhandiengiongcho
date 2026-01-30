# register.py
# Blueprint đăng ký (demo)

from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from connect import get_connection
from psycopg2.extras import RealDictCursor
import re

register_bp = Blueprint("register", __name__)


def validate_email(email):
    """Kiểm tra định dạng email"""
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(email_regex, email) is not None


def validate_username(username):
    """Kiểm tra username: 3-20 ký tự, chỉ chứa chữ, số, gạch dưới"""
    username_regex = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(username_regex, username) is not None


def validate_password_strength(password):
    """
    Kiểm tra độ mạnh mật khẩu
    Returns: (is_valid, message)
    """
    if len(password) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự"
    
    # Tùy chọn: thêm kiểm tra mạnh hơn
    # if not re.search(r'[A-Z]', password):
    #     return False, "Mật khẩu phải chứa ít nhất 1 chữ hoa"
    # if not re.search(r'[a-z]', password):
    #     return False, "Mật khẩu phải chứa ít nhất 1 chữ thường"
    # if not re.search(r'[0-9]', password):
    #     return False, "Mật khẩu phải chứa ít nhất 1 số"
    
    return True, ""


@register_bp.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Lấy dữ liệu từ form
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirmPassword", "")
        
        # Validation cơ bản
        if not all([fullname, email, username, password]):
            flash("Vui lòng nhập đầy đủ thông tin", "error")
            return render_template("register.html")
        
        # Kiểm tra họ tên
        if len(fullname) < 2:
            flash("Họ và tên phải có ít nhất 2 ký tự", "error")
            return render_template("register.html")
        
        # Kiểm tra email
        if not validate_email(email):
            flash("Email không hợp lệ", "error")
            return render_template("register.html")
        
        # Kiểm tra username
        if not validate_username(username):
            flash("Tên đăng nhập phải có 3-20 ký tự, chỉ chứa chữ cái, số và dấu gạch dưới", "error")
            return render_template("register.html")
        
        # Kiểm tra mật khẩu
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg, "error")
            return render_template("register.html")
        
        # Kiểm tra xác nhận mật khẩu
        if password != confirm_password:
            flash("Mật khẩu xác nhận không khớp", "error")
            return render_template("register.html")

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Kiểm tra trùng username
                cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
                if cur.fetchone():
                    flash("Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.", "error")
                    return render_template("register.html")
                
                # Kiểm tra trùng email
                cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    flash("Email đã được sử dụng. Vui lòng sử dụng email khác.", "error")
                    return render_template("register.html")

                # Tạo mật khẩu hash
                pwd_hash = generate_password_hash(password)
                
                # Tạo người dùng mới
                cur.execute(
                    "INSERT INTO users (username, password_hash, email, fullname, created_at) VALUES (%s, %s, %s, %s, NOW())",
                    (username, pwd_hash, email, fullname),
                )
                conn.commit()
                
                flash(f"Chúc mừng {fullname}! Tài khoản của bạn đã được tạo thành công. Vui lòng đăng nhập.", "success")
                return redirect(url_for("login.login"))
                
        except Exception as e:
            conn.rollback()
            print(f"[REGISTER ERROR] {e}")
            flash("Không thể tạo tài khoản. Vui lòng thử lại.", "error")
        finally:
            conn.close()
            
    return render_template("register.html")
