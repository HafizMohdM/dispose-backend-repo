import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_DATABASE")
    )
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM role_permissions")
    print(f"Role Permissions count: {cur.fetchall()}")
    cur.close()
    conn.close()
except Exception as e:
    print(e)
