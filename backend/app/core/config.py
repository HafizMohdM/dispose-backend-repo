import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = os.getenv("JWT_EXPIRE_HOURS", 24)

JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 15))


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:root@localhost/dispose")
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", 5))



