from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class UserDirectory(BaseModel):
    """
    Central registry of users to map them to their respective company schemas
    This model is stored in the public schema
    """

    __tablename__ = "user_directory"

    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(255), nullable=False, unique=True, index=True)

    # Company relation
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    company = relationship("Company")

    # Store schema name for direct access
    schema_name = Column(String(63), nullable=False)

    def __repr__(self):
        return f"<UserDirectory {self.email} (schema: {self.schema_name})>"