from pydantic import BaseModel
from typing import Optional

class InvitationAcceptRequest(BaseModel):
    token: str
    mobile: str
    password: Optional[str] = None

class InvitationAcceptResponse(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
