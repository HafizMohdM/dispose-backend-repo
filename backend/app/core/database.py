from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL

# Production connection pooling for high-concurrency and Celery workers
engine = create_engine(
    DATABASE_URL,
    pool_size=30,
    max_overflow=60,
    pool_timeout=30,
    pool_pre_ping=True  # Handles stale connections gracefully
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
