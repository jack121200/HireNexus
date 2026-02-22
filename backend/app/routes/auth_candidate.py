from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import AuthResponse, CandidateRegisterRequest, LoginRequest, UserPublic
from app.services import auth_service


router = APIRouter(prefix="/api/candidate", tags=["candidate-auth"])


def _user_public(user) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        role=user.role.value,
        full_name=user.full_name,
        company_id=user.company_id,
    )


@router.post("/register", response_model=AuthResponse)
def register(payload: CandidateRegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = auth_service.register_candidate(db, email=payload.email, password=payload.password, full_name=payload.full_name)
    result = auth_service.login(db, email=payload.email, password=payload.password)
    return AuthResponse(access_token=result.access_token, token_type=result.token_type, user=_user_public(result.user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    result = auth_service.login(db, email=payload.email, password=payload.password)
    return AuthResponse(access_token=result.access_token, token_type=result.token_type, user=_user_public(result.user))