from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.audit_service import log_event
from app.services.invitation_service import InvitationService
from app.api.v1.auth.invitation_schemas import InvitationAcceptRequest, InvitationAcceptResponse

# Usually, rate limiting would be added here e.g. @limiter.limit("10/hour")
router = APIRouter()

@router.post("/accept", response_model=InvitationAcceptResponse)
def accept_invitation(
    request_data: InvitationAcceptRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to securely accept an invitation. 
    Strict cryptographic verification prevents reuse.
    Yields session tokens upon successful mapping.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    service = InvitationService(db)
    result = service.accept_invitation(request_data, client_ip, user_agent)
    
    # Audit trail
    log_event(
        db,
        None, # System/Anonymous execution context initially, could decode token to get user_id but not strictly required
        "INVITATION_ACCEPTED",
        metadata={
            "token": request_data.token[:8] + "...", # Mask token for security
            "ip": client_ip,
            "user_agent": user_agent
        }
    )
    
    return result
