from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.user import User
from app.schemas.company import Company as CompanySchema, CompanyCreate, CompanyUpdate
from app.core.security import get_current_active_user
from app.db.session import get_db, create_schema, create_company_schema_tables
from app.crud.company import company as company_crud

router = APIRouter()


# Helper function to check if user has superuser permissions
def check_superuser_permissions(current_user: User):
    """
    Check if the current user has superuser permissions (permissions='all')
    """
    # For now, simply check if user has admin role or role with 'all' permissions
    if current_user.role != "ADMIN" and (
            not hasattr(current_user.role_obj, "permissions") or
            current_user.role_obj.permissions != "all"
    ):
        raise HTTPException(
            status_code=403,
            detail="Superuser privileges required for company management"
        )
    return current_user


@router.get("/", response_model=List[CompanySchema], summary="Get all companies")
def get_companies(
        request: Request,
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
        current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve all companies.

    - Requires superuser privileges
    - **skip**: Number of companies to skip (pagination)
    - **limit**: Maximum number of companies to return (pagination)
    - **active_only**: If true, only return active companies
    """
    # Check superuser permissions
    check_superuser_permissions(current_user)

    # Switch to public schema to access company table
    db.execute(text('SET search_path TO public'))

    if active_only:
        companies = company_crud.get_active(db, skip=skip, limit=limit)
    else:
        companies = company_crud.get_multi(db, skip=skip, limit=limit)
    return companies


@router.post("/", response_model=CompanySchema, summary="Create new company")
def create_company(
        request: Request,
        *,
        db: Session = Depends(get_db),
        company_in: CompanyCreate,
        current_user: User = Depends(get_current_active_user)
):
    """
    Create a new company.

    - Requires superuser privileges
    - Creates a new database schema for the company
    - Sets up all required tables in the new schema
    """
    # Check superuser permissions
    check_superuser_permissions(current_user)

    # Switch to public schema
    db.execute(text('SET search_path TO public'))

    # Check if company with same name or slug already exists
    existing_company = company_crud.get_by_name(db, name=company_in.name)
    if existing_company:
        raise HTTPException(
            status_code=400,
            detail="A company with this name already exists"
        )

    if company_in.slug:
        existing_company = company_crud.get_by_slug(db, slug=company_in.slug)
        if existing_company:
            raise HTTPException(
                status_code=400,
                detail="A company with this slug already exists"
            )

    # Create new company (this also creates the schema and tables)
    company = company_crud.create(db, obj_in=company_in)

    return company


@router.get("/{company_id}", response_model=CompanySchema, summary="Get company by ID")
def get_company(
        request: Request,
        *,
        db: Session = Depends(get_db),
        company_id: UUID = Path(..., description="The ID of the company to get"),
        current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific company by ID.

    - Requires superuser privileges
    """
    # Check superuser permissions
    check_superuser_permissions(current_user)

    # Switch to public schema
    db.execute(text('SET search_path TO public'))

    company = company_crud.get(db, id=company_id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )
    return company


@router.put("/{company_id}", response_model=CompanySchema, summary="Update company")
def update_company(
        request: Request,
        *,
        db: Session = Depends(get_db),
        company_id: UUID = Path(..., description="The ID of the company to update"),
        company_in: CompanyUpdate,
        current_user: User = Depends(get_current_active_user)
):
    """
    Update a company.

    - Requires superuser privileges
    - Cannot update schema_name (would break database structure)
    """
    # Check superuser permissions
    check_superuser_permissions(current_user)

    # Switch to public schema
    db.execute(text('SET search_path TO public'))

    company = company_crud.get(db, id=company_id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    # Prevent updates to schema_name
    if hasattr(company_in, "schema_name") and company_in.schema_name and company_in.schema_name != company.schema_name:
        raise HTTPException(
            status_code=400,
            detail="Cannot update schema_name for existing company"
        )

    # Check slug uniqueness if changing slug
    if company_in.slug and company_in.slug != company.slug:
        existing_company = company_crud.get_by_slug(db, slug=company_in.slug)
        if existing_company:
            raise HTTPException(
                status_code=400,
                detail="A company with this slug already exists"
            )

    company = company_crud.update(db, db_obj=company, obj_in=company_in)
    return company


@router.delete("/{company_id}", response_model=CompanySchema, summary="Delete company")
def delete_company(
        request: Request,
        *,
        db: Session = Depends(get_db),
        company_id: UUID = Path(..., description="The ID of the company to delete"),
        current_user: User = Depends(get_current_active_user)
):
    """
    Delete a company.

    - Requires superuser privileges
    - Does NOT delete the database schema for safety reasons
    - To completely remove company data, use the /drop-schema endpoint
    """
    # Check superuser permissions
    check_superuser_permissions(current_user)

    # Switch to public schema
    db.execute(text('SET search_path TO public'))

    company = company_crud.get(db, id=company_id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    company = company_crud.remove(db, id=company_id)
    return company


@router.post("/{company_id}/drop-schema", response_model=dict, summary="Drop company schema")
def drop_company_schema(
        request: Request,
        *,
        db: Session = Depends(get_db),
        company_id: UUID = Path(..., description="The ID of the company schema to drop"),
        confirm: bool = Query(False, description="Confirmation flag for schema deletion"),
        current_user: User = Depends(get_current_active_user)
):
    """
    Drop the database schema for a company.

    - Requires superuser privileges
    - THIS OPERATION IS DESTRUCTIVE AND CANNOT BE UNDONE
    - Must set confirm=true query parameter to proceed
    """
    # Check superuser permissions
    check_superuser_permissions(current_user)

    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required for schema deletion. Set confirm=true query parameter."
        )

    # Switch to public schema
    db.execute(text('SET search_path TO public'))

    # Get company to find schema name
    company = company_crud.get(db, id=company_id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    schema_name = company.schema_name

    # Import drop_schema function
    from app.db.session import drop_schema

    # Drop the schema
    try:
        drop_schema(schema_name, cascade=True)
        return {"message": f"Schema {schema_name} dropped successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error dropping schema: {str(e)}"
        )