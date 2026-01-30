# connect.py
# Kết nối tới PostgreSQL theo phong cách "bên ngoài" như ví dụ bạn đưa.

import os
import psycopg2


def get_connection():
    host = os.environ.get("PGHOST", "localhost")
    database = os.environ.get("PGDATABASE", "khoaluantn")
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "123456")
    port = os.environ.get("PGPORT", "5432")

    return psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port,
    )


if __name__ == "__main__":
    try:
        conn = get_connection()
        print("Kết nối thành công!")
        conn.close()
    except Exception as e:
        print("Kết nối thất bại:", e)
