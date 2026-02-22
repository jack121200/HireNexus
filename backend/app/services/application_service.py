from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIError
from app.models.application import Application, ApplicationStatus
from app.models.interview import Interview, InterviewStatus, InterviewType
from app.models.job import Job
from app.models.user import User, UserRole
from app.services.chat_service import ensure_conversation_for_job
from app.services.ml import EligibilityResult, compute_eligibility
from app.services.notification_service import create_notification
from app.services.resume_service import get_resume


def serialize_application(application: Application) -> dict[str, Any]:
    return {
        "id": application.id,
        "candidate_user_id": application.candidate_user_id,
        "job_id": application.job_id,
        "resume_id": application.resume_id,
        "status": application.status.value,
        "eligibility_percentage": application.eligibility_percentage,
        "skill_match_percentage": application.skill_match_percentage,
        "experience_match_percentage": application.experience_match_percentage,
        "education_match_percentage": application.education_match_percentage,
        "semantic_similarity": application.semantic_similarity,
        "keyword_overlap": application.keyword_overlap,
        "missing_skills": application.missing_skills,
        "breakdown": application.eligibility_breakdown_json,
        "application_details": application.application_details,
        "created_at": application.created_at.isoformat(),
    }


def _existing_application(db: Session, *, candidate_user_id: int, job_id: int) -> Application | None:
    stmt = select(Application).where(
        Application.candidate_user_id == candidate_user_id,
        Application.job_id == job_id,
    )
    return db.scalar(stmt)


def _job_like(job: Job) -> dict[str, Any]:
    return {
        "description": job.description,
        "required_skills": job.required_skills,
        "minimum_experience_years": job.minimum_experience_years,
        "education_requirement": job.education_requirement,
    }


def _resume_like(resume) -> dict[str, Any]:
    return {
        "raw_text": resume.raw_text,
        "skills": resume.extracted_skills,
        "estimated_experience_years": resume.estimated_experience_years,
        "education_level": resume.education_level,
        "parsed_json": resume.parsed_json,
    }


def apply_to_job(
    db: Session,
    *,
    candidate: User,
    job: Job,
    resume_id: int,
    application_details: dict[str, Any] | None = None,
) -> tuple[Application, Interview, EligibilityResult, dict[str, Any], Any]:
    if candidate.role != UserRole.candidate:
        raise APIError(status_code=403, code="candidate_required", detail="Candidate role required")
    if job.status != "open":
        raise APIError(status_code=400, code="job_closed", detail="Job is not open for applications")

    existing = _existing_application(db, candidate_user_id=candidate.id, job_id=job.id)
    if existing:
        raise APIError(status_code=400, code="already_applied", detail="You have already applied to this job")

    resume = get_resume(db, resume_id=resume_id, user=candidate)

    eligibility = compute_eligibility(resume_like=_resume_like(resume), job_like=_job_like(job))

    application = Application(
        candidate_user_id=candidate.id,
        job_id=job.id,
        resume_id=resume.id,
        status=ApplicationStatus.applied,
        eligibility_percentage=eligibility.eligibility_percentage,
        skill_match_percentage=eligibility.skill_match_percentage,
        experience_match_percentage=eligibility.experience_match_percentage,
        education_match_percentage=eligibility.education_match_percentage,
        semantic_similarity=eligibility.semantic_similarity,
        keyword_overlap=eligibility.keyword_overlap,
        missing_skills=list(eligibility.missing_skills),
        eligibility_breakdown_json=eligibility.to_dict(),
        application_details=application_details or {},
    )
    db.add(application)
    db.flush()

    conversation = ensure_conversation_for_job(db, candidate=candidate, job=job)

    interview = Interview(
        candidate_user_id=candidate.id,
        hr_user_id=job.hr_user_id,
        application_id=application.id,
        job_id=job.id,
        resume_id=resume.id,
        type=InterviewType.ai,
        status=InterviewStatus.started,
        report_json={
            "eligibility": eligibility.to_dict(),
            "questions": [],
            "answers": [],
        },
        transcript="",
    )
    db.add(interview)
    db.flush()

    hr_notification = create_notification(
        db,
        user_id=job.hr_user_id,
        type="application_created",
        title="New Application Received",
        body=f"{candidate.full_name} applied for {job.title}",
        data={
            "application_id": application.id,
            "job_id": job.id,
            "candidate_user_id": candidate.id,
            "interview_id": interview.id,
        },
    )

    return application, interview, eligibility, {"id": conversation.id}, hr_notification


def get_application(db: Session, *, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if not application:
        raise APIError(status_code=404, code="application_not_found", detail="Application not found")
    return application


def assert_application_owner(db: Session, *, application: Application, user: User) -> None:
    if user.role == UserRole.candidate:
        if application.candidate_user_id != user.id:
            raise APIError(status_code=403, code="application_forbidden", detail="Forbidden")
        return

    if user.role == UserRole.hr:
        job = db.get(Job, application.job_id)
        if not job or job.hr_user_id != user.id:
            raise APIError(status_code=403, code="application_forbidden", detail="Forbidden")
        return

    raise APIError(status_code=403, code="application_forbidden", detail="Forbidden")


def update_application_status(
    db: Session,
    *,
    hr_user: User,
    application: Application,
    new_status: ApplicationStatus,
) -> tuple[Application, Any]:
    if hr_user.role != UserRole.hr:
        raise APIError(status_code=403, code="hr_required", detail="HR role required")

    job = db.get(Job, application.job_id)
    if not job or job.hr_user_id != hr_user.id:
        raise APIError(status_code=403, code="application_forbidden", detail="Forbidden")

    application.status = new_status
    db.add(application)
    db.flush()

    status_text = "shortlisted" if new_status == ApplicationStatus.shortlisted else "rejected"
    candidate_notification = create_notification(
        db,
        user_id=application.candidate_user_id,
        type=f"application_{status_text}",
        title=f"Application {status_text.title()}",
        body=f"Your application for {job.title} has been {status_text}.",
        data={"application_id": application.id, "job_id": job.id, "status": new_status.value},
    )

    return application, candidate_notification
