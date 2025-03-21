from sqlalchemy import Boolean, Column, String, Enum, Table, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OWNER = "owner"
    MANAGER = "manager"
    SUPERVISOR = "supervisor"
    STAFF = "staff"


class Permission(str, enum.Enum):
    CREATE_USERS = "create_users"
    UPDATE_USERS = "update_users"
    DELETE_USERS = "delete_users"
    VIEW_USERS = "view_users"


# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', ForeignKey('role.id'), primary_key=True),
    Column('permission_name', String, primary_key=True)
)


class Role(BaseModel):
    """Role model for defining sets of permissions"""

    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    permissions = Column(String, nullable=True)  # Stored as comma-separated permission names
    users = relationship("User", back_populates="role_obj")

    # Company relation - roles belong to a specific company
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    company = relationship("Company")


class User(BaseModel):
    """User model for employees"""

    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    telephone = Column(String, nullable=False)
    role_id = Column(ForeignKey("role.id"), nullable=False)
    role_obj = relationship("Role", back_populates="users")
    role = Column(Enum(UserRole), default=UserRole.STAFF, nullable=False)
    is_active = Column(Boolean, default=True)
    refresh_token = Column(String, nullable=True)  # For storing refresh tokens
    last_login = Column(DateTime, nullable=True)

    # Company relation
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    company = relationship("Company", back_populates="users")