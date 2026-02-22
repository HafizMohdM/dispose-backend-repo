import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ.get('DATABASE_URL'))
with engine.connect() as conn:
    print("User Roles:", conn.execute(text("SELECT * FROM user_roles WHERE user_id=1")).fetchall())
    print("Subscriptions:", conn.execute(text("SELECT * FROM subscriptions")).fetchall())
