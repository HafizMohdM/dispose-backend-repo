from pydantic import BaseModel,EmailStr
from typing import Optional

class RequestOTP(BaseModel):
    mobile: str

class VerifyOTP(BaseModel):
    mobile: str
    otp: str

class UpdateProfileRequest(BaseModel):
    email: Optional[EmailStr] = None
    