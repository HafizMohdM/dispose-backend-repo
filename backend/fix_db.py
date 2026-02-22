import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from app.models.base import Base
import app.models.audit_log
import app.models.user
import app.models.organization

load_dotenv()
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("No DATABASE_URL found.")
    exit(1)

engine = create_engine(database_url)
print("Creating missing tables...")
Base.metadata.create_all(bind=engine)
print("Done.")
