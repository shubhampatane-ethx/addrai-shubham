"""
API v1 Package
Exposes all routers for the API v1
"""
from backend.app.api.v1 import (
    health,
    jobs,
    validation,
    admin,
    export
)

# New enhanced routers
try:
    from backend.app.api.v1.batch_validation import router as batch_validation_router
except ImportError:
    batch_validation_router = None

try:
    from backend.app.api.v1.enhanced_export import router as enhanced_export_router
except ImportError:
    enhanced_export_router = None

__all__ = [
    'health',
    'jobs',
    'validation',
    'admin',
    'export',
    'batch_validation_router',
    'enhanced_export_router'
]
