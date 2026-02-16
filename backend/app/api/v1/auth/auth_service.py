from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.user import User,UserSession
from app.core.security import generate_otp,hash_otp,create_access_token
from app.core.config import OTP_EXPIRY_MINUTES


def request_otp(db:Session,mobile:str):
    otp= generate_otp()
    hashed =hash_otp(otp)

    user = db.query(User).filter(User.mobile ==mobile).first()
    if not user:
        user = User(mobile=mobile)
        db.add(user)
        db.commit()
        db.refresh(user)

    session = UserSession(
        user_id=user.id,
        token=hashed,
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(session)
    db.commit()

    return otp   #testing

def verify_otp(db:Session,mobile:str,otp:str):
    user = db.query(User).filter(User.mobile ==mobile).first()
    if not user:
        return None

    hashed=hash_otp(otp)
    session = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.token == hashed,
            UserSession.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not session:
        return None

    token = create_access_token({"user_id":user.id})
    return token
    

        