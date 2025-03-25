from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID


class PermissionBase(BaseModel):
    """Base schema for Permission data"""
    code: str = Field(..., description="Unique permission code")
    name: str = Field(..., description="Human-readable name")
    module: str = Field(..., description="Module/resource this permission belongs to")
    description: Optional[str] = Field(None, description="Description of what this permission allows")


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission"""

    class Config:
        json_schema_extra = {
            "example": {
                "code": "users_create",
                "name": "Create Users",
                "module": "users",
                "description": "Allows creating new users in the system"
            }
        }


class PermissionUpdate(BaseModel):
    """Schema for updating a permission"""
    name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field(None, description="Description of what this permission allows")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Create User Accounts",
                "description": "Allows creating new user accounts in the system"
            }
        }


class Permission(PermissionBase):
    """Schema for Permission data returned to client"""
    id: UUID
    company_id: UUID

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """Base schema for Role data"""
    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    is_system_role: Optional[bool] = Field(False, description="Whether this is a system role that cannot be modified")


class RoleCreate(RoleBase):
    """Schema for creating a new role"""
    permission_ids: Optional[List[UUID]] = Field(None, description="List of permission IDs to assign to this role")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Site Manager",
                "description": "Can manage most aspects of a site but has limited user management",
                "is_system_role": False,
                "permission_ids": ["550e8400-e29b-41d4-a716-446655440000"]
            }
        }


class RoleUpdate(BaseModel):
    """Schema for updating a role"""
    name: Optional[str] = Field(None, description="Role name")
    description: Optional[str] = Field(None, description="Role description")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Site Manager",
                "description": "Updated description for site manager role"
            }
        }


class Role(RoleBase):
    """Schema for Role data returned to client"""
    id: UUID
    company_id: UUID
    permissions: List[Permission] = []

    class Config:
        from_attributes = True


class RolePermissionsUpdate(BaseModel):
    """Schema for adding or removing permissions from a role"""
    add_permission_ids: Optional[List[UUID]] = Field(None, description="List of permission IDs to add to this role")
    remove_permission_ids: Optional[List[UUID]] = Field(None,
                                                        description="List of permission IDs to remove from this role")

    class Config:
        json_schema_extra = {
            "example": {
                "add_permission_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                "remove_permission_ids": ["550e8400-e29b-41d4-a716-446655440001"]
            }
        }