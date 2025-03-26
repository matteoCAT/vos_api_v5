from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
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
        print(f"Creating schema: {schema_name}")
        db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        db.commit()
        print(f"Schema {schema_name} created successfully")
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
        # Set search path to the company schema only (not public)
        print(f"Setting search path to {schema_name}")
        db.execute(text(f'SET search_path TO "{schema_name}"'))

        # Create all tables from the Base metadata
        # This requires all models to be imported before calling this function
        from app.models.user import User, Role, Permission, role_permissions
        from app.models.base import BaseModel

        # Create tables in the schema
        print(f"Creating tables in schema {schema_name}")

        # List the tables we want to create in company schemas
        tenant_tables = ["user", "role", "permission", "role_permissions"]

        for table_name in tenant_tables:
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                LIKE public."{table_name}" INCLUDING ALL
            )
            """
            print(f"Creating table {schema_name}.{table_name}")
            db.execute(text(create_table_sql))

        db.commit()
        print(f"Successfully created tables in schema {schema_name}")

        # No roles and permissions as requested

    except Exception as e:
        db.rollback()
        print(f"Error creating tables in schema {schema_name}: {e}")
        raise
    finally:
        # Reset search path
        db.execute(text('SET search_path TO public'))
        db.close()


def create_default_roles_and_permissions(db: Session, schema_name: str):
    """
    Create default roles and permissions for a new company schema
    """
    try:
        # Set search path to the schema
        db.execute(text(f'SET search_path TO "{schema_name}"'))

        # Get company_id from the schema name
        result = db.execute(text("SELECT id FROM public.company WHERE schema_name = :schema"),
                            {"schema": schema_name}).fetchone()
        if not result:
            return

        company_id = result[0]

        # Create admin role if it doesn't exist
        admin_role = db.execute(text("""
            INSERT INTO role (name, description, is_system_role, company_id)
            VALUES ('ADMIN', 'Administrator with full system access', TRUE, :company_id)
            ON CONFLICT (name, company_id) DO NOTHING
            RETURNING id
        """), {"company_id": company_id}).fetchone()

        # Create staff role if it doesn't exist
        staff_role = db.execute(text("""
            INSERT INTO role (name, description, is_system_role, company_id)
            VALUES ('STAFF', 'Staff with limited access', TRUE, :company_id)
            ON CONFLICT (name, company_id) DO NOTHING
            RETURNING id
        """), {"company_id": company_id}).fetchone()

        # Create basic permissions (simplified, you may want to create more)
        basic_permissions = [
            ('users_read', 'View Users', 'users', 'Allows viewing user information'),
            ('users_create', 'Create Users', 'users', 'Allows creating new users'),
            ('users_update', 'Update Users', 'users', 'Allows updating user information'),
            ('users_delete', 'Delete Users', 'users', 'Allows deleting users')
        ]

        for code, name, module, description in basic_permissions:
            db.execute(text("""
                INSERT INTO permission (code, name, module, description, company_id)
                VALUES (:code, :name, :module, :description, :company_id)
                ON CONFLICT (code, company_id) DO NOTHING
            """), {
                "code": code,
                "name": name,
                "module": module,
                "description": description,
                "company_id": company_id
            })

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error creating default roles and permissions in schema {schema_name}: {e}")
    finally:
        # Reset search path
        db.execute(text('SET search_path TO public'))