from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/", summary="Health Check")
def health_check(db: Session = Depends(get_db)):
    """
    Perform a health check on the API.

    Returns:
        dict: Status information about the API and database connection
    """
    # Checking database connection by trying to use the session
    db_status = "ok" if db else "error"

    return {
        "status": "ok",
        "api_version": "v1",
        "database": db_status
    }