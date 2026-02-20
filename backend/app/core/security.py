from datetime import datetime, timedelta
from jose import jwt
import hashlib
import random
import secrets
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS, JWT_EXPIRE_MINUTES


def generate_otp():
    return str(random.randint(100000, 999999))

def hash_otp(otp: str):
    return hashlib.sha256(otp.encode()).hexdigest()

def generate_refresh_token():
    """Generate a cryptographically secure refresh token."""
    return secrets.token_urlsafe(48)

def create_access_token(payload: dict):
    to_encode = payload.copy()
    expire = datetime.utcnow() + timedelta(hours=int(JWT_EXPIRE_HOURS), minutes=int(JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
