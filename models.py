# models.py
# Database models for prediction history and user management

from datetime import datetime
from typing import Optional, List, Dict, Any
import json


class PredictionHistory:
    """Model để lưu lịch sử nhận diện giống chó"""
    
    def __init__(self, id: Optional[int] = None, user_id: Optional[int] = None, 
                 image_path: str = "", breed: str = "", confidence: float = 0.0,
                 species: str = "", created_at: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.image_path = image_path
        self.breed = breed
        self.confidence = confidence
        self.species = species
        self.created_at = created_at or datetime.now()
    
    @staticmethod
    def create_table(conn):
        """Tạo bảng prediction_history"""
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS prediction_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    image_path VARCHAR(500) NOT NULL,
                    breed VARCHAR(200),
                    confidence FLOAT,
                    species VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
    
    @staticmethod
    def save(conn, user_id: int, image_path: str, breed: str, 
             confidence: float, species: str = "Dog"):
        """Lưu một lần nhận diện vào database"""
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO prediction_history 
                (user_id, image_path, breed, confidence, species)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, image_path, breed, confidence, species))
            conn.commit()
            return cur.fetchone()[0]
    
    @staticmethod
    def get_by_user(conn, user_id: int, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Lấy lịch sử nhận diện của user với phân trang"""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, image_path, breed, confidence, species, created_at
                FROM prediction_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
            rows = cur.fetchall()
            return [{
                'id': row[0],
                'image_path': row[1],
                'breed': row[2],
                'confidence': row[3],
                'species': row[4],
                'created_at': row[5]
            } for row in rows]
    
    @staticmethod
    def count_by_user(conn, user_id: int) -> int:
        """Đếm tổng số bản ghi lịch sử của user"""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM prediction_history WHERE user_id = %s
            """, (user_id,))
            return cur.fetchone()[0]
    
    @staticmethod
    def get_stats(conn, user_id: int) -> Dict[str, Any]:
        """Lấy thống kê cho user"""
        with conn.cursor() as cur:
            # Tổng số lần nhận diện
            cur.execute("""
                SELECT COUNT(*) FROM prediction_history WHERE user_id = %s
            """, (user_id,))
            total_predictions = cur.fetchone()[0]
            
            # Top 5 giống phổ biến
            cur.execute("""
                SELECT breed, COUNT(*) as count
                FROM prediction_history
                WHERE user_id = %s AND breed IS NOT NULL
                GROUP BY breed
                ORDER BY count DESC
                LIMIT 5
            """, (user_id,))
            top_breeds = [{'breed': row[0], 'count': row[1]} for row in cur.fetchall()]
            
            # Độ tin cậy trung bình
            cur.execute("""
                SELECT AVG(confidence) FROM prediction_history 
                WHERE user_id = %s AND confidence IS NOT NULL
            """, (user_id,))
            avg_confidence = cur.fetchone()[0] or 0.0
            
            return {
                'total_predictions': total_predictions,
                'top_breeds': top_breeds,
                'avg_confidence': float(avg_confidence)
            }


class UserSettings:
    """Model cho user settings"""
    
    @staticmethod
    def create_table(conn):
        """Tạo bảng user_settings"""
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    theme VARCHAR(20) DEFAULT 'light',
                    language VARCHAR(10) DEFAULT 'vi',
                    notifications BOOLEAN DEFAULT TRUE,
                    email_notifications BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
    
    @staticmethod
    def get_or_create(conn, user_id: int) -> Dict[str, Any]:
        """Lấy hoặc tạo settings cho user"""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT theme, language, notifications, email_notifications
                FROM user_settings WHERE user_id = %s
            """, (user_id,))
            row = cur.fetchone()
            
            if not row:
                # Tạo settings mặc định
                cur.execute("""
                    INSERT INTO user_settings (user_id)
                    VALUES (%s)
                    RETURNING theme, language, notifications, email_notifications
                """, (user_id,))
                conn.commit()
                row = cur.fetchone()
            
            return {
                'theme': row[0],
                'language': row[1],
                'notifications': row[2],
                'email_notifications': row[3]
            }
    
    @staticmethod
    def update(conn, user_id: int, settings: Dict[str, Any]):
        """Cập nhật settings"""
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE user_settings
                SET theme = %s, language = %s, 
                    notifications = %s, email_notifications = %s
                WHERE user_id = %s
            """, (settings.get('theme'), settings.get('language'),
                  settings.get('notifications'), settings.get('email_notifications'),
                  user_id))
            conn.commit()


