import os
from dotenv import load_dotenv

load_dotenv()

# ========================
# APP CONFIGURATION
# ========================

APP_NAME = os.getenv("APP_NAME", "Dispose")
APP_ENV = os.getenv("APP_ENV", "development")
SECRET_KEY = os.getenv("SECRET_KEY", "super-strong-secret-key")

# ========================
# JWT CONFIGURATION
# ========================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "dispose-super-secret-key-2026"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

JWT_EXPIRE_MINUTES = int(
    os.getenv("JWT_EXPIRE_MINUTES", 60)
)

JWT_EXPIRE_HOURS = int(
    os.getenv("JWT_EXPIRE_HOURS", 24)
)

# ========================
# DATABASE CONFIGURATION
# ========================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:root@localhost:5432/dispose"
)

DB_CONNECTION = os.getenv("DB_CONNECTION", "postgresql")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_DATABASE = os.getenv("DB_DATABASE", "dispose")
DB_USERNAME = os.getenv("DB_USERNAME", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

# ========================
# OTP CONFIGURATION
# ========================

OTP_EXPIRY_MINUTES = int(
    os.getenv("OTP_EXPIRY_MINUTES", 5)
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
)
