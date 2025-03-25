from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    auth,
    companies,
    users, roles, permissions
    # Include other endpoints as needed
)

api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])