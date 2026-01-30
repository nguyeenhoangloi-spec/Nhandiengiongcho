# users.py
# Blueprint quản trị người dùng (admin-only)

from flask import Blueprint, render_template, session, redirect, url_for, flash, abort, request
from connect import get_connection
from models import init_database
from models import PaymentOrder
from models import UserQuota
from psycopg2.extras import RealDictCursor

users_bp = Blueprint("users", __name__)


def require_admin():
    if not session.get("user_id"):
        flash("Vui lòng đăng nhập để truy cập chức năng này.", "warning")
        return False
    if session.get("role") != "admin":
        abort(403)
    return True


@users_bp.route("/")
def list_users():
    """Danh sách người dùng (chỉ admin)"""
    if not require_admin():
        return redirect(url_for("login.login"))

    conn = None
    users = []
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT u.id, u.username, u.fullname, u.email, u.role, u.is_active, u.created_at,
                       COALESCE(q.plan, 'free') AS plan
                FROM users u
                LEFT JOIN user_quota q ON q.user_id = u.id
                ORDER BY created_at DESC
                LIMIT 200
                """
            )
            users = cur.fetchall() or []
    except Exception as e:
        print(f"[USERS] Query error: {e}")
        flash("Không thể tải danh sách người dùng.", "error")
    finally:
        if conn:
            conn.close()

    return render_template("users.html", users=users)


@users_bp.route("/init-db", methods=["POST", "GET"])
def init_db():
    """Khởi tạo các bảng ứng dụng (chỉ admin)."""
    if not require_admin():
        return redirect(url_for("login.login"))

    conn = None
    try:
        conn = get_connection()
        init_database(conn)
        flash("Đã khởi tạo bảng ứng dụng thành công.", "success")
    except Exception as e:
        print(f"[USERS] Init DB error: {e}")
        flash(f"Không thể khởi tạo DB: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("users.list_users"))


@users_bp.route("/payments")
def payments_list():
    if not require_admin():
        return redirect(url_for("login.login"))

    conn = None
    try:
        conn = get_connection()
        orders = PaymentOrder.list_all(conn, limit=200)
    finally:
        if conn:
            conn.close()

    return render_template("payments_admin.html", orders=orders)


@users_bp.route("/set-plan", methods=["POST"])
def set_user_plan():
    if not require_admin():
        return redirect(url_for("login.login"))

    user_id_raw = (request.form.get("user_id") or "").strip()
    plan = (request.form.get("plan") or "free").strip().lower()
    allowed_plans = {"free", "basic", "pro", "enterprise"}
    if plan not in allowed_plans:
        plan = "free"

    try:
        user_id = int(user_id_raw)
    except Exception:
        flash("User ID không hợp lệ.", "error")
        return redirect(url_for("users.list_users"))

    conn = None
    try:
        conn = get_connection()
        UserQuota.get_or_create(conn, user_id)
        UserQuota.set_plan(conn, user_id, plan)
        flash(f"Đã cấp gói {plan.upper()} cho user #{user_id}.", "success")
    except Exception as e:
        print(f"[USERS] set plan error: {e}")
        flash("Không thể cấp gói cho user. Vui lòng thử lại.", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("users.list_users"))
