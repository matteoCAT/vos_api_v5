from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Company(BaseModel):
    """
    Company model for multi-tenant architecture
    Companies are stored in the public schema and determine which schema to use for tenant data
    """

    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True, unique=True)
    schema_name = Column(String(63), nullable=False, unique=True)

    # Company information
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(255), nullable=True)

    # Contact information
    contact_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)

    # Company identifiers
    tax_id = Column(String(50), nullable=True)
    registration_number = Column(String(50), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    users = relationship("User", back_populates="company")

    def __repr__(self):
        return f"<Company {self.name}>"