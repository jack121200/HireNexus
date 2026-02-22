from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_candidate
from app.db.session import get_db
from app.models.user import User
from app.services.dashboard_service import candidate_dashboard


router = APIRouter(prefix="/api/candidate", tags=["candidate-dashboard"])


@router.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_candidate), db: Session = Depends(get_db)) -> dict:
    return candidate_dashboard(db, candidate=current_user)