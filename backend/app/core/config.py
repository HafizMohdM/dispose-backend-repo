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

# ========================
# TWILIO CONFIGURATION
# ========================

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# ========================
# RAZORPAY CONFIGURATION
# ========================

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_SL2t52a6r7GIcE")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "wk1foVV2bXcbmmnb8CjsPdiR")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "AF_WAZvdyR3TG@d")

# ========================
# REDIS & CELERY CONFIGURATION
# ========================

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# ========================
# EMAIL (SMTP) CONFIGURATION
# ========================

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "notifications@dispose.app")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Dispose Platform")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

# ========================
# FIREBASE (FCM) PUSH CONFIGURATION
# ========================

FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "")
FCM_PROJECT_ID = os.getenv("FCM_PROJECT_ID", "")
