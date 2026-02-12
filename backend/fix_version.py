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
    conn.autocommit = True
    cur = conn.cursor()
    
    print("Updating alembic_version...")
    cur.execute("UPDATE alembic_version SET version_num = 'b8a9479380e9';")
    print("Update complete.")
    
    cur.execute("SELECT version_num FROM alembic_version")
    print(f"New version in DB: {cur.fetchall()}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
