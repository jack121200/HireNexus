from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIError
from app.core.dependencies import get_current_hr
from app.db.session import get_db
from app.models.application import Application
from app.models.interview import Interview, InterviewType
from app.models.user import User
from app.schemas.common import meta_from_page
from app.schemas.job import JobApplicantsResponse
from app.services.interview_service import build_interview_report_payload
from app.services.job_service import applicants_for_job, assert_job_owner, get_job


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


@router.get("/{job_id}/applicants/{application_id}/ai-interview-report")
def applicant_ai_interview_report(
    job_id: int,
    application_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> dict:
    job = get_job(db, job_id=job_id)
    assert_job_owner(job=job, hr_user=current_user)

    application = db.get(Application, application_id)
    if not application or application.job_id != job.id:
        raise APIError(status_code=404, code="application_not_found", detail="Application not found")

    interview_stmt = (
        select(Interview)
        .where(
            Interview.application_id == application.id,
            Interview.type == InterviewType.ai,
        )
        .order_by(Interview.id.desc())
        .limit(1)
    )
    interview = db.scalar(interview_stmt)
    if not interview:
        raise APIError(status_code=404, code="interview_not_found", detail="AI interview report not found")

    return {"report": build_interview_report_payload(interview)}
