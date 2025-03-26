"""
Script to create tables in all company schemas or in a specific schema.
This is useful after adding new models or when tables weren't properly created.
"""
import sys
import os
import argparse
from sqlalchemy import text

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal, create_company_schema_tables


def create_all_company_tables():
    """
    Create tables in all company schemas
    """
    db = SessionLocal()
    try:
        # Get all company schemas
        companies = db.execute(text("""
            SELECT schema_name, name FROM company
        """)).fetchall()

        print(f"Found {len(companies)} companies")

        # Create tables for each company schema
        for schema_name, company_name in companies:
            print(f"Creating tables for company {company_name} in schema {schema_name}")
            create_company_schema_tables(schema_name)
            print(f"Successfully created tables for company {company_name}")

    finally:
        db.close()


def create_company_tables(schema_name: str):
    """
    Create tables in a specific company schema

    Args:
        schema_name: Name of the schema to create tables in
    """
    db = SessionLocal()
    try:
        # Verify schema exists
        exists = db.execute(text("""
            SELECT 1 FROM pg_namespace WHERE nspname = :schema
        """), {"schema": schema_name}).fetchone()

        if not exists:
            print(f"Error: Schema {schema_name} does not exist")
            return False

        print(f"Creating tables in schema {schema_name}")
        create_company_schema_tables(schema_name)
        print(f"Successfully created tables in schema {schema_name}")
        return True

    finally:
        db.close()


def main():
    """
    Main function to run table creation
    """
    parser = argparse.ArgumentParser(description='Create tables in company schemas')
    parser.add_argument('--schema', help='Specific schema to create tables in')
    parser.add_argument('--all', action='store_true', help='Create tables in all company schemas')

    args = parser.parse_args()

    if args.schema:
        create_company_tables(args.schema)
    elif args.all:
        create_all_company_tables()
    else:
        print("No action specified. Use --schema or --all.")
        parser.print_help()


if __name__ == "__main__":
    main()