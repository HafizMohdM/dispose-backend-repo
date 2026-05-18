from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.models.invitation import Invitation, InvitationStatus
from app.models.user import User

class InvitationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_invitation_by_token_for_acceptance(self, token: str) -> Optional[Invitation]:
        """
        Fetches an invitation strictly matching the token.
        Uses .with_for_update() to lock the row during the critical acceptance flow, preventing double claims.
        """
        return self.db.query(Invitation).filter(
            Invitation.token == token
        ).with_for_update().first()
    
    def get_user_by_email_or_mobile(self, email: str, mobile: str) -> Optional[User]:
        return self.db.query(User).filter(
            or_(
                User.email == email,
                User.mobile == mobile
            )
        ).first()
