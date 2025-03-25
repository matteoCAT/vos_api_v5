"""
Script to manage tenant schemas in the database.
This script can be used to:
- Create new schemas for all companies
- Update existing schemas with new tables
- Remove orphaned schemas
"""
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError
from sqlalchemy import text

from app.db.session import SessionLocal, create_schema, drop_schema, create_company_schema_tables
from app.models.company import Company
from app.core.config import settings


def get_all_database_schemas() -> list:
    """
    Get all schemas in the PostgreSQL database
    Returns a list of schema names
    """
    db = SessionLocal()
    try:
        # Query information_schema.schemata to get all schemas
        result = db.execute(text("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
            AND schema_name NOT LIKE 'pg_toast%'
            AND schema_name NOT LIKE 'pg_temp%'
        """))
        schemas = [row[0] for row in result]
        return schemas
    finally:
        db.close()


def setup_company_schemas():
    """
    Create or update schemas for all companies
    """
    db = SessionLocal()
    try:
        # Get all companies
        companies = db.query(Company).all()

        print(f"Found {len(companies)} companies")

        # Create or update schema for each company
        for company in companies:
            schema_name = company.schema_name

            # Check if schema exists
            try:
                db.execute(f"SELECT 1 FROM pg_namespace WHERE nspname = '{schema_name}'")
                schema_exists = bool(db.fetchone())
            except ProgrammingError:
                schema_exists = False

            # Create schema if it doesn't exist
            if not schema_exists:
                print(f"Creating schema for company {company.name}: {schema_name}")
                create_schema(schema_name)
                create_company_schema_tables(schema_name)

                # Schema created successfully
                print(f"Successfully created schema {schema_name} for company {company.name}")
            else:
                print(f"Schema for company {company.name} already exists: {schema_name}")

                # TODO: Check if schema needs updating
                # This would involve comparing the tables in the schema with the current model definitions
    finally:
        db.close()


def cleanup_orphaned_schemas(dry_run=True):
    """
    Remove schemas that don't belong to any company

    Args:
        dry_run: If True, only print actions without actually removing schemas
    """
    db = SessionLocal()
    try:
        # Get all schemas in the database
        all_schemas = get_all_database_schemas()

        # Get all company schemas from the companies table
        companies = db.query(Company).all()
        company_schemas = [company.schema_name for company in companies]

        # Always preserve these schemas
        preserved_schemas = ['public']

        # Find orphaned schemas
        orphaned_schemas = [
            schema for schema in all_schemas
            if schema not in company_schemas and schema not in preserved_schemas
        ]

        print(f"Found {len(orphaned_schemas)} orphaned schemas")

        # Remove orphaned schemas
        for schema in orphaned_schemas:
            if dry_run:
                print(f"Would drop schema: {schema}")
            else:
                print(f"Dropping schema: {schema}")
                drop_schema(schema, cascade=True)

                # Schema dropped successfully
                print(f"Successfully dropped schema {schema}")

    finally:
        db.close()


def main():
    """
    Main function to run schema management tasks
    """
    import argparse

    parser = argparse.ArgumentParser(description='Manage tenant schemas')
    parser.add_argument('--setup', action='store_true', help='Create or update company schemas')
    parser.add_argument('--cleanup', action='store_true', help='Remove orphaned schemas')
    parser.add_argument('--apply', action='store_true', help='Apply schema changes to all tenants')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t actually make changes')

    args = parser.parse_args()

    if args.setup:
        print("Setting up company schemas...")
        setup_company_schemas()

    if args.cleanup:
        print("Cleaning up orphaned schemas...")
        cleanup_orphaned_schemas(dry_run=args.dry_run)

    if args.apply:
        print("Applying schema changes to all tenants...")
        # This would call a function to apply new migrations to existing schemas
        # Not implemented yet
        print("Not implemented yet")

    if not any([args.setup, args.cleanup, args.apply]):
        print("No action specified. Use --setup, --cleanup, or --apply.")
        parser.print_help()


if __name__ == "__main__":
    main()