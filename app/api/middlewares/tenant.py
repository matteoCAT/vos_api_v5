from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.core.security import decode_jwt_token
from app.models.company import Company  # We'll create this model next


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle schema selection based on tenant (company)
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # Extract token from authorization header
        token = self._extract_token(request)
        if not token:
            return await call_next(request)

        # Get company_id from token
        company_id = self._get_company_id_from_token(token)
        if not company_id:
            return await call_next(request)

        # Set company context in request state
        request.state.company_id = company_id

        # Attach schema name to the request state
        # This will be used in the get_db dependency to set the search_path
        schema_name = await self._get_schema_for_company(company_id)
        request.state.schema_name = schema_name

        # Continue with the request
        response = await call_next(request)
        return response

    def _should_skip_auth(self, path: str) -> bool:
        """Check if authentication should be skipped for this path"""
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            f"{settings.API_V1_STR}/auth/login",
            f"{settings.API_V1_STR}/auth/refresh",
            f"{settings.API_V1_STR}/health"
        ]

        return any(path.startswith(skip_path) for skip_path in skip_paths)

    def _extract_token(self, request: Request) -> str:
        """Extract JWT token from Authorization header"""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        return auth_header.replace("Bearer ", "")

    def _get_company_id_from_token(self, token: str):
        """Extract company_id from JWT token"""
        try:
            payload = decode_jwt_token(token)
            return payload.get("company_id")
        except Exception:
            return None

    async def _get_schema_for_company(self, company_id: str) -> str:
        """Get schema name for a company"""
        # Use a database session to look up the schema name
        db = SessionLocal()
        try:
            # Set to public schema first to query the company table
            db.execute(text('SET search_path TO public'))

            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return settings.DEFAULT_SCHEMA

            return company.schema_name or f"company_{company_id}"
        finally:
            db.close()