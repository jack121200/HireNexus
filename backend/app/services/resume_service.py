from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import APIError
from app.services.ml.exceptions import FileReadError, ResumeParseError, ValidationError as MLValidationError
from app.models.resume import Resume
from app.models.user import User
from app.services.ml import EligibilityResult, ParsedResume, compute_eligibility, parse_resume


settings = get_settings()


def _extension(file_name: str) -> str:
    return Path(file_name).suffix.lower()


def validate_upload(file: UploadFile) -> str:
    ext = _extension(file.filename or "")
    if ext not in settings.upload_allowed_extensions:
        raise APIError(
            status_code=400,
            code="invalid_file_type",
            detail=f"Unsupported file type: {ext}",
            data={"allowed": sorted(settings.upload_allowed_extensions)},
        )
    return ext


def _safe_file_name(file_name: str) -> str:
    cleaned = file_name.replace(" ", "_")
    return "".join(ch for ch in cleaned if ch.isalnum() or ch in {"_", ".", "-"})


def save_resume_file(*, user: User, file: UploadFile) -> tuple[Path, str]:
    ext = validate_upload(file)

    user_dir = settings.upload_dir / "resumes" / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    safe_name = _safe_file_name(file.filename or f"resume{ext}")
    file_name = f"{timestamp}_{safe_name}"
    file_path = user_dir / file_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path, ext


def _unset_primary(db: Session, *, user_id: int) -> None:
    stmt = update(Resume).where(Resume.user_id == user_id, Resume.is_primary.is_(True)).values(is_primary=False)
    db.execute(stmt)


def create_resume(db: Session, *, user: User, file: UploadFile) -> Resume:
    file_path, ext = save_resume_file(user=user, file=file)

    try:
        parsed: ParsedResume = parse_resume(file_path=file_path, file_type=ext)
    except (FileReadError, ResumeParseError, MLValidationError) as exc:
        detail = getattr(exc, "message", str(exc))
        raise APIError(
            status_code=400,
            code="resume_parse_failed",
            detail=detail,
            data=getattr(exc, "details", {}),
        ) from exc
    parsed_payload = parsed.to_dict()

    _unset_primary(db, user_id=user.id)

    resume = Resume(
        user_id=user.id,
        file_name=file.filename or file_path.name,
        file_type=ext,
        file_path=str(file_path),
        raw_text=parsed.raw_text,
        parsed_json=parsed_payload,
        extracted_skills=list(parsed_payload.get("skills", [])),
        keywords=list(parsed_payload.get("keywords", [])),
        estimated_experience_years=parsed.estimated_experience_years,
        education_level=parsed.education_level,
        is_primary=True,
    )
    db.add(resume)
    db.flush()
    return resume


def list_resumes(db: Session, *, user_id: int) -> list[Resume]:
    stmt = (
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.is_primary.desc(), Resume.created_at.desc(), Resume.id.desc())
    )
    return db.execute(stmt).scalars().all()


def get_resume(db: Session, *, resume_id: int, user: User) -> Resume:
    resume = db.get(Resume, resume_id)
    if not resume or resume.user_id != user.id:
        raise APIError(status_code=404, code="resume_not_found", detail="Resume not found")
    return resume


def get_primary_resume(db: Session, *, user_id: int) -> Resume | None:
    stmt = (
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.is_primary.desc(), Resume.created_at.desc(), Resume.id.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def set_primary_resume(db: Session, *, resume: Resume) -> Resume:
    _unset_primary(db, user_id=resume.user_id)
    resume.is_primary = True
    db.add(resume)
    db.flush()
    return resume


def analyze_resume_against_jd(
    db: Session,
    *,
    resume: Resume,
    jd_text: str,
    required_skills: list[str] | None,
    minimum_experience_years: float | None,
    education_requirement: str | None,
) -> EligibilityResult:
    job_like = {
        "description": jd_text,
        "required_skills": required_skills or [],
        "minimum_experience_years": minimum_experience_years or 0.0,
        "education_requirement": education_requirement,
    }
    resume_like = {
        "raw_text": resume.raw_text,
        "skills": resume.extracted_skills,
        "estimated_experience_years": resume.estimated_experience_years,
        "education_level": resume.education_level,
        "parsed_json": resume.parsed_json,
    }

    result = compute_eligibility(resume_like=resume_like, job_like=job_like)

    parsed_json = dict(resume.parsed_json or {})
    snapshots: list[dict[str, Any]] = list(parsed_json.get("analysis_snapshots", []))
    snapshots.append(
        {
            "timestamp": time.time(),
            "jd_preview": jd_text[:200],
            "result": result.to_dict(),
        }
    )
    parsed_json["analysis_snapshots"] = snapshots[-20:]
    resume.parsed_json = parsed_json
    db.add(resume)
    db.flush()

    return result
