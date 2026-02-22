from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import APIError
from app.models.application import Application, ApplicationStatus
from app.models.interview import Interview, InterviewStatus, InterviewType
from app.models.job import Job
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.services.ml import compute_eligibility
from app.services.resume_service import get_primary_resume


def _resume_score(db: Session, *, candidate: User) -> float:
    resume = get_primary_resume(db, user_id=candidate.id)
    if not resume:
        return 0.0

    jobs_stmt = (
        select(Job)
        .where(Job.status == "open")
        .order_by(Job.created_at.desc(), Job.id.desc())
        .limit(20)
    )
    jobs = db.execute(jobs_stmt).scalars().all()
    if not jobs:
        return 0.0

    resume_like = {
        "raw_text": resume.raw_text,
        "skills": resume.extracted_skills,
        "estimated_experience_years": resume.estimated_experience_years,
        "education_level": resume.education_level,
        "parsed_json": resume.parsed_json,
    }

    scores: list[float] = []
    for job in jobs:
        job_like = {
            "description": job.description,
            "required_skills": job.required_skills,
            "minimum_experience_years": job.minimum_experience_years,
            "education_requirement": job.education_requirement,
        }
        result = compute_eligibility(resume_like=resume_like, job_like=job_like)
        scores.append(result.eligibility_percentage)

    return round(sum(scores) / len(scores), 2) if scores else 0.0


def candidate_dashboard(db: Session, *, candidate: User) -> dict[str, Any]:
    if candidate.role != UserRole.candidate:
        raise APIError(status_code=403, code="candidate_required", detail="Candidate role required")

    resume_score = _resume_score(db, candidate=candidate)

    applied_stmt = select(func.count(Application.id)).where(Application.candidate_user_id == candidate.id)
    shortlisted_stmt = select(func.count(Application.id)).where(
        Application.candidate_user_id == candidate.id,
        Application.status == ApplicationStatus.shortlisted,
    )

    interviews_stmt = select(Interview).where(
        Interview.candidate_user_id == candidate.id,
        Interview.status == InterviewStatus.completed,
    )
    interviews = db.execute(interviews_stmt).scalars().all()

    ai_scores = [i.overall_score for i in interviews if i.type == InterviewType.ai]
    mock_scores = [i.overall_score for i in interviews if i.type == InterviewType.mock]

    notifications_stmt = select(func.count(Notification.id)).where(
        Notification.user_id == candidate.id,
        Notification.is_read.is_(False),
    )

    return {
        "resume_score": resume_score,
        "jobs_applied": int(db.scalar(applied_stmt) or 0),
        "jobs_shortlisted": int(db.scalar(shortlisted_stmt) or 0),
        "interview_performance": {
            "ai_average": round(sum(ai_scores) / len(ai_scores), 2) if ai_scores else 0.0,
            "mock_average": round(sum(mock_scores) / len(mock_scores), 2) if mock_scores else 0.0,
            "total_completed": len(interviews),
        },
        "notifications_unread": int(db.scalar(notifications_stmt) or 0),
    }


def hr_dashboard(db: Session, *, hr_user: User) -> dict[str, Any]:
    if hr_user.role != UserRole.hr:
        raise APIError(status_code=403, code="hr_required", detail="HR role required")

    job_ids_stmt = select(Job.id).where(Job.hr_user_id == hr_user.id)

    jobs_posted_stmt = select(func.count(Job.id)).where(Job.hr_user_id == hr_user.id)

    applications_total_stmt = select(func.count(Application.id)).where(Application.job_id.in_(job_ids_stmt))
    shortlisted_stmt = select(func.count(Application.id)).where(
        Application.job_id.in_(job_ids_stmt),
        Application.status == ApplicationStatus.shortlisted,
    )
    rejected_stmt = select(func.count(Application.id)).where(
        Application.job_id.in_(job_ids_stmt),
        Application.status == ApplicationStatus.rejected,
    )

    interviews_completed_stmt = select(func.count(Interview.id)).where(
        Interview.job_id.in_(job_ids_stmt),
        Interview.status == InterviewStatus.completed,
    )

    notifications_unread_stmt = select(func.count(Notification.id)).where(
        Notification.user_id == hr_user.id,
        Notification.is_read.is_(False),
    )

    return {
        "jobs_posted": int(db.scalar(jobs_posted_stmt) or 0),
        "applications_total": int(db.scalar(applications_total_stmt) or 0),
        "shortlisted": int(db.scalar(shortlisted_stmt) or 0),
        "rejected": int(db.scalar(rejected_stmt) or 0),
        "interviews_completed": int(db.scalar(interviews_completed_stmt) or 0),
        "notifications_unread": int(db.scalar(notifications_unread_stmt) or 0),
    }
