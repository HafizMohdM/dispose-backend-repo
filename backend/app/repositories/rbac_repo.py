from sqlalchemy.orm import Session, joinedload
from sqlalchemy import exc
from typing import List, Optional

from app.models.role import Role, Permission
from app.models.role_mapping import RolePermission, UserRole

class RBACRepository:
    
    @staticmethod
    def get_all_roles(db: Session) -> List[Role]:
        # Utilizing joinedload to fetch RolePermission -> Permission automatically to prevent N+1 queries
        return db.query(Role).options(
            joinedload(Role.permissions).joinedload(RolePermission.permission)
        ).filter(Role.is_active == True).all()

    @staticmethod
    def get_role_by_id(db: Session, role_id: int) -> Optional[Role]:
        return db.query(Role).options(
            joinedload(Role.permissions).joinedload(RolePermission.permission)
        ).filter(Role.id == role_id).first()

    @staticmethod
    def get_role_by_name(db: Session, name: str) -> Optional[Role]:
        return db.query(Role).filter(Role.name == name, Role.is_active == True).first()

    @staticmethod
    def create_role(db: Session, name: str, description: Optional[str]) -> Role:
        new_role = Role(
            name=name.upper(),
            description=description,
            is_system_role=False  # Custom roles are explicitly NOT system roles
        )
        db.add(new_role)
        db.flush() 
        return new_role

    @staticmethod
    def update_role_description(db: Session, role: Role, description: str) -> Role:
        role.description = description
        db.flush()
        return role

    @staticmethod
    def is_role_assigned_to_users(db: Session, role_id: int) -> bool:
        """Checks if any active users currently hold this role."""
        count = db.query(UserRole).filter(UserRole.role_id == role_id).count()
        return count > 0

    @staticmethod
    def delete_role(db: Session, role: Role):
        role.is_active = False
        db.flush()

    @staticmethod
    def get_all_permissions(db: Session) -> List[Permission]:
        return db.query(Permission).all()

    @staticmethod
    def get_permissions_by_ids(db: Session, permission_ids: List[int]) -> List[Permission]:
        return db.query(Permission).filter(Permission.id.in_(permission_ids)).all()

    @staticmethod
    def assign_role_permissions(db: Session, role_id: int, permission_ids: List[int]):
        """
        Atomically replaces all permissions for a role in a single transaction.
        """
        try:
            # 1. Delete all existing mappings for this role
            db.query(RolePermission).filter(RolePermission.role_id == role_id).delete(synchronize_session=False)

            # 2. Insert new mappings
            new_mappings = [
                RolePermission(role_id=role_id, permission_id=p_id) 
                for p_id in permission_ids
            ]
            
            db.bulk_save_objects(new_mappings)
            db.flush()
            
        except exc.IntegrityError:
            db.rollback()
            raise
