from pydantic import BaseModel, Field
from typing import List, Optional

class RoleResponseSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_system_role: bool
    permissions: List[str]

    class Config:
        from_attributes = True

class RoleCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="The unique name of the role (e.g., FLEET_MANAGER)")
    description: Optional[str] = Field(None, max_length=255, description="What this role is responsible for")

class RoleUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description="Role name (Cannot be modified for system roles)")
    description: Optional[str] = Field(None, max_length=255, description="New description for the role")

class PermissionResponseSchema(BaseModel):
    id: int
    name: str = Field(alias='code')
    description: str

    class Config:
        from_attributes = True
        populate_by_name = True

class PermissionAssignSchema(BaseModel):
    permission_ids: List[int] = Field(..., description="List of exact permission IDs to assign to the role", min_items=1)
