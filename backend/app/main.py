"""
FastAPI Main Application
Address Validation Platform with Authentication
FIXED: validators_admin import commented out (file has wrong content)
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.api.v1 import jobs, jobs_export, validation, health, admin, export
from backend.app.api.v1.batch_validation import router as batch_router
from backend.app.api.v1.enhanced_export import router as enhanced_export_router
from backend.app.api.v1.metrics import router as metrics_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.users import router as users_router
# from backend.app.api.v1.validators_admin import router as validators_router  # TEMPORARILY DISABLED - File has wrong content
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade address validation platform with authentication",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )

# Include routers
# Core routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])

# Authentication & User Management (NEW)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/v1/users", tags=["User Management"])
# app.include_router(validators_router, prefix="/api/v1/validators", tags=["Validator Configuration"])  # TEMPORARILY DISABLED

# Validation & Jobs
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(validation.router, prefix="/api/v1/validation", tags=["Validation"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

# Export routers
app.include_router(export.router, prefix="/api/v1", tags=["Export - Basic"])
app.include_router(batch_router, prefix="/api/v1/validation", tags=["Batch Validation"])
app.include_router(enhanced_export_router, prefix="/api/v1/export", tags=["Export - Enhanced"])


# Metrics router
app.include_router(metrics_router, prefix="/api/v1/metrics", tags=["Metrics"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "features": {
            "authentication": "enabled",
            "metrics": "enabled",
            "batch_processing": "enabled",
            "dynamic_validators": "temporarily_disabled"  # Changed from "enabled"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info("Authentication: Enabled (JWT-based)")
    logger.info("User Management: Enabled")
    logger.info("Dynamic Validators: Temporarily Disabled (validators_admin.py has wrong content)")
    logger.info(f"OSM Validator: {'Enabled' if settings.ENABLE_OSM_VALIDATOR else 'Disabled'}")
    logger.info(f"USPS API: {'Enabled' if settings.ENABLE_USPS_API else 'Disabled'}")
    logger.info("Batch Processing: Enabled (5 records per batch)")
    logger.info("Enhanced Export: Enabled (Complete CSV with Oracle format)")
    logger.info("Metrics System: Enabled (Real-time data quality tracking)")
    logger.info("Default Admin: username=admin, password=admin (CHANGE THIS!)")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.APP_NAME}...")

# Results and Export endpoints
from backend.app.api.v1 import jobs_export
app.include_router(jobs_export.router, prefix="/api/v1/jobs", tags=["jobs"])
