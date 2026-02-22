from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_hr
from app.db.session import get_db
from app.models.user import User
from app.services.dashboard_service import hr_dashboard


router = APIRouter(prefix="/api/hr", tags=["hr-dashboard"])


@router.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_hr), db: Session = Depends(get_db)) -> dict:
    return hr_dashboard(db, hr_user=current_user)