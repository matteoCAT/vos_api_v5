from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    auth,
    companies,
    # Include other endpoints as needed
)

api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
# Include other routers as needed