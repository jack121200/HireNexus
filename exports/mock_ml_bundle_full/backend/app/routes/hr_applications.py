from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_hr
from app.db.session import get_db
from app.models.application import ApplicationStatus
from app.models.user import User
from app.schemas.application import ApplicationStatusUpdateRequest, ApplicationStatusUpdateResponse
from app.services.application_service import get_application, serialize_application, update_application_status
from app.services.dashboard_service import candidate_dashboard, hr_dashboard
from app.services.notification_service import get_unread_count, serialize_notification
from app.services.realtime import broadcast_user


router = APIRouter(prefix="/api/hr/applications", tags=["hr-applications"])


@router.post("/{application_id}/status", response_model=ApplicationStatusUpdateResponse)
async def update_status(
    application_id: int,
    payload: ApplicationStatusUpdateRequest,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> ApplicationStatusUpdateResponse:
    application = get_application(db, application_id=application_id)
    new_status = ApplicationStatus(payload.status)

    application, candidate_notification = update_application_status(
        db,
        hr_user=current_user,
        application=application,
        new_status=new_status,
    )

    db.commit()
    db.refresh(candidate_notification)

    candidate_unread = get_unread_count(db, user_id=application.candidate_user_id)
    await broadcast_user(
        user_id=application.candidate_user_id,
        event="notification.created",
        data={
            "notification": serialize_notification(candidate_notification),
            "unread_count": candidate_unread,
        },
    )

    # Dashboard updates for both users.
    candidate_user = db.get(User, application.candidate_user_id)
    if candidate_user:
        await broadcast_user(
            user_id=candidate_user.id,
            event="dashboard.updated",
            data={"summary": candidate_dashboard(db, candidate=candidate_user)},
        )

    await broadcast_user(
        user_id=current_user.id,
        event="dashboard.updated",
        data={"summary": hr_dashboard(db, hr_user=current_user)},
    )

    return ApplicationStatusUpdateResponse(application=serialize_application(application))