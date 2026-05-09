from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.api.v1.organizations.member_schemas import MemberCreate, MemberUpdate
from app.models.organization_member import OrganizationMember, MembershipStatus
from app.repositories.organization_member_repo import OrganizationMemberRepository
from app.models.role import Role
from app.models.user import User
from app.models.organization import Organization
from app.models.role_mapping import UserRole
from app.services.audit_service import AuditService
from app.services.subscription_service import SubscriptionService
from datetime import datetime

class OrganizationMemberService:
    
    @staticmethod
    def _is_system_admin(db: Session, user_id: int) -> bool:
        admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
        if not admin_role: return False
        return db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == admin_role.id).first() is not None

    @staticmethod
    def _is_org_member(db: Session, user_id: int, org_id: int) -> bool:
        return db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.org_id == org_id).first() is not None

    @staticmethod
    def _sync_user_role(db: Session, user_id: int, role_id: int, org_id: int, status: MembershipStatus):
        """Synchronizes the main system RBAC user_roles table with the membership status"""
        existing = db.query(UserRole).filter(
            UserRole.user_id == user_id, 
            UserRole.org_id == org_id
        ).first()

        if status in [MembershipStatus.ACTIVE, MembershipStatus.INVITED]:
            if existing:
                existing.role_id = role_id
            else:
                db.add(UserRole(user_id=user_id, role_id=role_id, org_id=org_id))
        else: # REMOVED or SUSPENDED means cut RBAC
            if existing:
                db.delete(existing)

    @staticmethod
    def list_members(db: Session, org_id: int, current_user: User):
        if not OrganizationMemberService._is_org_member(db, current_user.id, org_id) and not OrganizationMemberService._is_system_admin(db, current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to view members for this organization")
            
        members = OrganizationMemberRepository.get_members_by_org(db, org_id)
        
        # Format response
        result = []
        for m in members:
            result.append({
                "id": m.id,
                "organization_id": m.organization_id,
                "user_id": m.user_id,
                "role_id": m.role_id,
                "status": m.status,
                "joined_at": m.joined_at,
                "created_at": m.created_at,
                "email": m.user.email,
                "role_name": m.role.name if m.role else None
            })
        return result

    @staticmethod
    def add_member(db: Session, org_id: int, data: MemberCreate, current_user: User):
        if not OrganizationMemberService._is_org_member(db, current_user.id, org_id) and not OrganizationMemberService._is_system_admin(db, current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to manage members for this organization")

        # 1. Validate Organization
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # 2. Validate Role
        role = db.query(Role).filter(Role.id == data.role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        if role.name == "ADMIN":
            raise HTTPException(status_code=400, detail="Cannot assign system ADMIN role through organization membership")

        # 3. Check Subscription Limits
        try:
            sub = SubscriptionService.get_my_subscription(db, org_id)
            if hasattr(sub.plan, 'max_members') and sub.plan.max_members is not None:
                current_active = OrganizationMemberRepository.count_active_members(db, org_id)
                if current_active >= sub.plan.max_members:
                    raise HTTPException(status_code=403, detail=f"Membership limit ({sub.plan.max_members}) reached for your subscription plan")
        except HTTPException as e:
            if e.status_code == 404:
                # No subscription found, optionally block or allow
                pass 
            else:
                raise e

        # 4. Resolve User Create/Link
        user = db.query(User).filter(User.email == data.email).first()
        if not user:
            # Create minimal user shell
            user = User(email=data.email, is_active=True, mobile=f"invite_{datetime.utcnow().timestamp()}")
            db.add(user)
            db.flush()
            db.refresh(user)

        # 5. Prevent Duplicates
        existing_member = OrganizationMemberRepository.get_member(db, org_id, user.id)
        if existing_member and existing_member.status in [MembershipStatus.ACTIVE, MembershipStatus.INVITED]:
            raise HTTPException(status_code=400, detail="User is already an active member of this organization")

        # 6. Create Row
        new_member = OrganizationMember(
            organization_id=org_id,
            user_id=user.id,
            role_id=role.id,
            invited_by=current_user.id,
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.utcnow()
        )
        
        if existing_member and existing_member.status == MembershipStatus.REMOVED:
            # Reactivate
            existing_member.status = MembershipStatus.ACTIVE
            existing_member.role_id = role.id
            existing_member.joined_at = datetime.utcnow()
            new_member = existing_member
        else:
            new_member = OrganizationMemberRepository.create_member(db, new_member)

        # 7. Sync RBAC
        OrganizationMemberService._sync_user_role(db, user.id, role.id, org_id, MembershipStatus.ACTIVE)

        # 8. Audit
        audit = AuditService(db)
        audit.log_action(current_user.id, "membership.created", org_id, {"target_user_id": user.id, "role": role.name})

        db.commit()
        db.refresh(new_member)
        
        return {
            "id": new_member.id,
            "organization_id": new_member.organization_id,
            "user_id": new_member.user_id,
            "role_id": new_member.role_id,
            "status": new_member.status,
            "joined_at": new_member.joined_at,
            "created_at": new_member.created_at,
            "email": user.email,
            "role_name": role.name
        }

    @staticmethod
    def update_member(db: Session, org_id: int, user_id: int, data: MemberUpdate, current_user: User):
        if not OrganizationMemberService._is_org_member(db, current_user.id, org_id) and not OrganizationMemberService._is_system_admin(db, current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to manage members")

        member = OrganizationMemberRepository.get_member(db, org_id, user_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        old_role = member.role
        
        # Role Validation Guard
        new_role = None
        if data.role_id is not None and data.role_id != member.role_id:
            new_role = db.query(Role).filter(Role.id == data.role_id).first()
            if not new_role:
                raise HTTPException(status_code=404, detail="New role not found")
            if new_role.name == "ADMIN":
                raise HTTPException(status_code=400, detail="Cannot assign system ADMIN role")

        # Demotion / Orphan Guard
        if (data.status in [MembershipStatus.SUSPENDED, MembershipStatus.REMOVED] or (new_role and new_role.name != "ORGANIZATION")) and old_role.name == "ORGANIZATION":
            admin_count = OrganizationMemberRepository.count_active_admins(db, org_id)
            if admin_count <= 1:
                db.rollback()
                raise HTTPException(status_code=400, detail="Cannot demote or suspend the last active ORG_ADMIN")

        if data.status is not None:
            member.status = data.status
            
        if new_role:
            member.role_id = new_role.id

        # Sync RBAC system to match new state
        OrganizationMemberService._sync_user_role(db, member.user_id, member.role_id, org_id, member.status)

        # Audit
        audit = AuditService(db)
        audit.log_action(current_user.id, "membership.updated", org_id, {
            "target_user_id": member.user_id, 
            "new_status": member.status.value,
            "new_role_id": member.role_id
        })

        db.commit()
        db.refresh(member)
        return {
            "id": member.id,
            "organization_id": member.organization_id,
            "user_id": member.user_id,
            "role_id": member.role_id,
            "status": member.status,
            "joined_at": member.joined_at,
            "created_at": member.created_at,
            "email": member.user.email,
            "role_name": db.query(Role.name).filter(Role.id == member.role_id).scalar()
        }

    @staticmethod
    def remove_member(db: Session, org_id: int, user_id: int, current_user: User):
        if not OrganizationMemberService._is_org_member(db, current_user.id, org_id) and not OrganizationMemberService._is_system_admin(db, current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to manage members")

        member = OrganizationMemberRepository.get_member(db, org_id, user_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        # Prevent removing system ADMINs entirely (safety parachute)
        if OrganizationMemberService._is_system_admin(db, user_id):
            raise HTTPException(status_code=400, detail="Cannot remove a global system ADMIN from their organization via this endpoint")

        # Orphan Guard
        if member.role.name == "ORGANIZATION":
            admin_count = OrganizationMemberRepository.count_active_admins(db, org_id)
            if admin_count <= 1:
                db.rollback()
                raise HTTPException(status_code=400, detail="Cannot remove the last active ORG_ADMIN")

        # Soft Delete
        member.status = MembershipStatus.REMOVED
        
        # Kill RBAC access instantly
        OrganizationMemberService._sync_user_role(db, member.user_id, member.role_id, org_id, MembershipStatus.REMOVED)

        # Audit
        audit = AuditService(db)
        audit.log_action(current_user.id, "membership.removed", org_id, {"target_user_id": member.user_id})

        db.commit()
        return {"status": "success", "message": "Member successfully removed"}
