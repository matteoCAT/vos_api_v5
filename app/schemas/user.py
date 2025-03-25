from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base schema for User data"""
    email: EmailStr
    username: str
    name: str
    surname: str
    telephone: str
    is_active: Optional[bool] = True
    role: Optional[UserRole] = UserRole.STAFF
    role_id: Optional[UUID] = None  # Changed to UUID type


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "name": "John",
                "surname": "Doe",
                "telephone": "+1234567890",
                "password": "securepassword",
                "role": "staff",
                "role_id": "550e8400-e29b-41d4-a716-446655440000",  # Example UUID
                "is_active": True
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    telephone: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    role_id: Optional[UUID] = None  # Changed to UUID type

    class Config:
        json_schema_extra = {
            "example": {
                "email": "updated@example.com",
                "username": "newusername",
                "name": "Updated",
                "surname": "Name",
                "telephone": "+9876543210",
                "role": "manager",
                "role_id": "550e8400-e29b-41d4-a716-446655440000",  # Example UUID
                "is_active": True
            }
        }


class UserInDBBase(UserBase):
    """Schema for User data as stored in DB"""
    id: UUID

    class Config:
        from_attributes = True


class User(UserInDBBase):
    """Schema for User data returned to client"""
    pass


class UserWithPermissions(User):
    """Schema for User data including their permissions"""
    permissions: List[str] = []