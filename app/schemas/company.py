from pydantic import BaseModel, EmailStr, HttpUrl, Field, validator
from typing import Optional
from uuid import UUID


class CompanyBase(BaseModel):
    """Base schema for Company data"""
    name: str = Field(..., description="Company name")
    slug: Optional[str] = Field(None, description="URL-friendly identifier")
    schema_name: Optional[str] = Field(None, description="Database schema name")
    display_name: Optional[str] = Field(None, description="Display name for UI")
    description: Optional[str] = Field(None, description="Company description")
    logo_url: Optional[str] = Field(None, description="URL to company logo")
    contact_name: Optional[str] = Field(None, description="Primary contact name")
    email: Optional[EmailStr] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    address: Optional[str] = Field(None, description="Company address")
    tax_id: Optional[str] = Field(None, description="Tax ID or VAT number")
    registration_number: Optional[str] = Field(None, description="Business registration number")
    is_active: Optional[bool] = Field(True, description="Whether the company is active")

    @validator('schema_name')
    def validate_schema_name(cls, v):
        """Validate schema_name to ensure it's a valid PostgreSQL schema name"""
        if v:
            # PostgreSQL schema names should be lowercase alphanumeric with underscores
            if not v.islower() or not all(c.isalnum() or c == '_' for c in v):
                raise ValueError("Schema name must be lowercase alphanumeric with underscores only")
            # Max length for PostgreSQL identifiers is 63 characters
            if len(v) > 63:
                raise ValueError("Schema name must be 63 characters or less")
        return v


class CompanyCreate(CompanyBase):
    """Schema for creating a new company"""
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Restaurants Inc",
                "slug": "acme-restaurants",
                "display_name": "ACME Restaurants",
                "description": "A chain of fine dining restaurants",
                "contact_name": "John Smith",
                "email": "contact@acmerestaurants.com",
                "phone": "+1234567890",
                "address": "123 Main St, Anytown, USA",
                "tax_id": "123456789",
                "registration_number": "REG123456",
                "is_active": True
            }
        }


class CompanyUpdate(BaseModel):
    """Schema for updating a company"""
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Restaurants Inc (Updated)",
                "display_name": "ACME Restaurants & Bars",
                "contact_name": "Jane Doe",
                "email": "jane@acmerestaurants.com",
                "is_active": True
            }
        }


class CompanyInDBBase(CompanyBase):
    """Schema for Company data as stored in DB"""
    id: UUID

    class Config:
        from_attributes = True


class Company(CompanyInDBBase):
    """Schema for Company data returned to client"""
    pass