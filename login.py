# login.py
# Blueprint đăng nhập (demo)

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from connect import get_connection
from psycopg2.extras import RealDictCursor
import re

login_bp = Blueprint("login", __name__)


def is_email(username):
    """Kiểm tra xem username có phải là email không"""
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(email_regex, username) is not None


@login_bp.route("/", methods=["GET", "POST"])
def login():
    # Nếu đã đăng nhập, chuyển hướng về dashboard
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard"))
    
    if request.method == "POST":
        username_or_email = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"
        
        # Validation
        if not username_or_email:
            flash("Vui lòng nhập tên đăng nhập hoặc email", "error")
            return render_template("login.html")
        
        if not password:
            flash("Vui lòng nhập mật khẩu", "error")
            return render_template("login.html")
        
        if len(username_or_email) < 3:
            flash("Tên đăng nhập/Email phải có ít nhất 3 ký tự", "error")
            return render_template("login.html")
        
        if len(password) < 6:
            flash("Mật khẩu phải có ít nhất 6 ký tự", "error")
            return render_template("login.html")

        # Truy vấn người dùng từ DB
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Hỗ trợ đăng nhập bằng username hoặc email
                if is_email(username_or_email):
                    cur.execute("SELECT * FROM users WHERE email = %s", (username_or_email,))
                else:
                    cur.execute("SELECT * FROM users WHERE username = %s", (username_or_email,))
                
                user = cur.fetchone()
        except Exception as e:
            print(f"[LOGIN ERROR] Database query failed: {e}")
            flash("Lỗi kết nối cơ sở dữ liệu. Vui lòng thử lại.", "error")
            return render_template("login.html")
        finally:
            conn.close()

        if not user:
            flash("Tài khoản không tồn tại.", "error")
            return render_template("login.html")

        if not check_password_hash(user["password_hash"], password):
            flash("Mật khẩu không đúng.", "error")
            return render_template("login.html")

        # Đăng nhập thành công
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["fullname"] = user.get("fullname", user["username"])
        # Phân quyền: lưu vai trò vào session (mặc định 'user')
        session["role"] = user.get("role", "user")
        # Cờ tiện dụng để kiểm tra quyền admin
        session["is_admin"] = (session.get("role") == "admin")
        
        # Xử lý remember me
        if remember:
            session.permanent = True  # Session sẽ tồn tại lâu hơn
        
        flash(f"Chào mừng trở lại, {user.get('fullname', user['username'])}!", "success")
        
        # Chuyển hướng về trang trước đó nếu có, không thì về dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        # Điều hướng dựa trên vai trò (admin vẫn về dashboard quản trị)
        if session.get("role") == "admin":
            return redirect(url_for("dashboard.dashboard"))
        return redirect(url_for("dashboard.dashboard"))
    
    return render_template("login.html")
