from pydantic import BaseModel

class RequestOTP(BaseModel):
    mobile: str

class VerifyOTP(BaseModel):
    mobile: str
    otp: str
