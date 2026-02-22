from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_hr
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import meta_from_page
from app.schemas.job import JobApplicantsResponse
from app.services.job_service import applicants_for_job


router = APIRouter(prefix="/api/hr/job", tags=["hr-applicants"])


@router.get("/{job_id}/applicants", response_model=JobApplicantsResponse)
def applicants(
    job_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=50),
    sort_by: str = Query(default="eligibility"),
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> JobApplicantsResponse:
    items, meta = applicants_for_job(
        db,
        hr_user=current_user,
        job_id=job_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    return JobApplicantsResponse(items=items, meta=meta_from_page(meta))