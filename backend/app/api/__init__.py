"""HTTP API layer.

Aggregates the individual routers into a single ``api_router`` that
``app.main`` mounts. Phase 1 exposes only the health routes; ``POST /query`` and
friends are added in Phase 5.
"""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.query import router as query_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(query_router)

__all__ = ["api_router"]
