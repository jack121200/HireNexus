from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_candidate
from app.db.session import get_db
from app.models.user import User
from app.schemas.application import ApplyRequest, ApplyResponse
from app.schemas.common import meta_from_page
from app.schemas.job import JobBrowseResponse
from app.services.application_service import apply_to_job, serialize_application
from app.services.job_service import get_job, list_jobs_for_candidate
from app.services.notification_service import get_unread_count, serialize_notification
from app.services.realtime import broadcast_user


router = APIRouter(prefix="/api/candidate/jobs", tags=["candidate-jobs"])


@router.get("", response_model=JobBrowseResponse)
async def browse_jobs(
    resume_id: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> JobBrowseResponse:
    items, meta = list_jobs_for_candidate(
        db,
        candidate=current_user,
        resume_id=resume_id,
        page=page,
        page_size=page_size,
    )
    return JobBrowseResponse(items=items, meta=meta_from_page(meta))


@router.post("/{job_id}/apply", response_model=ApplyResponse)
async def apply(
    job_id: int,
    payload: ApplyRequest,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> ApplyResponse:
    job = get_job(db, job_id=job_id)

    application, interview, eligibility, conversation, hr_notification = apply_to_job(
        db,
        candidate=current_user,
        job=job,
        resume_id=payload.resume_id,
        application_details=payload.details,
    )

    # Commit before broadcasting so other sessions can observe the changes.
    db.commit()
    db.refresh(hr_notification)

    unread_count = get_unread_count(db, user_id=job.hr_user_id)
    await broadcast_user(
        user_id=job.hr_user_id,
        event="notification.created",
        data={
            "notification": serialize_notification(hr_notification),
            "unread_count": unread_count,
        },
    )

    return ApplyResponse(
        application=serialize_application(application),
        interview_id=interview.id,
        conversation_id=conversation["id"],
        eligibility=eligibility.to_dict(),
    )
