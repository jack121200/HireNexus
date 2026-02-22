from __future__ import annotations

from typing import Annotated

import re
from pydantic import BaseModel, BeforeValidator, Field


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email_relaxed(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("Invalid email format")
    return normalized


EmailStrRelaxed = Annotated[str, BeforeValidator(_validate_email_relaxed)]


class UserPublic(BaseModel):
    id: int
    email: EmailStrRelaxed
    role: str
    full_name: str
    company_id: int | None = None


class CandidateRegisterRequest(BaseModel):
    email: EmailStrRelaxed
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)


class HrRegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    company_name: str = Field(min_length=2, max_length=255)
    company_website: str = Field(min_length=3, max_length=255)
    email: EmailStrRelaxed
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStrRelaxed
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
