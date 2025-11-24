from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import SessionDep
from app.core.config import settings

router = APIRouter(tags=["admin"])


@router.get("/health")
async def health_check():
    """
    Liveness probe.
    
    Returns 200 if the service is running.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
    }


@router.get("/ready")
async def readiness_check(session: SessionDep = None):
    """
    Readiness probe.
    
    Checks connectivity to required services:
    - Database
    - Vector DB (TODO)
    """
    checks = {
        "database": False,
        "vector_db": False,
    }
    
    # Check database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        pass
    
    # TODO: Check vector DB connectivity
    # checks["vector_db"] = await check_vector_db()
    checks["vector_db"] = True  # Stub for now
    
    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503
    
    return {
        "status": "ready" if all_ready else "not ready",
        "checks": checks,
    }
