from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_candidate
from app.core.exceptions import APIError
from app.db.session import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import (
    ResumeAnalysisRequest,
    ResumeAnalysisResponse,
    ResumeDetailResponse,
    ResumeResponse,
    ResumeUploadResponse,
)
from app.services.ml import EligibilityResult
from app.services.resume_service import (
    analyze_resume_against_jd,
    create_resume,
    get_resume,
    list_resumes,
    set_primary_resume,
)


router = APIRouter(prefix="/api/candidate/resumes", tags=["candidate-resumes"])


def _resume_response(resume: Resume) -> ResumeResponse:
    return ResumeResponse(
        id=resume.id,
        file_name=resume.file_name,
        file_type=resume.file_type,
        is_primary=resume.is_primary,
        extracted_skills=resume.extracted_skills,
        estimated_experience_years=resume.estimated_experience_years,
        education_level=resume.education_level,
        created_at=resume.created_at.isoformat(),
    )


@router.get("", response_model=list[ResumeResponse])
def get_resumes(current_user: User = Depends(get_current_candidate), db: Session = Depends(get_db)) -> list[ResumeResponse]:
    resumes = list_resumes(db, user_id=current_user.id)
    return [_resume_response(resume) for resume in resumes]


@router.post("", response_model=ResumeUploadResponse)
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
    resume = create_resume(db, user=current_user, file=file)
    return ResumeUploadResponse(resume=_resume_response(resume))


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
def get_resume_detail(
    resume_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    resume = get_resume(db, resume_id=resume_id, user=current_user)
    base = _resume_response(resume)
    return ResumeDetailResponse(**base.model_dump(), raw_text=resume.raw_text, parsed=resume.parsed_json)


@router.get("/{resume_id}/download")
def download_resume(
    resume_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> FileResponse:
    resume = get_resume(db, resume_id=resume_id, user=current_user)
    file_path = Path(resume.file_path)
    if not file_path.exists():
        raise APIError(status_code=404, code="resume_file_missing", detail="Resume file not found")
    return FileResponse(
        path=str(file_path),
        filename=resume.file_name,
        media_type="application/octet-stream",
    )


@router.post("/{resume_id}/set-primary", response_model=ResumeUploadResponse)
def set_primary(
    resume_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
    resume = get_resume(db, resume_id=resume_id, user=current_user)
    resume = set_primary_resume(db, resume=resume)
    return ResumeUploadResponse(resume=_resume_response(resume))


@router.post("/{resume_id}/analyze", response_model=ResumeAnalysisResponse)
def analyze_resume(
    resume_id: int,
    payload: ResumeAnalysisRequest,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> ResumeAnalysisResponse:
    resume = get_resume(db, resume_id=resume_id, user=current_user)
    result: EligibilityResult = analyze_resume_against_jd(
        db,
        resume=resume,
        jd_text=payload.jd_text,
        required_skills=payload.required_skills,
        minimum_experience_years=payload.minimum_experience_years,
        education_requirement=payload.education_requirement,
    )
    return ResumeAnalysisResponse(resume_id=resume.id, eligibility=result.to_dict())
