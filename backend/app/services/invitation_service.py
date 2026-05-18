import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Tuple
from app.repositories.invitation_repo import InvitationRepository
from app.models.invitation import InvitationStatus
from app.models.user import User, UserSession
from app.models.role import Role
from app.models.role_mapping import UserRole
from app.api.v1.auth.invitation_schemas import InvitationAcceptRequest, InvitationAcceptResponse
from app.core.security import create_access_token, generate_refresh_token

class InvitationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InvitationRepository(db)

    def accept_invitation(self, request: InvitationAcceptRequest, client_ip: str = None, user_agent: str = None) -> InvitationAcceptResponse:
        """
        Processes a secure invitation acceptance. Fully atomic.
        Returns the initial JWT tokens.
        """
        try:
            with self.db.begin_nested():
                # 1. Fetch and Lock the invitation
                invitation = self.repo.get_invitation_by_token_for_acceptance(request.token)
                
                if not invitation:
                    raise ValueError("Invitation not found.")
                    
                if invitation.status == InvitationStatus.EXPIRED.value:
                    raise ValueError("Invitation has expired.")
                elif invitation.status != InvitationStatus.PENDING.value:
                    raise ValueError(f"Invitation is {invitation.status}.")
                    
                if datetime.datetime.utcnow() > invitation.expires_at:
                    invitation.status = InvitationStatus.EXPIRED.value
                    raise ValueError("Invitation has expired.")
                    
                # 2. Find or Create User
                user = self.repo.get_user_by_email_or_mobile(invitation.email, request.mobile)
                if not user:
                    user = User(
                        email=invitation.email,
                        mobile=request.mobile,
                        is_active=True
                        # password_hash handling if added later
                    )
                    self.db.add(user)
                    self.db.flush() # get user.id
                else:
                    # User exists. Check consistency
                    if user.email and user.email != invitation.email:
                        raise ValueError("Mobile number already registered to a different email.")
                    # Attach email if it was missing
                    if not user.email:
                        user.email = invitation.email
                        
                # 3. Resolve Target Role
                role = self.db.query(Role).filter(Role.name == invitation.role).first()
                if not role:
                    raise ValueError(f"Target system role '{invitation.role}' could not be resolved.")
                    
                # 4. Map User to Organization
                existing_mapping = self.db.query(UserRole).filter(
                    UserRole.user_id == user.id, 
                    UserRole.org_id == invitation.organization_id
                ).first()
                
                if not existing_mapping:
                    mapping = UserRole(
                        user_id=user.id,
                        role_id=role.id,
                        org_id=invitation.organization_id
                    )
                    self.db.add(mapping)
                else:
                    existing_mapping.role_id = role.id

                # 5. Mark Invitation as Accepted
                invitation.status = InvitationStatus.ACCEPTED.value
                invitation.accepted_at = datetime.datetime.utcnow()
                invitation.accepted_by_user_id = user.id

                # 6. Generate Session and Tokens
                refresh_token = generate_refresh_token()
                session = UserSession(
                    user_id=user.id,
                    token="temp", # Temporary, will update
                    refresh_token=refresh_token,
                    expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7),
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                self.db.add(session)
                self.db.flush()

                # Generate Access Token
                access_token = create_access_token({
                    "user_id": user.id,
                    "org_id": invitation.organization_id,
                    "role": role.name,
                    "session_id": session.id,
                    "token_version": user.token_version
                })
                
                # Link token to session
                session.token = access_token

            self.db.commit()
            
            return InvitationAcceptResponse(
                message="Invitation accepted successfully.",
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer"
            )
            
        except ValueError as ve:
            self.db.rollback()
            msg = str(ve)
            if "expired" in msg:
                raise HTTPException(status_code=status.HTTP_410_GONE, detail=msg)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to accept invitation.")

    def cleanup_expired_invitations(self, organization_id: int) -> int:
        """
        Idempotent utility to cleanly delete expired invitations for an organization.
        """
        from app.models.invitation import Invitation
        
        expired_invites = self.db.query(Invitation).filter(
            Invitation.organization_id == organization_id,
            Invitation.status == InvitationStatus.PENDING.value,
            Invitation.expires_at < datetime.datetime.utcnow()
        ).with_for_update().all()
        
        count = len(expired_invites)
        if count == 0:
            return 0
            
        for invite in expired_invites:
            self.db.delete(invite)
            
        self.db.commit()
        return count
