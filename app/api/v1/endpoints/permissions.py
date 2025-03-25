from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.role import (
    Permission as PermissionSchema,
    PermissionCreate,
    PermissionUpdate
)
from app.crud.permission import permission as permission_crud
from app.core.security import get_current_active_user, check_user_permissions
from app.core.permissions import permission_registry

router = APIRouter()

# Define permissions for this module
PERMISSIONS = {
    "create": "permissions_create",
    "read": "permissions_read",
    "update": "permissions_update",
    "delete": "permissions_delete"
}

# Define descriptions for permissions
PERMISSION_DESCRIPTIONS = {
    "permissions_create": "Allows creating new permissions in the system",
    "permissions_read": "Allows viewing permission information",
    "permissions_update": "Allows updating permission information",
    "permissions_delete": "Allows deleting permissions from the system"
}

# Register permissions with the registry
permission_registry.register_permissions("permissions", PERMISSIONS, PERMISSION_DESCRIPTIONS)


@router.get("/", response_model=List[PermissionSchema], summary="Get all permissions")
def get_permissions(
        request: Request,
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
        module: Optional[str] = None,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["read"]]))
):
    """
    Retrieve permissions within the company.

    - Requires roles_read permission
    - **skip**: Number of permissions to skip (pagination)
    - **limit**: Maximum number of permissions to return (pagination)
    - **module**: Optional filter by module name
    """
    if module:
        permissions = permission_crud.get_multi_by_module(
            db, company_id=current_user.company_id, module=module, skip=skip, limit=limit
        )
    else:
        permissions = permission_crud.get_multi_by_company(
            db, company_id=current_user.company_id, skip=skip, limit=limit
        )

    return permissions


@router.get("/modules", response_model=List[str], summary="Get all permission modules")
def get_permission_modules(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["read"]]))
):
    """
    Retrieve all unique module names for permissions.

    - Requires roles_read permission
    """
    modules = permission_crud.get_modules(db, company_id=current_user.company_id)
    return modules


@router.post("/", response_model=PermissionSchema, status_code=status.HTTP_201_CREATED, summary="Create new permission")
def create_permission(
        request: Request,
        *,
        db: Session = Depends(get_db),
        permission_in: PermissionCreate,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["create"]]))
):
    """
    Create a new permission.

    - Requires roles_manage_permissions permission
    """
    # Check if permission with same code already exists
    existing_permission = permission_crud.get_by_code(
        db, code=permission_in.code, company_id=current_user.company_id
    )

    if existing_permission:
        raise HTTPException(
            status_code=400,
            detail=f"Permission with code '{permission_in.code}' already exists"
        )

    # Create the permission
    try:
        permission = permission_crud.create(db, obj_in=permission_in, company_id=current_user.company_id)
        return permission
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.get("/{permission_id}", response_model=PermissionSchema, summary="Get permission by ID")
def get_permission(
        request: Request,
        *,
        db: Session = Depends(get_db),
        permission_id: UUID = Path(..., description="The ID of the permission to get"),
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["read"]]))
):
    """
    Get a specific permission by ID.

    - Requires roles_read permission
    """
    permission = permission_crud.get(db, id=permission_id)
    if not permission:
        raise HTTPException(
            status_code=404,
            detail="Permission not found"
        )

    # Ensure the permission belongs to the current user's company
    if permission.company_id != current_user.company_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return permission


@router.put("/{permission_id}", response_model=PermissionSchema, summary="Update permission")
def update_permission(
        request: Request,
        *,
        db: Session = Depends(get_db),
        permission_id: UUID = Path(..., description="The ID of the permission to update"),
        permission_in: PermissionUpdate,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["update"]]))
):
    """
    Update a permission.

    - Requires roles_manage_permissions permission
    - Cannot update the permission code
    """
    permission = permission_crud.get(db, id=permission_id)
    if not permission:
        raise HTTPException(
            status_code=404,
            detail="Permission not found"
        )

    # Ensure the permission belongs to the current user's company
    if permission.company_id != current_user.company_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    # Update the permission
    updated_permission = permission_crud.update(db, db_obj=permission, obj_in=permission_in)
    return updated_permission


@router.delete("/{permission_id}", response_model=PermissionSchema, summary="Delete permission")
def delete_permission(
        request: Request,
        *,
        db: Session = Depends(get_db),
        permission_id: UUID = Path(..., description="The ID of the permission to delete"),
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["delete"]]))
):
    """
    Delete a permission.

    - Requires roles_manage_permissions permission
    - Cannot delete permissions that are assigned to roles
    """
    permission = permission_crud.get(db, id=permission_id)
    if not permission:
        raise HTTPException(
            status_code=404,
            detail="Permission not found"
        )

    # Ensure the permission belongs to the current user's company
    if permission.company_id != current_user.company_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    # Check if the permission is assigned to any roles
    if permission.roles:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a permission that is assigned to roles"
        )

    # Delete the permission
    deleted_permission = permission_crud.remove(db, id=permission_id)
    return deleted_permission


@router.post("/initialize", response_model=Dict[str, Any], summary="Initialize permissions from registry")
def initialize_permissions(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["create"]]))
):
    """
    Initialize permissions from the registry.

    - Requires roles_manage_permissions permission
    - Creates any missing permissions defined in the application
    """
    # Get permission definitions from registry
    permission_definitions = permission_registry.get_permission_definitions()

    # Create permissions
    created_permissions = permission_crud.create_multi(
        db, permissions=permission_definitions, company_id=current_user.company_id
    )

    return {
        "message": f"Successfully initialized {len(created_permissions)} permissions",
        "created_count": len(created_permissions)
    }