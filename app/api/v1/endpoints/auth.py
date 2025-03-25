from datetime import timedelta
import uuid
from fastapi import APIRouter, Body, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
import jwt
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_current_user
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import Login, Token, RefreshToken

router = APIRouter()


@router.post("/login", response_model=Token, summary="User login")
def login(
        request: Request,
        db: Session = Depends(get_db),
        form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticate a user with username (email) and password

    Returns:
        Token: Access and refresh token for authenticated user
    """
    # First find the user in the central directory (public schema)
    from app.models.user_directory import UserDirectory

    # Ensure we're in the public schema for the directory lookup
    db.execute(text('SET search_path TO public'))

    user_dir = db.query(UserDirectory).filter(
        (UserDirectory.email == form_data.username) |
        (UserDirectory.username == form_data.username)
    ).first()

    if not user_dir:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set the schema to the user's company schema
    db.execute(text(f'SET search_path TO {user_dir.schema_name}, public'))

    # Now find the actual user record in the company schema
    user = db.query(User).filter(
        (User.email == form_data.username) |
        (User.username == form_data.username)
    ).first()
    print(user.hashed_password)
    print(user)

    # Check if user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token with company_id
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        company_id=user.company_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Create refresh token with company_id
    refresh_token = create_refresh_token(
        subject=user.id,
        role=user.role,
        company_id=user.company_id
    )

    # Store refresh token in database
    user.refresh_token = refresh_token
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/login/json", response_model=Token, summary="User login with JSON")
def login_json(
        request: Request,
        login_data: Login,
        db: Session = Depends(get_db)
):
    """
    Authenticate a user with JSON payload containing email and password

    Returns:
        Token: Access and refresh token for authenticated user
    """
    # First find the user in the central directory (public schema)
    from app.models.user_directory import UserDirectory

    # Ensure we're in the public schema for the directory lookup
    db.execute(text('SET search_path TO public'))

    user_dir = db.query(UserDirectory).filter(UserDirectory.email == login_data.email).first()

    if not user_dir:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set the schema to the user's company schema
    db.execute(text(f'SET search_path TO {user_dir.schema_name}, public'))
    db.execute(text(f'SELECT * FROM {user_dir.schema_name}.user'))

    # Now find the actual user record in the company schema
    user = db.query(User).filter(User.email == login_data.email).first()

    # Check if user exists and password is correct
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token with company_id
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        company_id=user.company_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Create refresh token with company_id
    refresh_token = create_refresh_token(
        subject=user.id,
        role=user.role,
        company_id=user.company_id
    )

    # Store refresh token in database
    user.refresh_token = refresh_token
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token, summary="Refresh access token")
def refresh_token(
        request: Request,
        token_data: RefreshToken,
        db: Session = Depends(get_db)
):
    """
    Issue a new access token using a refresh token

    Returns:
        Token: New access and refresh tokens
    """
    try:
        # Decode the refresh token
        payload = jwt.decode(
            token_data.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Verify it's a refresh token
        if not payload.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid refresh token",
            )

        # Get the user ID from the token
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid refresh token",
            )

        # Get the company ID from the token
        company_id = payload.get("company_id")
        if company_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid refresh token - missing company_id",
            )

        # First, query the user_directory to find the right schema
        db.execute(text('SET search_path TO public'))

        from app.models.user_directory import UserDirectory
        user_dir = db.query(UserDirectory).filter(UserDirectory.company_id == company_id).first()

        if not user_dir:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid company information in token",
            )

        # Now switch to the correct company schema
        db.execute(text(f'SET search_path TO {user_dir.schema_name}, public'))

        # Get the user from the correct schema
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Verify the refresh token matches what's stored
        if user.refresh_token != token_data.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid refresh token",
            )

        # Create new access token with company_id
        access_token = create_access_token(
            subject=user.id,
            role=user.role,
            company_id=user.company_id
        )

        # Create new refresh token with company_id
        refresh_token = create_refresh_token(
            subject=user.id,
            role=user.role,
            company_id=user.company_id
        )

        # Update the refresh token in database
        user.refresh_token = refresh_token
        db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid refresh token",
        )


@router.post("/logout", summary="Logout and invalidate refresh token")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Logout the current user by invalidating their refresh token
    """
    # Clear the refresh token
    current_user.refresh_token = None
    db.commit()

    return {"message": "Successfully logged out"}