from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.crud.base import CRUDBase
from app.models.user import Permission
from app.schemas.role import PermissionCreate, PermissionUpdate


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    """
    CRUD operations for Permission model
    """

    def get_by_code(self, db: Session, *, code: str, company_id: UUID) -> Optional[Permission]:
        """
        Get a permission by code within a company

        Args:
            db: Database session
            code: Permission code
            company_id: Company ID

        Returns:
            Optional[Permission]: Permission instance if found, None otherwise
        """
        return db.query(Permission).filter(
            Permission.code == code,
            Permission.company_id == company_id
        ).first()

    def get_multi_by_company(
            self, db: Session, *, company_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Permission]:
        """
        Get multiple permissions for a specific company with pagination

        Args:
            db: Database session
            company_id: Company ID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (pagination)

        Returns:
            List[Permission]: List of permission instances
        """
        return db.query(Permission).filter(
            Permission.company_id == company_id
        ).offset(skip).limit(limit).all()

    def get_multi_by_module(
            self, db: Session, *, company_id: UUID, module: str, skip: int = 0, limit: int = 100
    ) -> List[Permission]:
        """
        Get permissions for a specific module within a company

        Args:
            db: Database session
            company_id: Company ID
            module: Module/resource name
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (pagination)

        Returns:
            List[Permission]: List of permission instances
        """
        return db.query(Permission).filter(
            Permission.company_id == company_id,
            Permission.module == module
        ).offset(skip).limit(limit).all()

    def get_modules(self, db: Session, *, company_id: UUID) -> List[str]:
        """
        Get all unique module names for a company

        Args:
            db: Database session
            company_id: Company ID

        Returns:
            List[str]: List of unique module names
        """
        # Query distinct module names
        result = db.query(Permission.module).filter(
            Permission.company_id == company_id
        ).distinct().all()

        # Extract module names from result tuples
        return [r[0] for r in result]

    def create(self, db: Session, *, obj_in: PermissionCreate, company_id: UUID) -> Permission:
        """
        Create a new permission

        Args:
            db: Database session
            obj_in: PermissionCreate schema
            company_id: Company ID

        Returns:
            Permission: Created permission instance
        """
        # Check if permission with same code already exists for this company
        existing = self.get_by_code(db, code=obj_in.code, company_id=company_id)
        if existing:
            raise ValueError(f"Permission with code '{obj_in.code}' already exists for this company")

        # Create permission object
        db_obj = Permission(
            code=obj_in.code,
            name=obj_in.name,
            module=obj_in.module,
            description=obj_in.description,
            company_id=company_id
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_multi(self, db: Session, *, permissions: List[PermissionCreate], company_id: UUID) -> List[Permission]:
        """
        Create multiple permissions at once

        Args:
            db: Database session
            permissions: List of PermissionCreate schemas
            company_id: Company ID

        Returns:
            List[Permission]: List of created permission instances
        """
        created_permissions = []

        for perm_data in permissions:
            # Skip if permission with same code already exists
            existing = self.get_by_code(db, code=perm_data.code, company_id=company_id)
            if existing:
                continue

            # Create permission
            db_obj = Permission(
                code=perm_data.code,
                name=perm_data.name,
                module=perm_data.module,
                description=perm_data.description,
                company_id=company_id
            )

            db.add(db_obj)
            created_permissions.append(db_obj)

        db.commit()

        # Refresh all created permissions
        for perm in created_permissions:
            db.refresh(perm)

        return created_permissions


# Create an instance of the CRUD class
permission = CRUDPermission(Permission)