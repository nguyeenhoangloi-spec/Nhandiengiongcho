# init_db.py
# Script để khởi tạo database tables

from connect import get_connection
from models import init_database

if __name__ == "__main__":
    try:
        print("Đang kết nối đến database...")
        conn = get_connection()
        
        print("Đang khởi tạo các bảng...")
        init_database(conn)
        
        print("✓ Khởi tạo database thành công!")
        print("Các bảng đã được tạo:")
        print("  - prediction_history")
        print("  - user_settings")
        
        conn.close()
        print("✓ Đã đóng kết nối database")
        
    except Exception as e:
        print(f"✗ Lỗi khi khởi tạo database: {e}")
        raise
