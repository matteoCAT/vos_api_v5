from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.role import (
    Role as RoleSchema,
    RoleCreate,
    RoleUpdate,
    RolePermissionsUpdate,
    Permission
)
from app.crud.role import role as role_crud
from app.crud.permission import permission as permission_crud
from app.core.security import get_current_active_user, check_user_permissions
from app.core.permissions import permission_registry

router = APIRouter()

# Define permissions for this module
PERMISSIONS = {
    "create": "roles_create",
    "read": "roles_read",
    "update": "roles_update",
    "delete": "roles_delete",
    "manage_permissions": "roles_manage_permissions"
}

# Define descriptions for permissions
PERMISSION_DESCRIPTIONS = {
    "roles_create": "Allows creating new roles in the system",
    "roles_read": "Allows viewing role information",
    "roles_update": "Allows updating role information",
    "roles_delete": "Allows deleting roles from the system",
    "roles_manage_permissions": "Allows managing role permissions"
}

# Register permissions with the registry
permission_registry.register_permissions("roles", PERMISSIONS, PERMISSION_DESCRIPTIONS)


@router.get("/", response_model=List[RoleSchema], summary="Get all roles")
def get_roles(
        request: Request,
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["read"]]))
):
    """
    Retrieve all roles within the company.

    - Requires roles_read permission
    - **skip**: Number of roles to skip (pagination)
    - **limit**: Maximum number of roles to return (pagination)
    """
    roles = role_crud.get_multi_by_company(db, company_id=current_user.company_id, skip=skip, limit=limit)
    return roles


@router.post("/", response_model=RoleSchema, status_code=status.HTTP_201_CREATED, summary="Create new role")
def create_role(
        request: Request,
        *,
        db: Session = Depends(get_db),
        role_in: RoleCreate,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["create"]]))
):
    """
    Create a new role within the company.

    - Requires roles_create permission
    - Can optionally assign initial permissions
    """
    # Check if role with same name already exists
    existing_role = role_crud.get_by_name(db, name=role_in.name, company_id=current_user.company_id)
    if existing_role:
        raise HTTPException(
            status_code=400,
            detail="A role with this name already exists"
        )

    # Create the role
    role = role_crud.create(db, obj_in=role_in, company_id=current_user.company_id)
    return role


@router.get("/{role_id}", response_model=RoleSchema, summary="Get role by ID")
def get_role(
        request: Request,
        *,
        db: Session = Depends(get_db),
        role_id: UUID = Path(..., description="The ID of the role to get"),
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["read"]]))
):
    """
    Get a specific role by ID.

    - Requires roles_read permission
    """
    role = role_crud.get(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    # Ensure the role belongs to the current user's company
    if role.company_id != current_user.company_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return role


@router.put("/{role_id}", response_model=RoleSchema, summary="Update role")
def update_role(
        request: Request,
        *,
        db: Session = Depends(get_db),
        role_id: UUID = Path(..., description="The ID of the role to update"),
        role_in: RoleUpdate,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["update"]]))
):
    """
    Update a role.

    - Requires roles_update permission
    - Cannot update system roles
    """
    role = role_crud.get(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    # Ensure the role belongs to the current user's company
    if role.company_id != current_user.company_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    # Prevent updates to system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=400,
            detail="System roles cannot be modified"
        )

    # If updating name, check if it already exists
    if role_in.name and role_in.name != role.name:
        existing_role = role_crud.get_by_name(db, name=role_in.name, company_id=current_user.company_id)
        if existing_role:
            raise HTTPException(
                status_code=400,
                detail="A role with this name already exists"
            )

    # Update the role
    try:
        role = role_crud.update(db, db_obj=role, obj_in=role_in)
        return role
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.put("/{role_id}/permissions", response_model=RoleSchema, summary="Update role permissions")
def update_role_permissions(
        request: Request,
        *,
        db: Session = Depends(get_db),
        role_id: UUID = Path(..., description="The ID of the role to update"),
        permissions_update: RolePermissionsUpdate,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["manage_permissions"]]))
):
    """
    Add or remove permissions from a role.

    - Requires roles_manage_permissions permission
    - Cannot update system roles
    """
    role = role_crud.get(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    # Ensure the role belongs to the current user's company
    if role.company_id != current_user.company_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    # Prevent updates to system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=400,
            detail="System roles cannot be modified"
        )

    # Update permissions
    try:
        role = role_crud.update_permissions(
            db,
            db_obj=role,
            add_ids=permissions_update.add_permission_ids,
            remove_ids=permissions_update.remove_permission_ids
        )
        return role
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.delete("/{role_id}", response_model=RoleSchema, summary="Delete role")
def delete_role(
        request: Request,
        *,
        db: Session = Depends(get_db),
        role_id: UUID = Path(..., description="The ID of the role to delete"),
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["delete"]]))
):
    """
    Delete a role.

    - Requires roles_delete permission
    - Cannot delete system roles
    - Cannot delete roles that are assigned to users
    """
    role = role_crud.get(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    # Ensure the role belongs to the current user's company
    if role.company_id != current_user.company_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    # Check if the role is assigned to any users
    if role.users:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a role that is assigned to users"
        )

    # Delete the role
    try:
        role = role_crud.remove(db, id=role_id)
        return role
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )