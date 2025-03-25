from sqlalchemy import Boolean, Column, String, Enum, Table, ForeignKey, DateTime, UniqueConstraint
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


# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', ForeignKey('role.id'), primary_key=True),
    Column('permission_id', ForeignKey('permission.id'), primary_key=True)
)


class Permission(BaseModel):
    """Permission model for defining access rights"""

    code = Column(String, nullable=False)  # Unique permission code (e.g., "users_create")
    name = Column(String, nullable=False)  # Human-readable name (e.g., "Create Users")
    module = Column(String, nullable=False)  # Module/resource this permission belongs to (e.g., "users")
    description = Column(String, nullable=True)  # Description of what this permission allows

    # Company relation - permissions belong to a specific company
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    company = relationship("Company")

    # Ensure permission code is unique within a company
    __table_args__ = (
        UniqueConstraint('code', 'company_id', name='unique_permission_code_per_company'),
    )


class Role(BaseModel):
    """Role model for defining sets of permissions"""

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)  # Indicates if this is a non-modifiable system role
    users = relationship("User", back_populates="role_obj")

    # Many-to-many relationship with permissions through role_permissions table
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        backref="roles"
    )

    # Company relation - roles belong to a specific company
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    company = relationship("Company")

    # Ensure name is unique within a company
    __table_args__ = (
        UniqueConstraint('name', 'company_id', name='unique_role_name_per_company'),
    )


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

    def has_permission(self, permission_code: str) -> bool:
        """
        Check if user has a specific permission

        Args:
            permission_code: The permission code to check for

        Returns:
            bool: True if user has permission, False otherwise
        """
        # Admin role has all permissions
        if self.role == UserRole.ADMIN:
            return True

        # Check if the user's role has the permission
        if self.role_obj and self.role_obj.permissions:
            return any(p.code == permission_code for p in self.role_obj.permissions)

        return False

    def get_permissions(self) -> list:
        """
        Get all permissions for this user

        Returns:
            list: List of permission codes
        """
        # Admin role has all permissions (would need to be fetched from db in real implementation)
        if self.role == UserRole.ADMIN:
            return ["all"]

        # Return permissions from the user's role
        if self.role_obj and self.role_obj.permissions:
            return [p.code for p in self.role_obj.permissions]

        return []