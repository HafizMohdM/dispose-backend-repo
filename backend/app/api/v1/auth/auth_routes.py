from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.v1.auth.auth_schemas import RequestOTP, VerifyOTP
from app.api.v1.auth.auth_service import request_otp, verify_otp
from app.core.database import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/request-otp")
def request_otp_api(payload: RequestOTP, db: Session = Depends(get_db)):
    otp = request_otp(db, payload.mobile)
    return {"message": "OTP sent", "otp": otp}  # REMOVE otp later


@router.post("/verify-otp")
def verify_otp_api(payload: VerifyOTP, db: Session = Depends(get_db)):
    token = verify_otp(db, payload.mobile, payload.otp)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    return {"access_token": token}
