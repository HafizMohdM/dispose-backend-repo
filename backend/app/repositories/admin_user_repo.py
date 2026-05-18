from sqlalchemy.orm import Session
from sqlalchemy import asc, or_, func
from typing import List, Tuple, Optional
from app.models.user import User
from app.models.role_mapping import UserRole
from app.models.role import Role
from app.models.invitation import Invitation, InvitationStatus

class AdminUserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_users_cursor_paginated(
        self, 
        organization_id: int,
        last_seen_id: Optional[int], 
        limit: int,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[User], bool]:
        """
        High-Scale Keyset/Cursor Pagination bypassing slow OFFSET scans.
        Filters by organization_id, optional search term, role, and status.
        """
        query = self.db.query(User).join(UserRole).join(Role).filter(
            UserRole.org_id == organization_id
        )
        
        if search:
            search_term = f"%{search.lower().strip()}%"
            query = query.filter(
                or_(
                    func.lower(User.email).like(search_term),
                    func.lower(Role.name).like(search_term)
                )
            )

        if role:
            query = query.filter(func.lower(Role.name) == role.lower().strip())

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        # Dynamic Sorting safely checking allowed fields
        allowed_sorts = {"created_at": User.created_at, "last_login_at": User.last_login_at, "email": User.email, "id": User.id}
        sort_column = allowed_sorts.get(sort_by.lower(), User.created_at)
        
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc(), User.id.asc())
        else:
            query = query.order_by(sort_column.desc(), User.id.desc())
        
        if last_seen_id is not None:
            if sort_by.lower() == "id":
                if sort_order.lower() == "desc":
                    query = query.filter(User.id < last_seen_id)
                else:
                    query = query.filter(User.id > last_seen_id)
            else:
                # Treat last_seen_id as offset for non-id sorts to prevent frontend breakage
                query = query.offset(last_seen_id)

        users = query.limit(limit + 1).all()
        
        has_more = len(users) > limit
        if has_more:
            users = users[:limit]
            
        return users, has_more

    def get_invitation_by_token(self, token: str) -> Optional[Invitation]:
        return self.db.query(Invitation).filter(Invitation.token == token).first()

    def get_pending_invitations_by_emails(self, organization_id: int, emails: List[str]) -> List[str]:
        """Returns a list of emails that already have a pending invitation. Locks rows for update."""
        invites = self.db.query(Invitation.email).filter(
            Invitation.organization_id == organization_id,
            Invitation.email.in_(emails),
            Invitation.status == InvitationStatus.PENDING.value
        ).with_for_update().all()
        return [inv.email for inv in invites]
