from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_hr
from app.db.session import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.common import meta_from_page
from app.schemas.job import JobBrowseResponse, JobCreateRequest, JobCreateResponse, JobResponse
from app.services.job_service import create_job, hr_jobs_summary
from app.services.ml.jd_parser import parse_jd_with_groq
from app.services.ml.score_cache import rescore_job_vs_all_candidates
from app.services.pagination import paginate


router = APIRouter(prefix="/api/hr/jobs", tags=["hr-jobs"])


def _job_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        hr_user_id=job.hr_user_id,
        company_id=job.company_id,
        title=job.title,
        description=job.description,
        responsibilities=job.responsibilities,
        required_skills=job.required_skills,
        extracted_required_skills=job.extracted_required_skills,
        minimum_experience_years=job.minimum_experience_years,
        education_requirement=job.education_requirement,
        location=job.location,
        employment_type=job.employment_type,
        status=job.status,
        created_at=job.created_at.isoformat(),
    )



def _trigger_jd_enrichment(job_id: int, description: str, db_session_factory) -> None:
    """Background task: parse JD with Groq and store parsed_jd on job."""
    try:
        db = next(db_session_factory())
        job: Job | None = db.get(Job, job_id)
        if job:
            parsed = parse_jd_with_groq(description)
            job.parsed_jd = parsed
            job.preferred_skills = parsed.get("preferred_skills", [])
            db.add(job)
            db.commit()
        db.close()
    except Exception:
        pass  # Non-fatal


@router.post("", response_model=JobCreateResponse)
def post_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    job = create_job(
        db,
        hr_user=current_user,
        title=payload.title,
        description=payload.description,
        responsibilities=payload.responsibilities,
        required_skills=payload.required_skills,
        minimum_experience_years=payload.minimum_experience_years,
        education_requirement=payload.education_requirement,
        location=payload.location,
        employment_type=payload.employment_type,
    )
    db.commit()
    db.refresh(job)
    # Background 1: parse JD with Groq to populate parsed_jd + preferred_skills
    background_tasks.add_task(_trigger_jd_enrichment, job.id, payload.description, get_db)
    # Background 2: compute match scores for all candidates against this new job
    background_tasks.add_task(rescore_job_vs_all_candidates, job_id=job.id, db_session_factory=get_db)
    return JobCreateResponse(job=_job_response(job))


@router.get("", response_model=JobBrowseResponse)
def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> JobBrowseResponse:
    stmt = (
        select(Job)
        .where(Job.hr_user_id == current_user.id)
        .order_by(Job.created_at.desc(), Job.id.desc())
    )
    jobs, meta = paginate(db, stmt, page=page, page_size=page_size)
    items = [_job_response(job).model_dump() for job in jobs]
    return JobBrowseResponse(items=items, meta=meta_from_page(meta))


@router.get("/summary")
def summary(current_user: User = Depends(get_current_hr), db: Session = Depends(get_db)) -> dict:
    return hr_jobs_summary(db, hr_user=current_user)