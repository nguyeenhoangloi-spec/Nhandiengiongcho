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


@users_bp.route("/payments/confirm", methods=["POST"])
def confirm_payment():
    if not require_admin():
        return redirect(url_for("login.login"))
    order_id = (request.form.get("order_id") or "").strip()
    if not order_id:
        flash("Thiếu mã đơn.", "error")
        return redirect(url_for("users.payments_list"))
    conn = None
    try:
        conn = get_connection()
        ok = PaymentOrder.mark_paid(conn, order_id)
        # --- Ưu tiên gói cao nhất còn hạn khi xác nhận đơn ---
        if ok:
            from datetime import datetime, timedelta
            # Lấy user_id từ đơn vừa xác nhận
            order = PaymentOrder.get_by_order_id(conn, order_id)
            user_id = order["user_id"] if order else None
            if user_id:
                # Lấy tất cả đơn PAID của user, mới nhất trước
                all_orders = PaymentOrder.list_by_user(conn, user_id, limit=20)
                # Ưu tiên đơn có plan cao nhất, mới nhất
                plan_priority = {"enterprise": 3, "pro": 2, "basic": 1, "free": 0}
                best_order = None
                for o in all_orders:
                    if o["status"] == "paid":
                        if not best_order or plan_priority.get(o["plan"], 0) > plan_priority.get(best_order["plan"], 0):
                            best_order = o
                if best_order:
                    plan = best_order["plan"]
                    now = datetime.now()
                    if plan == "pro":
                        plan_expire = now + timedelta(days=30)
                    elif plan == "enterprise":
                        plan_expire = now + timedelta(days=90)
                    elif plan == "basic":
                        plan_expire = now + timedelta(days=7)
                    else:
                        plan_expire = None
                    UserQuota.set_plan(conn, user_id, plan, plan_expire)
            flash(f"Đã xác nhận thanh toán cho đơn {order_id}.", "success")
        else:
            flash("Không thể xác nhận đơn (có thể đã xác nhận hoặc không tồn tại).", "error")
    except Exception as e:
        print(f"[ADMIN] confirm_payment error: {e}")
        flash("Lỗi xác nhận đơn.", "error")
    finally:
        if conn:
            conn.close()
    return redirect(url_for("users.payments_list"))


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
