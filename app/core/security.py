from datetime import datetime, timedelta, UTC
from typing import Any, Dict, Optional, Union
from uuid import UUID
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import TokenData, TokenPayload
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


def create_access_token(
        subject: Union[str, UUID], role: str, company_id: Union[str, UUID], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        subject: The subject of the token (typically user ID)
        role: The user's role
        company_id: The user's company ID
        expires_delta: Optional expiration time override

    Returns:
        str: JWT token string
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "company_id": str(company_id)
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
        subject: Union[str, int], role: str, company_id: Union[str, UUID]
) -> str:
    """
    Create a refresh token with longer expiration

    Args:
        subject: The subject of the token (typically user ID)
        role: The user's role
        company_id: The user's company ID

    Returns:
        str: JWT token string
    """
    expire = datetime.now(UTC) + timedelta(days=7)  # Refresh tokens typically last longer

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "company_id": str(company_id),
        "refresh": True
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash

    Args:
        plain_password: The plain-text password
        hashed_password: The hashed password

    Returns:
        bool: True if the password matches the hash
    """
    print(f'Hash: {get_password_hash(plain_password)}')
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password

    Args:
        password: The plain-text password

    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token and return its payload

    Args:
        token: JWT token string

    Returns:
        Dict: Token payload

    Raises:
        jwt.PyJWTError: If token is invalid
    """
    return jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )


def get_current_user(
        request: Request,
        db: Session = Depends(get_db),
        token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get the current authenticated user

    Args:
        request: FastAPI request
        db: Database session
        token: JWT token from authentication header

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: If authentication fails
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        if token_data.exp < int(datetime.now(UTC).timestamp()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Store company_id in request state for schema selection
        if hasattr(token_data, "company_id"):
            request.state.company_id = token_data.company_id

    except (jwt.PyJWTError, ValidationError) as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


def get_current_active_user(
        current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user

    Args:
        current_user: The current authenticated user

    Returns:
        User: The authenticated active user

    Raises:
        HTTPException: If the user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def check_user_permissions(required_permissions: list[str] = None):
    """
    Create a dependency to check if the current user has the required permissions

    Args:
        required_permissions: List of permission strings required

    Returns:
        Callable: A dependency function that checks permissions
    """

    def validate_permissions(current_user: User = Depends(get_current_user)):
        # Admin has all permissions
        if current_user.role == UserRole.ADMIN:
            return current_user

        # If specific permissions are required, check the user's permissions
        if required_permissions:
            for permission in required_permissions:
                if not current_user.has_permission(permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Not enough permissions. Missing: {permission}",
                    )

        return current_user

    return validate_permissions