import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.role import Role, Permission
from app.models.role_mapping import RolePermission, UserRole
from app.main import app

def test_delete_admin_role_forbidden(client: TestClient, admin_token_headers: dict, db: Session):
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    assert admin_role is not None
    
    response = client.delete(
        f"/api/v1/admin/roles/{admin_role.id}",
        headers=admin_token_headers
    )
    
    assert response.status_code == 403
    assert "System roles cannot be deleted" in response.json()["detail"]


def test_rename_admin_role_forbidden(client: TestClient, admin_token_headers: dict, db: Session):
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    assert admin_role is not None
    
    response = client.patch(
        f"/api/v1/admin/roles/{admin_role.id}",
        headers=admin_token_headers,
        json={"name": "SUPER_ADMIN", "description": "Trying to rename it"}
    )
    
    assert response.status_code == 400
    assert "System roles cannot be renamed" in response.json()["detail"]


def test_remove_critical_permissions_from_admin(client: TestClient, admin_token_headers: dict, db: Session):
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    
    # Try to assign permission without rbac.manage, pickup.manage etc
    # 9999 is a dummy non-critical permission (hopefully doesn't exist, will fail ID check, or we use a valid one)
    # Let's get a safe permission to assign
    safe_perm = db.query(Permission).filter(Permission.code == "driver:view").first()
    assert safe_perm is not None
    
    response = client.patch(
        f"/api/v1/admin/roles/{admin_role.id}/permissions",
        headers=admin_token_headers,
        json={"permission_ids": [safe_perm.id]}
    )
    
    assert response.status_code == 400
    assert "Cannot remove critical permissions from ADMIN role" in response.json()["detail"]


def test_self_lockout_prevention(client: TestClient, admin_token_headers: dict, db: Session, default_admin_user):
    # Determine the role ID of the admin user
    user_role = db.query(UserRole).filter(UserRole.user_id == default_admin_user.id).first()
    assert user_role is not None
    
    # Needs to be tested with a custom role that the user has, because ADMIN triggers the critical permission block first!
    # Let's create a custom role, give it rbac.manage, assign to user.
    custom_role = Role(name="TEST_MANAGER", description="Test", is_system_role=False)
    db.add(custom_role)
    db.flush()
    
    rbac_perm = db.query(Permission).filter(Permission.code == "rbac.manage").first()
    db.add(RolePermission(role_id=custom_role.id, permission_id=rbac_perm.id))
    
    # Assign our test user
    db.add(UserRole(user_id=default_admin_user.id, role_id=custom_role.id, org_id=1))
    db.commit()
    
    # Now, test user tries to remove rbac.manage from their TEST_MANAGER role
    safe_perm = db.query(Permission).filter(Permission.code == "driver:view").first()
    
    response = client.patch(
        f"/api/v1/admin/roles/{custom_role.id}/permissions",
        headers=admin_token_headers,
        json={"permission_ids": [safe_perm.id]} # omitting rbac.manage
    )
    
    assert response.status_code == 403
    assert "Self-lockout prevented" in response.json()["detail"]


def test_delete_role_in_use(client: TestClient, admin_token_headers: dict, db: Session, default_admin_user):
    custom_role = Role(name="IN_USE_ROLE", description="Test", is_system_role=False)
    db.add(custom_role)
    db.flush()
    
    db.add(UserRole(user_id=default_admin_user.id, role_id=custom_role.id, org_id=1))
    db.commit()
    
    response = client.delete(
        f"/api/v1/admin/roles/{custom_role.id}",
        headers=admin_token_headers
    )
    
    assert response.status_code == 400
    assert "assigned to users and cannot be deleted" in response.json()["detail"]
