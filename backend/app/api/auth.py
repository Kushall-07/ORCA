"""``GET /auth/me`` - the current-user probe.

Signup, login, password reset and session issuance all happen on the
frontend directly against Clerk (see ``@clerk/clerk-react`` in ``frontend/``)
- this backend has no signup/login endpoints of its own and never sees a
password. This route only reports who an already-verified Clerk session
belongs to, for the frontend to display next to the sign-out control.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.profiles import Profile
from app.models.auth import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
async def me(user: Profile = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.clerk_user_id, email=user.email)
