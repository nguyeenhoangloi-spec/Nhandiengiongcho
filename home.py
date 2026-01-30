# home.py
# Blueprint trang chủ

from flask import Blueprint, render_template

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def index():
    from flask import session, redirect, url_for
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard"))
    return render_template("home.html")
