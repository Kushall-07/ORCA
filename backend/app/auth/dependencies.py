"""FastAPI dependency enforcing a valid Clerk session on protected routes.

Clerk owns signup, login, password and session issuance - the frontend talks
to Clerk directly and this backend never sees a password. This dependency
only verifies the session token Clerk already issued (networkless when Clerk
caches its JWKS; a JWKS fetch otherwise) and resolves it to the app-side
Supabase profile (see ``app.auth.profiles``).
"""

from __future__ import annotations

from clerk_backend_api import AuthenticateRequestOptions
from clerk_backend_api.security.types import RequestState
from fastapi import HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool

from app.auth.clerk_client import get_clerk_client
from app.auth.profiles import Profile, get_or_create_profile
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)

_AUTH_SERVICE_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Authentication service temporarily unavailable.",
)


def _authenticate_sync(request: Request, authorized_parties: list[str]) -> RequestState:
    return get_clerk_client().authenticate_request(
        request,
        AuthenticateRequestOptions(authorized_parties=authorized_parties),
    )


def _lookup_email_sync(user_id: str) -> str:
    """Best-effort fallback when the session token itself carries no `email`
    claim (depends on the Clerk JWT template) - fetched once, only for a
    first-time profile, never on the hot path of an already-known user."""
    try:
        user = get_clerk_client().users.get(user_id=user_id)
    except Exception:  # noqa: BLE001 - a profile with a blank email beats a 500 here
        return ""
    match = next(
        (a.email_address for a in (user.email_addresses or []) if a.id == user.primary_email_address_id),
        None,
    )
    return match or ""


async def get_current_user(request: Request) -> Profile:
    settings = get_settings()
    if not settings.clerk_secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured on this server.",
        )
    try:
        state = await run_in_threadpool(_authenticate_sync, request, settings.cors_origins)
    except Exception as exc:  # noqa: BLE001 - never let a Clerk SDK/network hiccup
        # (JWKS fetch failure, transient network error, etc.) reach the client
        # as a raw 500 - the project-wide invariant is "no stack trace ever
        # reaches the client" (docs/architecture.md §5). Distinct from
        # _UNAUTHORIZED: the token may well be valid, we just couldn't check.
        logger.warning("Clerk authenticate_request failed: %s", exc)
        raise _AUTH_SERVICE_UNAVAILABLE from exc
    if not state.is_signed_in or state.payload is None:
        raise _UNAUTHORIZED
    user_id = state.payload.get("sub")
    if not user_id:
        raise _UNAUTHORIZED
    email = state.payload.get("email") or await run_in_threadpool(_lookup_email_sync, user_id)
    return await get_or_create_profile(user_id, email)
