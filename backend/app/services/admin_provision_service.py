import secrets
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.repositories.admin_user_repo import AdminUserRepository
from app.models.invitation import Invitation, InvitationStatus
from app.api.v1.admin.admin_schemas import InviteRecord, InvitationResponse

class AdminProvisionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdminUserRepository(db)

    def bulk_provision_staff(self, org_id: int, invites: List[InviteRecord]) -> List[InvitationResponse]:
        """
        Atomic bulk provisioning of staff with explicit transaction block rollback.
        Includes idempotency checks, email normalization, and batch error reporting.
        """
        valid_roles = {"admin", "manager", "staff", "driver", "auditor"}
        
        normalized_invites = []
        emails_to_invite = []
        seen_emails_in_request = set()
        errors = []
        
        for invite in invites:
            normalized_email = invite.email.lower().strip()
            
            # Duplicate detection within request
            if normalized_email in seen_emails_in_request:
                errors.append(f"Duplicate email in request: {normalized_email}")
                continue
                
            seen_emails_in_request.add(normalized_email)
            invite.email = normalized_email
            normalized_invites.append(invite)
            emails_to_invite.append(normalized_email)
            
        invitation_records = []
        errors = []
        try:
            with self.db.begin_nested():
                # Idempotency check inside transaction boundary with FOR UPDATE locking
                existing_pending_emails = self.repo.get_pending_invitations_by_emails(org_id, emails_to_invite)
                
                for invite in normalized_invites:
                    if invite.role not in valid_roles:
                        errors.append(f"Unknown role capability for {invite.email}: {invite.role}")
                        continue
                        
                    if invite.email in existing_pending_emails:
                        errors.append(f"Invitation already pending for {invite.email}")
                        continue
                    
                    token = secrets.token_urlsafe(48)
                    expires_at = datetime.utcnow() + timedelta(days=7)
                    
                    invitation = Invitation(
                        organization_id=org_id,
                        email=invite.email,
                        role=invite.role,
                        token=token,
                        expires_at=expires_at,
                        status=InvitationStatus.PENDING.value
                    )
                    invitation_records.append(invitation)
                
                if errors:
                    # Rollback explicitly if any logical error is caught, providing clear batch feedback
                    raise ValueError("Batch validation failed")
                
                self.db.add_all(invitation_records)
            self.db.commit()
            
            for inv in invitation_records:
                self.db.refresh(inv)
                
        except ValueError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": errors})
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Bulk provision failed")
            
        return [
            InvitationResponse(
                id=inv.id,
                email=inv.email,
                role=inv.role,
                status=inv.status,
                expires_at=inv.expires_at,
                created_at=inv.created_at
            )
            for inv in invitation_records
        ]

    def verify_invitation(self, token: str) -> InvitationResponse:
        """
        Cryptographic verification logic handling expiration and status state.
        """
        invitation = self.repo.get_invitation_by_token(token)
        
        if not invitation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
            
        if invitation.status != InvitationStatus.PENDING.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invitation is {invitation.status}")
            
        if datetime.utcnow() > invitation.expires_at:
            invitation.status = InvitationStatus.EXPIRED.value
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired.")
            
        return InvitationResponse(
            id=invitation.id,
            email=invitation.email,
            role=invitation.role,
            status=invitation.status,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at
        )
