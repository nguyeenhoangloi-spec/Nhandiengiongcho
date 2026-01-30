# account.py
# Blueprint cho các chức năng tài khoản: quên mật khẩu (placeholder)

from flask import Blueprint, render_template, request, flash, redirect, url_for

account_bp = Blueprint("account", __name__)


@account_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    """Trang quên mật khẩu (placeholder logic)"""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Vui lòng nhập email", "error")
            return render_template("forgot_password.html")
        # TODO: Gửi email reset password. Hiện tại hiển thị thông báo.
        flash("Nếu email tồn tại, chúng tôi đã gửi hướng dẫn đặt lại mật khẩu.", "success")
        return redirect(url_for("login.login"))
    return render_template("forgot_password.html")
