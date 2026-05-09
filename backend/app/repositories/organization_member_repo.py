from sqlalchemy.orm import Session, joinedload
from app.models.organization_member import OrganizationMember, MembershipStatus
from app.models.role import Role
import uuid
from typing import List, Optional

class OrganizationMemberRepository:
    
    @staticmethod
    def get_members_by_org(db: Session, org_id: int) -> List[OrganizationMember]:
        return db.query(OrganizationMember).options(
            joinedload(OrganizationMember.user),
            joinedload(OrganizationMember.role)
        ).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.status.in_([MembershipStatus.ACTIVE, MembershipStatus.INVITED, MembershipStatus.SUSPENDED])
        ).all()
        
    @staticmethod
    def get_member(db: Session, org_id: int, user_id: int) -> Optional[OrganizationMember]:
        return db.query(OrganizationMember).options(
            joinedload(OrganizationMember.user),
            joinedload(OrganizationMember.role)
        ).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status != MembershipStatus.REMOVED
        ).first()
        
    @staticmethod
    def create_member(db: Session, member: OrganizationMember) -> OrganizationMember:
        db.add(member)
        db.flush()
        db.refresh(member)
        return member
        
    @staticmethod
    def count_active_admins(db: Session, org_id: int) -> int:
        """
        Uses row-level locking (FOR UPDATE) to safely count active ORG_ADMIN roles
        to prevent race conditions when removing the last admin.
        """
        return db.query(OrganizationMember).join(Role, OrganizationMember.role_id == Role.id).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.status == MembershipStatus.ACTIVE,
            Role.name == "ORGANIZATION"
        ).with_for_update().count()
        
    @staticmethod
    def count_active_members(db: Session, org_id: int) -> int:
        return db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.status.in_([MembershipStatus.ACTIVE, MembershipStatus.INVITED])
        ).count()
