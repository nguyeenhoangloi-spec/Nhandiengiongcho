# logout.py
# Blueprint đăng xuất

from flask import Blueprint, redirect, url_for, flash, session

logout_bp = Blueprint("logout", __name__)


@logout_bp.route("/")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("home.index"))
