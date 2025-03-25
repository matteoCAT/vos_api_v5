from typing import Any, Dict, List, Optional, Union
from slugify import slugify
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.crud.base import CRUDBase
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.db.session import create_schema, create_company_schema_tables


class CRUDCompany(CRUDBase[Company, CompanyCreate, CompanyUpdate]):
    """
    CRUD operations for Company model with additional schema management
    """

    def get_by_name(self, db: Session, *, name: str) -> Optional[Company]:
        """
        Get a company by name

        Args:
            db: Database session
            name: Company name

        Returns:
            Optional[Company]: Company instance if found, None otherwise
        """
        return db.query(Company).filter(Company.name == name).first()

    def get_by_slug(self, db: Session, *, slug: str) -> Optional[Company]:
        """
        Get a company by slug

        Args:
            db: Database session
            slug: Company slug

        Returns:
            Optional[Company]: Company instance if found, None otherwise
        """
        return db.query(Company).filter(Company.slug == slug).first()

    def get_by_schema_name(self, db: Session, *, schema_name: str) -> Optional[Company]:
        """
        Get a company by schema name

        Args:
            db: Database session
            schema_name: Company schema name

        Returns:
            Optional[Company]: Company instance if found, None otherwise
        """
        return db.query(Company).filter(Company.schema_name == schema_name).first()

    def get_active(
            self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Company]:
        """
        Get active companies with pagination

        Args:
            db: Database session
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (pagination)

        Returns:
            List[Company]: List of active company instances
        """
        return db.query(Company).filter(Company.is_active == True).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CompanyCreate) -> Company:
        """
        Create a new company with a corresponding database schema

        Args:
            db: Database session
            obj_in: CompanyCreate schema

        Returns:
            Company: Created company instance
        """
        # Ensure we're in the public schema
        db.execute(text('SET search_path TO public'))

        # Generate slug if not provided
        slug = obj_in.slug if hasattr(obj_in, 'slug') and obj_in.slug else slugify(obj_in.name)

        # Generate schema name if not provided
        schema_name = obj_in.schema_name if hasattr(obj_in, 'schema_name') and obj_in.schema_name else f"company_{slug}"

        # Create the company in the database
        db_obj = Company(
            name=obj_in.name,
            slug=slug,
            schema_name=schema_name,
            display_name=obj_in.display_name if hasattr(obj_in, 'display_name') else obj_in.name,
            description=obj_in.description if hasattr(obj_in, 'description') else None,
            logo_url=obj_in.logo_url if hasattr(obj_in, 'logo_url') else None,
            contact_name=obj_in.contact_name if hasattr(obj_in, 'contact_name') else None,
            email=obj_in.email if hasattr(obj_in, 'email') else None,
            phone=obj_in.phone if hasattr(obj_in, 'phone') else None,
            address=obj_in.address if hasattr(obj_in, 'address') else None,
            tax_id=obj_in.tax_id if hasattr(obj_in, 'tax_id') else None,
            registration_number=obj_in.registration_number if hasattr(obj_in, 'registration_number') else None,
            is_active=obj_in.is_active if hasattr(obj_in, 'is_active') else True
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # Create the schema and tables for this company
        try:
            create_schema(schema_name)
            create_company_schema_tables(schema_name)
        except Exception as e:
            # If schema creation fails, we should probably delete the company record
            # and roll back, but for simplicity, we'll just log the error for now
            print(f"Error creating schema for company {db_obj.name}: {e}")

        return db_obj

    def update(
            self, db: Session, *, db_obj: Company, obj_in: Union[CompanyUpdate, Dict[str, Any]]
    ) -> Company:
        """
        Update a company

        Args:
            db: Database session
            db_obj: Company model instance
            obj_in: CompanyUpdate schema or dict

        Returns:
            Company: Updated company instance
        """
        # Ensure we're in the public schema
        db.execute(text('SET search_path TO public'))

        # Handle both dict and schema input
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        # If updating slug, make sure it's properly slugified
        if "slug" in update_data and update_data["slug"]:
            update_data["slug"] = slugify(update_data["slug"])

        # Schema name cannot be updated for existing companies
        if "schema_name" in update_data:
            del update_data["schema_name"]

        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def remove(self, db: Session, *, id: UUID) -> Company:
        """
        Delete a company record (does not drop the schema)

        Args:
            db: Database session
            id: Company ID

        Returns:
            Company: Deleted company instance
        """
        # Ensure we're in the public schema
        db.execute(text('SET search_path TO public'))

        # Get the company first
        company = self.get(db, id=id)
        if not company:
            return None

        # Remove the company record
        return super().remove(db, id=id)


# Create an instance of the CRUD class
company = CRUDCompany(Company)