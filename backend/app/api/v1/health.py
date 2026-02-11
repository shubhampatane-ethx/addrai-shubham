"""
Health Check API Endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.database import get_db
from backend.app.services.osm_validator import OSMNominatimValidator
from backend.app.core.config import settings
import redis

router = APIRouter()

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Complete health check
    Checks: API, Database, Redis, OSM Validator
    """
    status = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "osm_validator": "unknown"
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        status["database"] = "healthy"
    except Exception as e:
        status["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        status["redis"] = "healthy"
    except Exception as e:
        status["redis"] = f"unhealthy: {str(e)}"
    
    # Check OSM Validator
    if settings.ENABLE_OSM_VALIDATOR:
        try:
            validator = OSMNominatimValidator()
            if validator.health_check():
                status["osm_validator"] = "healthy"
            else:
                status["osm_validator"] = "unreachable"
        except Exception as e:
            status["osm_validator"] = f"error: {str(e)}"
    else:
        status["osm_validator"] = "disabled"
    
    # Overall status
    all_healthy = all(
        v == "healthy" or v == "disabled" 
        for v in status.values()
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": status,
        "environment": settings.ENVIRONMENT
    }

@router.get("/health/simple")
async def simple_health():
    """Simple health check - just returns 200 OK"""
    return {"status": "ok"}
