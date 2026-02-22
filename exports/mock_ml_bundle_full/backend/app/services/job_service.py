from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import APIError
from app.models.application import Application
from app.models.interview import Interview, InterviewType
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.services.ml import EligibilityResult, compute_eligibility, extract_required_skills
from app.services.pagination import paginate
from app.services.resume_service import get_primary_resume, get_resume


def create_job(
    db: Session,
    *,
    hr_user: User,
    title: str,
    description: str,
    responsibilities: str | None,
    required_skills: list[str],
    minimum_experience_years: float,
    education_requirement: str | None,
    location: str | None,
    employment_type: str | None,
) -> Job:
    if hr_user.role != UserRole.hr:
        raise APIError(status_code=403, code="hr_required", detail="HR role required")
    if not hr_user.company_id:
        raise APIError(status_code=400, code="company_missing", detail="HR user is not linked to a company")

    merged_required_skills = extract_required_skills(description=description, explicit_required_skills=required_skills)

    job = Job(
        hr_user_id=hr_user.id,
        company_id=hr_user.company_id,
        title=title.strip(),
        description=description.strip(),
        responsibilities=responsibilities.strip() if responsibilities else None,
        required_skills=required_skills,
        extracted_required_skills=merged_required_skills,
        minimum_experience_years=minimum_experience_years,
        education_requirement=education_requirement.strip() if education_requirement else None,
        location=location.strip() if location else None,
        employment_type=employment_type.strip() if employment_type else None,
        status="open",
    )
    db.add(job)
    db.flush()
    return job


