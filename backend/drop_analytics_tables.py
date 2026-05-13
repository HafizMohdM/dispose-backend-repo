from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

tables_to_drop = [
    'analytics_events', 
    'daily_metrics', 
    'pickup_metrics', 
    'revenue_metrics', 
    'driver_metrics'
]

with engine.connect() as conn:
    for table in tables_to_drop:
        print(f"Dropping table {table}...")
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    conn.commit()
print("Done.")
