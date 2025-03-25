from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    User as UserSchema,
    UserCreate,
    UserUpdate,
    UserWithPermissions
)
from app.crud.user import user as user_crud
from app.core.security import (
    get_current_active_user,
    check_user_permissions,
    get_password_hash
)
from app.core.permissions import permission_registry

router = APIRouter()

# Define permissions for this module
PERMISSIONS = {
    "create": "users_create",
    "read": "users_read",
    "update": "users_update",
    "delete": "users_delete",
    "manage_permissions": "users_manage_permissions"
}

# Define descriptions for permissions
PERMISSION_DESCRIPTIONS = {
    "users_create": "Allows creating new users in the system",
    "users_read": "Allows viewing user information",
    "users_update": "Allows updating user information",
    "users_delete": "Allows deleting users from the system",
    "users_manage_permissions": "Allows managing user roles and permissions"
}

# Register permissions with the registry
permission_registry.register_permissions("users", PERMISSIONS, PERMISSION_DESCRIPTIONS)


@router.get("/me", response_model=UserWithPermissions, summary="Get current user details")
def get_current_user_details(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    Get details of the currently authenticated user.

    Returns:
        User: Current user information including permissions
    """
    # You could load permissions dynamically based on the user's role
    # For now, we'll use a simplified approach
    permissions = current_user.get_permissions()

    # Convert model to dictionary and add permissions
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "name": current_user.name,
        "surname": current_user.surname,
        "telephone": current_user.telephone,
        "is_active": current_user.is_active,
        "role": current_user.role,
        "role_id": current_user.role_id,
        "permissions": permissions
    }

    return user_data


@router.get("/", response_model=List[UserSchema], summary="Get all users")
def get_users(
        request: Request,
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["read"]]))
):
    """
    Retrieve all users within the company.

    - Requires users_read permission
    - **skip**: Number of users to skip (pagination)
    - **limit**: Maximum number of users to return (pagination)
    """
    users = user_crud.get_multi(db, skip=skip, limit=limit)
    return users


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED, summary="Create new user")
def create_user(
        request: Request,
        *,
        db: Session = Depends(get_db),
        user_in: UserCreate,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["create"]]))
):
    """
    Create a new user within the company.

    - Requires users_create permission
    - Creates a new user in the current company schema
    - Also adds the user to the central user directory
    """
    # Check if user with same email or username already exists
    db_user = user_crud.get_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists"
        )

    # Create the user
    user = user_crud.create(db, obj_in=user_in, company_id=current_user.company_id)
    return user


@router.get("/{user_id}", response_model=UserSchema, summary="Get user by ID")
def get_user(
        request: Request,
        *,
        db: Session = Depends(get_db),
        user_id: UUID = Path(..., description="The ID of the user to get"),
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["read"]]))
):
    """
    Get a specific user by ID.

    - Requires users_read permission
    """
    user = user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserSchema, summary="Update user")
def update_user(
        request: Request,
        *,
        db: Session = Depends(get_db),
        user_id: UUID = Path(..., description="The ID of the user to update"),
        user_in: UserUpdate,
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["update"]]))
):
    """
    Update a user.

    - Requires users_update permission
    - Cannot update a user with higher privileges than the current user
    """
    user = user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Prevent regular users from updating admin users
    if user.role == UserRole.ADMIN and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Cannot update user with higher privileges"
        )

    # If updating email, check that it's not already in use
    if user_in.email and user_in.email != user.email:
        existing_user = user_crud.get_by_email(db, email=user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already in use"
            )

    user = user_crud.update(db, db_obj=user, obj_in=user_in)
    return user


@router.delete("/{user_id}", response_model=UserSchema, summary="Delete user")
def delete_user(
        request: Request,
        *,
        db: Session = Depends(get_db),
        user_id: UUID = Path(..., description="The ID of the user to delete"),
        current_user: User = Depends(get_current_active_user),
        _: Any = Depends(check_user_permissions([PERMISSIONS["delete"]]))
):
    """
    Delete a user.

    - Requires users_delete permission
    - Cannot delete a user with higher privileges than the current user
    - Cannot delete yourself
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own user account"
        )

    user = user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Prevent regular users from deleting admin users
    if user.role == UserRole.ADMIN and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Cannot delete user with higher privileges"
        )

    user = user_crud.delete(db, user_id=user_id)
    return user


@router.put("/me/password", response_model=dict, summary="Update current user password")
def update_current_user_password(
        request: Request,
        *,
        db: Session = Depends(get_db),
        password_update: dict = Body(..., example={"current_password": "oldpassword", "new_password": "newpassword"}),
        current_user: User = Depends(get_current_active_user)
):
    """
    Update password for the currently authenticated user.

    - Requires authentication
    - Validates the current password before allowing update
    """
    # Verify current password
    if not user_crud.authenticate(
            db, email=current_user.email, password=password_update.get("current_password")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Update to new password
    hashed_password = get_password_hash(password_update.get("new_password"))
    current_user.hashed_password = hashed_password
    db.add(current_user)
    db.commit()

    return {"message": "Password updated successfully"}