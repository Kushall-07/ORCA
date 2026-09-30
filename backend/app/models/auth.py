"""Response schema for the current-user probe."""

from __future__ import annotations

from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    email: str
