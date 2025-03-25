from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.crud.base import CRUDBase
from app.models.user import Role, Permission
from app.schemas.role import RoleCreate, RoleUpdate


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """
    CRUD operations for Role model
    """

    def get_by_name(self, db: Session, *, name: str, company_id: UUID) -> Optional[Role]:
        """
        Get a role by name within a company

        Args:
            db: Database session
            name: Role name
            company_id: Company ID

        Returns:
            Optional[Role]: Role instance if found, None otherwise
        """
        return db.query(Role).filter(
            Role.name == name,
            Role.company_id == company_id
        ).first()

    def get_multi_by_company(
            self, db: Session, *, company_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Role]:
        """
        Get multiple roles for a specific company with pagination

        Args:
            db: Database session
            company_id: Company ID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (pagination)

        Returns:
            List[Role]: List of role instances
        """
        return db.query(Role).filter(Role.company_id == company_id).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: RoleCreate, company_id: UUID) -> Role:
        """
        Create a new role with optional initial permissions

        Args:
            db: Database session
            obj_in: RoleCreate schema
            company_id: Company ID

        Returns:
            Role: Created role instance
        """
        # Create role object without permissions first
        db_obj = Role(
            name=obj_in.name,
            description=obj_in.description,
            is_system_role=obj_in.is_system_role,
            company_id=company_id
        )

        # Add to database to get an ID
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # Add permissions if specified
        if obj_in.permission_ids:
            permissions = db.query(Permission).filter(
                Permission.id.in_(obj_in.permission_ids),
                Permission.company_id == company_id
            ).all()

            db_obj.permissions.extend(permissions)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

        return db_obj

    def update(
            self, db: Session, *, db_obj: Role, obj_in: Union[RoleUpdate, Dict[str, Any]]
    ) -> Role:
        """
        Update a role's basic information (not permissions)

        Args:
            db: Database session
            db_obj: Role model instance
            obj_in: RoleUpdate schema or dict

        Returns:
            Role: Updated role instance
        """
        # Prevent updates to system roles
        if db_obj.is_system_role:
            raise ValueError("System roles cannot be modified")

        return super().update(db, db_obj=db_obj, obj_in=obj_in)

    def update_permissions(
            self, db: Session, *, db_obj: Role, add_ids: List[UUID] = None, remove_ids: List[UUID] = None
    ) -> Role:
        """
        Add or remove permissions from a role

        Args:
            db: Database session
            db_obj: Role model instance
            add_ids: List of permission IDs to add
            remove_ids: List of permission IDs to remove

        Returns:
            Role: Updated role instance
        """
        # Prevent updates to system roles
        if db_obj.is_system_role:
            raise ValueError("System roles cannot be modified")

        # Add permissions
        if add_ids:
            permissions_to_add = db.query(Permission).filter(
                Permission.id.in_(add_ids),
                Permission.company_id == db_obj.company_id
            ).all()

            for permission in permissions_to_add:
                if permission not in db_obj.permissions:
                    db_obj.permissions.append(permission)

        # Remove permissions
        if remove_ids:
            permissions_to_remove = db.query(Permission).filter(
                Permission.id.in_(remove_ids),
                Permission.company_id == db_obj.company_id
            ).all()

            for permission in permissions_to_remove:
                if permission in db_obj.permissions:
                    db_obj.permissions.remove(permission)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: UUID) -> Role:
        """
        Delete a role if it's not a system role

        Args:
            db: Database session
            id: Role ID

        Returns:
            Role: Deleted role instance
        """
        role = self.get(db, id=id)
        if not role:
            return None

        # Prevent deletion of system roles
        if role.is_system_role:
            raise ValueError("System roles cannot be deleted")

        return super().remove(db, id=id)


# Create an instance of the CRUD class
role = CRUDRole(Role)