class UserQuota:
    """Theo dõi quota sử dụng tính năng nhận diện cho user.

    - Free: 10 lần nhận diện miễn phí.
    - Sau đó phải xem quảng cáo để mở khóa thêm, tối đa 3 lần xem.
    - Premium: không giới hạn (demo).
    """

    FREE_PREDICTIONS = 10
    MAX_AD_VIEWS = 3
    AD_UNLOCK_PER_VIEW = 3

    @staticmethod
    def create_table(conn):
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_quota (
                    user_id INTEGER PRIMARY KEY,
                    plan VARCHAR(20) NOT NULL DEFAULT 'free',
                    ad_views_used INTEGER NOT NULL DEFAULT 0,
                    ad_unlocks_remaining INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    @staticmethod
    def get_or_create(conn, user_id: int) -> Dict[str, Any]:
        """Lấy quota hoặc tạo mặc định nếu chưa có."""
        # An toàn: đảm bảo bảng tồn tại (CREATE IF NOT EXISTS là idempotent)
        UserQuota.create_table(conn)

        with conn.cursor() as cur:
            cur.execute(
                "SELECT plan, ad_views_used, ad_unlocks_remaining FROM user_quota WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO user_quota (user_id) VALUES (%s) RETURNING plan, ad_views_used, ad_unlocks_remaining",
                    (user_id,),
                )
                conn.commit()
                row = cur.fetchone()

        return {
            "plan": row[0],
            "ad_views_used": int(row[1] or 0),
            "ad_unlocks_remaining": int(row[2] or 0),
        }

    @staticmethod
    def set_plan(conn, user_id: int, plan: str) -> None:
        UserQuota.create_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_quota (user_id, plan)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET plan = EXCLUDED.plan, updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, plan),
            )
            conn.commit()

    @staticmethod
    def mark_ad_watched(conn, user_id: int) -> Optional[Dict[str, Any]]:
        """Ghi nhận đã xem 1 quảng cáo và cộng thêm unlock.

        Trả về trạng thái mới nếu còn lượt xem ads; None nếu đã hết.
        """
        UserQuota.create_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_quota
                SET ad_views_used = ad_views_used + 1,
                    ad_unlocks_remaining = ad_unlocks_remaining + %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND ad_views_used < %s
                RETURNING plan, ad_views_used, ad_unlocks_remaining
                """,
                (UserQuota.AD_UNLOCK_PER_VIEW, user_id, UserQuota.MAX_AD_VIEWS),
            )
            row = cur.fetchone()
            if not row:
                conn.commit()
                return None
            conn.commit()
            return {
                "plan": row[0],
                "ad_views_used": int(row[1] or 0),
                "ad_unlocks_remaining": int(row[2] or 0),
            }

    @staticmethod
    def consume_ad_unlock(conn, user_id: int) -> bool:
        """Trừ 1 unlock nếu còn. Trả về True nếu trừ thành công."""
        UserQuota.create_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_quota
                SET ad_unlocks_remaining = ad_unlocks_remaining - 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND ad_unlocks_remaining > 0
                RETURNING ad_unlocks_remaining
                """,
                (user_id,),
            )
            ok = cur.fetchone() is not None
            conn.commit()
            return bool(ok)

    @staticmethod
    def refund_ad_unlock(conn, user_id: int) -> None:
        """Hoàn lại 1 unlock (dùng khi prediction fail sau khi đã consume)."""
        UserQuota.create_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_quota
                SET ad_unlocks_remaining = ad_unlocks_remaining + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (user_id,),
            )
            conn.commit()


def init_database(conn):
    """Khởi tạo tất cả các bảng cần thiết"""
    PredictionHistory.create_table(conn)
    UserSettings.create_table(conn)
    UserQuota.create_table(conn)
    PaymentOrder.create_table(conn)
    print("✅ Database tables initialized successfully!")


class PaymentOrder:
    """Đơn thanh toán (demo) để admin theo dõi ai mua gói gì."""

    @staticmethod
    def create_table(conn):
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_orders (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(32) NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    plan VARCHAR(20) NOT NULL,
                    payment_method VARCHAR(20) NOT NULL,
                    amount_vnd INTEGER NOT NULL DEFAULT 0,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            conn.commit()

    @staticmethod
    def create_order(conn, order_id: str, user_id: int, plan: str, payment_method: str, amount_vnd: int) -> int:
        PaymentOrder.create_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO payment_orders (order_id, user_id, plan, payment_method, amount_vnd)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (order_id, user_id, plan, payment_method, int(amount_vnd or 0)),
            )
            conn.commit()
            return int(cur.fetchone()[0])

    @staticmethod
    def get_by_order_id(conn, order_id: str) -> Optional[Dict[str, Any]]:
        PaymentOrder.create_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT order_id, user_id, plan, payment_method, amount_vnd, status, created_at, confirmed_at
                FROM payment_orders
                WHERE order_id = %s
                """,
                (order_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "order_id": row[0],
                "user_id": row[1],
                "plan": row[2],
                "payment_method": row[3],
                "amount_vnd": int(row[4] or 0),
                "status": row[5],
                "created_at": row[6],
                "confirmed_at": row[7],
            }

    @staticmethod
    def list_by_user(conn, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        PaymentOrder.create_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT order_id, plan, payment_method, amount_vnd, status, created_at, confirmed_at
                FROM payment_orders
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cur.fetchall() or []
            return [
                {
                    "order_id": r[0],
                    "plan": r[1],
                    "payment_method": r[2],
                    "amount_vnd": int(r[3] or 0),
                    "status": r[4],
                    "created_at": r[5],
                    "confirmed_at": r[6],
                }
                for r in rows
            ]

    @staticmethod
    def list_all(conn, limit: int = 200) -> List[Dict[str, Any]]:
        PaymentOrder.create_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT po.order_id, po.plan, po.payment_method, po.amount_vnd, po.status, po.created_at, po.confirmed_at,
                       u.id, u.username, u.fullname, u.email
                FROM payment_orders po
                JOIN users u ON u.id = po.user_id
                ORDER BY po.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall() or []
            return [
                {
                    "order_id": r[0],
                    "plan": r[1],
                    "payment_method": r[2],
                    "amount_vnd": int(r[3] or 0),
                    "status": r[4],
                    "created_at": r[5],
                    "confirmed_at": r[6],
                    "user_id": r[7],
                    "username": r[8],
                    "fullname": r[9],
                    "email": r[10],
                }
                for r in rows
            ]

    @staticmethod
    def mark_paid(conn, order_id: str) -> bool:
        PaymentOrder.create_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE payment_orders
                SET status = 'paid', confirmed_at = CURRENT_TIMESTAMP
                WHERE order_id = %s AND status <> 'paid'
                RETURNING order_id
                """,
                (order_id,),
            )
            ok = cur.fetchone() is not None
            conn.commit()
            return bool(ok)
