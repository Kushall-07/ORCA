"""HTTP API layer.

Aggregates the individual routers into a single ``api_router`` that
``app.main`` mounts. Phase 1 exposes only the health routes; ``POST /query`` and
friends are added in Phase 5.

``/health`` and ``/auth`` stay open (a health probe and the current-user
probe cannot themselves require a login - and login itself happens on the
frontend directly against Clerk, never through this backend). ``/gis`` and
``/reference`` also stay open: they are static/public geospatial and
reference-snapshot data with no user query content, and ``EvidencePanels``
links straight to the ``/reference/pfz`` and ``/reference/rsmc`` snapshot URLs
as plain anchors, which cannot carry an Authorization header. Every other
router - the actual interactive decision-support surface - requires a valid
Clerk session via ``get_current_user`` (see app.auth.dependencies).
"""

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.api.authority import router as authority_router
from app.api.auth import router as auth_router
from app.api.gis import router as gis_router
from app.api.health import router as health_router
from app.api.query import router as query_router
from app.api.replay import router as replay_router
from app.api.route_compare import router as route_compare_router
from app.api.whatif import router as whatif_router

api_router = APIRouter()
_require_login = [Depends(get_current_user)]

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(gis_router)
api_router.include_router(query_router, dependencies=_require_login)
api_router.include_router(whatif_router, dependencies=_require_login)
api_router.include_router(replay_router, dependencies=_require_login)
api_router.include_router(route_compare_router, dependencies=_require_login)
api_router.include_router(authority_router, dependencies=_require_login)

__all__ = ["api_router"]
