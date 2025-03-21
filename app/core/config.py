from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from dotenv import load_dotenv
import os

# Load .env file explicitly to make variables available in os.environ
load_dotenv()


class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"

    # Security settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Database settings
    DATABASE_URL: str
    DEFAULT_SCHEMA: str = "public"  # Default schema to use

    # Multi-tenant settings
    ENABLE_MULTI_TENANCY: bool = True  # Enable or disable multi-tenancy
    CREATE_TENANT_SCHEMAS: bool = True  # Auto-create schemas for new tenants
    AUTO_UPDATE_TENANT_SCHEMAS: bool = True  # Auto-update tenant schemas on migration

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Meta info for Swagger
    PROJECT_NAME: str = "Restaurant Management API"
    DESCRIPTION: str = """
    Restaurant Management API helps manage restaurants and bars with features for
    managing users, products, recipes, and invoices.
    """
    VERSION: str = "0.1.0"

    # Use this configuration with Pydantic v2
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Create settings instance - will load values from environment variables
# which have been loaded from .env file by load_dotenv()
settings = Settings(
    SECRET_KEY=os.environ.get("SECRET_KEY"),
    ALGORITHM=os.environ.get("ALGORITHM"),
    ACCESS_TOKEN_EXPIRE_MINUTES=int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    DATABASE_URL=os.environ.get("DATABASE_URL"),
    DEFAULT_SCHEMA=os.environ.get("DEFAULT_SCHEMA", "public"),
    ENABLE_MULTI_TENANCY=os.environ.get("ENABLE_MULTI_TENANCY", "True").lower() == "true",
    CREATE_TENANT_SCHEMAS=os.environ.get("CREATE_TENANT_SCHEMAS", "True").lower() == "true",
    AUTO_UPDATE_TENANT_SCHEMAS=os.environ.get("AUTO_UPDATE_TENANT_SCHEMAS", "True").lower() == "true"
)