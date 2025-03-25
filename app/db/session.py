from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Request

from app.core.config import settings

# Create a database engine
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Create a custom session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()


# Dependency to get DB session with schema selection
def get_db(request: Request = None):
    """
    Get database session with schema selection based on tenant

    If request is provided and has schema_name in state, the search_path
    is set to that schema followed by the public schema.

    For authentication routes, this defaults to the public schema first,
    then the respective endpoints will switch to the proper tenant schema
    once the user is identified from the central registry.
    """
    db = SessionLocal()
    try:
        # For authentication endpoints, start in public schema
        # Authentication endpoints will switch schemas after user lookup
        if request and request.url.path.endswith(('/login', '/login/json', '/refresh')):
            db.execute(text('SET search_path TO public'))
        # Set schema if request contains schema information
        elif request and hasattr(request.state, "schema_name"):
            schema_name = request.state.schema_name
            # Set the search_path to the tenant schema followed by public
            db.execute(text(f'SET search_path TO "{schema_name}", public'))
        else:
            # Default to public schema only
            db.execute(text(f'SET search_path TO "{settings.DEFAULT_SCHEMA}"'))

        yield db
    finally:
        db.close()


# Helper function to create a new schema
def create_schema(schema_name: str):
    """
    Create a new PostgreSQL schema
    """
    db = SessionLocal()
    try:
        # Create the schema if it doesn't exist
        db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error creating schema: {e}")
        raise
    finally:
        db.close()


# Helper function to drop a schema
def drop_schema(schema_name: str, cascade: bool = False):
    """
    Drop a PostgreSQL schema

    Args:
        schema_name: Name of the schema to drop
        cascade: If True, automatically drop objects in the schema
    """
    db = SessionLocal()
    try:
        if cascade:
            db.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        else:
            db.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}"'))
        db.commit()
    finally:
        db.close()


# Helper function to generate company schema tables
def create_company_schema_tables(schema_name: str):
    """
    Create tables in a specific company schema
    """
    db = SessionLocal()
    try:
        # Set search path to the company schema
        db.execute(text(f'SET search_path TO "{schema_name}"'))

        # Create all tables from the Base metadata
        # This requires all models to be imported before calling this function
        from app.models.base import BaseModel

        # Create only tables that should be in tenant schemas
        # (exclude Company and other global models)
        tenant_metadata = BaseModel.metadata.tables.copy()

        # Remove tables that should remain in public schema
        public_tables = ["company", "user_directory"]
        for table_name in public_tables:
            if table_name in tenant_metadata:
                del tenant_metadata[table_name]

        # Create tables in the tenant schema
        for table in tenant_metadata.values():
            table_creation_sql = str(table.schema(schema_name))
            db.execute(text(table_creation_sql))

        db.commit()
    finally:
        # Reset search path
        db.execute(text('SET search_path TO public'))
        db.close()