def get_job(db: Session, *, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise APIError(status_code=404, code="job_not_found", detail="Job not found")
    return job


def assert_job_owner(*, job: Job, hr_user: User) -> None:
    if hr_user.role != UserRole.hr or job.hr_user_id != hr_user.id:
        raise APIError(status_code=403, code="job_forbidden", detail="Forbidden")


def _application_map(db: Session, *, candidate_user_id: int, job_ids: list[int]) -> dict[int, Application]:
    if not job_ids:
        return {}
    stmt = select(Application).where(
        Application.candidate_user_id == candidate_user_id,
        Application.job_id.in_(job_ids),
    )
    applications = db.execute(stmt).scalars().all()
    return {app.job_id: app for app in applications}


def _eligibility_for_job(*, resume: Resume | None, job: Job) -> EligibilityResult | None:
    if not resume:
        return None

    job_like = {
        "description": job.description,
        "required_skills": job.required_skills,
        "minimum_experience_years": job.minimum_experience_years,
        "education_requirement": job.education_requirement,
    }
    resume_like = {
        "raw_text": resume.raw_text,
        "skills": resume.extracted_skills,
        "estimated_experience_years": resume.estimated_experience_years,
        "education_level": resume.education_level,
        "parsed_json": resume.parsed_json,
    }
    return compute_eligibility(resume_like=resume_like, job_like=job_like)


def list_jobs_for_candidate(
    db: Session,
    *,
    candidate: User,
    resume_id: int | None,
    page: int,
    page_size: int,
):
    if candidate.role != UserRole.candidate:
        raise APIError(status_code=403, code="candidate_required", detail="Candidate role required")

    resume = get_resume(db, resume_id=resume_id, user=candidate) if resume_id else get_primary_resume(db, user_id=candidate.id)

    stmt = (
        select(Job)
        .where(Job.status == "open")
        .order_by(Job.created_at.desc(), Job.id.desc())
    )
    jobs, meta = paginate(db, stmt, page=page, page_size=page_size)

    job_ids = [job.id for job in jobs]
    application_map = _application_map(db, candidate_user_id=candidate.id, job_ids=job_ids)

    payload: list[dict[str, Any]] = []
    for job in jobs:
        eligibility = _eligibility_for_job(resume=resume, job=job)
        application = application_map.get(job.id)
        payload.append(
            {
                "id": job.id,
                "title": job.title,
                "location": job.location,
                "employment_type": job.employment_type,
                "description": job.description,
                "responsibilities": job.responsibilities,
                "required_skills": job.required_skills,
                "minimum_experience_years": job.minimum_experience_years,
                "education_requirement": job.education_requirement,
                "company_id": job.company_id,
                "eligibility": eligibility.to_dict() if eligibility else None,
                "application": {
                    "id": application.id,
                    "status": application.status.value,
                    "eligibility_percentage": application.eligibility_percentage,
                }
                if application
                else None,
                "created_at": job.created_at.isoformat(),
            }
        )

    return payload, meta


def hr_jobs_summary(db: Session, *, hr_user: User) -> dict[str, Any]:
    if hr_user.role != UserRole.hr:
        raise APIError(status_code=403, code="hr_required", detail="HR role required")

    jobs_stmt = select(func.count(Job.id)).where(Job.hr_user_id == hr_user.id)
    jobs_count = int(db.scalar(jobs_stmt) or 0)

    applications_stmt = (
        select(Job.id, Job.title, func.count(Application.id))
        .join(Application, Application.job_id == Job.id, isouter=True)
        .where(Job.hr_user_id == hr_user.id)
        .group_by(Job.id)
        .order_by(Job.created_at.desc())
    )
    application_counts = [
        {"job_id": job_id, "title": title, "applications": int(count)}
        for job_id, title, count in db.execute(applications_stmt).all()
    ]

    return {
        "jobs_posted": jobs_count,
        "applications_per_job": application_counts,
    }


def _latest_ai_interview_subquery():
    return (
        select(
            Interview.application_id.label("application_id"),
            func.max(Interview.id).label("latest_interview_id"),
        )
        .where(Interview.type == InterviewType.ai)
        .group_by(Interview.application_id)
        .subquery()
    )


def _latest_mock_by_candidate(db: Session, *, candidate_ids: list[int]) -> dict[int, Interview]:
    if not candidate_ids:
        return {}
    latest_mock_subq = (
        select(Interview.candidate_user_id, func.max(Interview.id).label("latest_mock_id"))
        .where(Interview.type == InterviewType.mock, Interview.candidate_user_id.in_(candidate_ids))
        .group_by(Interview.candidate_user_id)
        .subquery()
    )

    stmt = select(Interview).join(
        latest_mock_subq,
        Interview.id == latest_mock_subq.c.latest_mock_id,
    )
    interviews = db.execute(stmt).scalars().all()
    return {interview.candidate_user_id: interview for interview in interviews}


def applicants_for_job(
    db: Session,
    *,
    hr_user: User,
    job_id: int,
    page: int,
    page_size: int,
    sort_by: str,
):
    job = get_job(db, job_id=job_id)
    assert_job_owner(job=job, hr_user=hr_user)

    latest_ai_subq = _latest_ai_interview_subquery()

    ai_score_expr = func.coalesce(Interview.overall_score, 0.0)

    order_expr = {
        "eligibility": Application.eligibility_percentage.desc(),
        "skill_match": Application.skill_match_percentage.desc(),
        "interview_score": ai_score_expr.desc(),
    }.get(sort_by, Application.eligibility_percentage.desc())

    stmt = (
        select(Application, Resume, Interview, User)
        .join(Resume, Resume.id == Application.resume_id)
        .join(User, User.id == Application.candidate_user_id)
        .join(latest_ai_subq, latest_ai_subq.c.application_id == Application.id, isouter=True)
        .join(Interview, Interview.id == latest_ai_subq.c.latest_interview_id, isouter=True)
        .where(Application.job_id == job.id)
        .order_by(order_expr, Application.id.desc())
    )

    rows, meta = paginate(db, stmt, page=page, page_size=page_size)

    # paginate() returns scalars; for multi-entity selects we need a manual approach.
    # Re-run with explicit execution to preserve tuple rows.
    paged_stmt = stmt.offset((meta.page - 1) * meta.page_size).limit(meta.page_size)
    rows = db.execute(paged_stmt).all()

    candidate_ids = [row[0].candidate_user_id for row in rows]
    mock_map = _latest_mock_by_candidate(db, candidate_ids=candidate_ids)

    payload: list[dict[str, Any]] = []
    for application, resume, ai_interview, candidate_user in rows:
        mock_interview = mock_map.get(application.candidate_user_id)
        payload.append(
            {
                "application": {
                    "id": application.id,
                    "status": application.status.value,
                    "eligibility_percentage": application.eligibility_percentage,
                    "skill_match_percentage": application.skill_match_percentage,
                    "experience_match_percentage": application.experience_match_percentage,
                    "education_match_percentage": application.education_match_percentage,
                    "missing_skills": application.missing_skills,
                    "created_at": application.created_at.isoformat(),
                },
                "candidate": {
                    "id": application.candidate_user_id,
                    "full_name": candidate_user.full_name,
                    "email": candidate_user.email,
                    "resume_id": application.resume_id,
                    "skills": resume.extracted_skills,
                    "estimated_experience_years": resume.estimated_experience_years,
                    "education_level": resume.education_level,
                },
                "ai_interview": {
                    "id": ai_interview.id if ai_interview else None,
                    "overall_score": ai_interview.overall_score if ai_interview else None,
                    "confidence_score": ai_interview.confidence_score if ai_interview else None,
                    "status": ai_interview.status.value if ai_interview else None,
                    "recording_url": ai_interview.recording_url if ai_interview else None,
                },
                "mock_interview": {
                    "id": mock_interview.id if mock_interview else None,
                    "overall_score": mock_interview.overall_score if mock_interview else None,
                    "confidence_score": mock_interview.confidence_score if mock_interview else None,
                    "status": mock_interview.status.value if mock_interview else None,
                },
            }
        )

    return payload, meta
