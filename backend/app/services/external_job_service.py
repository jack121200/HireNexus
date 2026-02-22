# file name is external_job_service.py
from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.user import User
from app.services.ml import compute_eligibility, extract_required_skills
from app.services.pagination import PageMeta
from app.services.resume_service import get_primary_resume, get_resume


logger = get_logger(__name__)


def _usajobs_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Host": "data.usajobs.gov",
        "User-Agent": settings.usajobs_user_agent,
        "Authorization-Key": settings.usajobs_api_key,
    }


def _safe_text(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _location_display(descriptor: dict[str, Any]) -> str | None:
    display = _safe_text(descriptor.get("PositionLocationDisplay"))
    if display:
        return display

    locations = descriptor.get("PositionLocation") or []
    parts: list[str] = []
    for loc in locations:
        city = _safe_text(loc.get("CityName"))
        state = _safe_text(loc.get("CountrySubDivisionCode"))
        country = _safe_text(loc.get("CountryCode"))
        combined = ", ".join([p for p in [city, state or country] if p])
        if combined:
            parts.append(combined)

    if parts:
        return "; ".join(parts[:3])

    remote = descriptor.get("RemoteIndicator")
    if isinstance(remote, str) and remote.lower() in {"true", "yes"}:
        return "Remote"
    if remote is True:
        return "Remote"
    return None


def _employment_type(descriptor: dict[str, Any]) -> str | None:
    schedules = descriptor.get("PositionSchedule") or []
    if schedules and isinstance(schedules, list):
        name = schedules[0].get("Name")
        if name:
            return _safe_text(name)
    return None


def _description_from_descriptor(descriptor: dict[str, Any]) -> str:
    user_area = descriptor.get("UserArea") or {}
    details = user_area.get("Details") or {}

    summary = _safe_text(details.get("JobSummary")) or _safe_text(descriptor.get("QualificationSummary"))
    duties = _safe_text(details.get("MajorDuties"))
    requirements = _safe_text(details.get("Requirements")) or _safe_text(details.get("QualificationSummary"))

    chunks = [chunk for chunk in [summary, duties, requirements] if chunk]
    return "\n\n".join(chunks) if chunks else _safe_text(descriptor.get("PositionTitle"))


def _apply_url(descriptor: dict[str, Any]) -> str | None:
    apply_uris = descriptor.get("ApplyURI") or []
    if isinstance(apply_uris, list) and apply_uris:
        return _safe_text(apply_uris[0])
    return _safe_text(descriptor.get("PositionURI")) or None


def _map_usajobs_item(
    descriptor: dict[str, Any],
    *,
    description: str,
    required_skills: list[str],
    eligibility: dict[str, Any] | None,
) -> dict[str, Any]:
    job_id = (
        _safe_text(descriptor.get("PositionID"))
        or _safe_text(descriptor.get("PositionURI"))
        or _safe_text(descriptor.get("PositionTitle"))
    )

    return {
        "id": f"usajobs:{job_id}",
        "source": "usajobs",
        "external": True,
        "title": _safe_text(descriptor.get("PositionTitle")) or "Untitled Role",
        "company": _safe_text(descriptor.get("OrganizationName")) or "USAJOBS",
        "location": _location_display(descriptor),
        "employment_type": _employment_type(descriptor),
        "description": description,
        "required_skills": required_skills,
        "minimum_experience_years": 0.0,
        "eligibility": eligibility,
        "application": None,
        "apply_url": _apply_url(descriptor),
        "posted_at": _safe_text(descriptor.get("PublicationStartDate")) or None,
        "closing_date": _safe_text(descriptor.get("ApplicationCloseDate")) or None,
    }


def _fetch_usajobs(
    *,
    keyword: str | None,
    location: str | None,
    page: int,
    page_size: int,
    job_category_code: str | None,
) -> tuple[list[dict[str, Any]], PageMeta]:
    settings = get_settings()
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 50)

    if not settings.usajobs_api_key or not settings.usajobs_user_agent:
        logger.info("usajobs_not_configured")
        return [], PageMeta(page=safe_page, page_size=safe_page_size, total=0)

    params: dict[str, Any] = {
        "Page": safe_page,
        "ResultsPerPage": safe_page_size,
    }

    kw = _safe_text(keyword or settings.usajobs_default_keyword)
    loc = _safe_text(location or settings.usajobs_default_location)
    category = _safe_text(job_category_code or settings.usajobs_default_job_category_code)

    if kw:
        params["Keyword"] = kw
    if loc:
        params["LocationName"] = loc
    if category:
        params["JobCategoryCode"] = category

    try:
        response = httpx.get(
            settings.usajobs_base_url,
            headers=_usajobs_headers(),
            params=params,
            timeout=settings.usajobs_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("usajobs_fetch_failed", error=str(exc))
        return [], PageMeta(page=safe_page, page_size=safe_page_size, total=0)

    search = payload.get("SearchResult") or {}
    total = int(search.get("SearchResultCountAll") or search.get("SearchResultCount") or 0)
    items = search.get("SearchResultItems") or []
    descriptors = [item.get("MatchedObjectDescriptor") or {} for item in items if isinstance(item, dict)]

    return descriptors, PageMeta(page=safe_page, page_size=safe_page_size, total=total)


def list_external_jobs_for_candidate(
    db: Session,
    *,
    candidate: User,
    resume_id: int | None,
    page: int,
    page_size: int,
    keyword: str | None = None,
    location: str | None = None,
    job_category_code: str | None = None,
) -> tuple[list[dict[str, Any]], PageMeta]:
    resume = get_resume(db, resume_id=resume_id, user=candidate) if resume_id else get_primary_resume(db, user_id=candidate.id)

    resume_like: dict[str, Any] | None = None
    if resume:
        resume_like = {
            "raw_text": resume.raw_text,
            "skills": resume.extracted_skills,
            "estimated_experience_years": resume.estimated_experience_years,
            "education_level": resume.education_level,
            "parsed_json": resume.parsed_json,
        }

    descriptors, meta = _fetch_usajobs(
        keyword=keyword,
        location=location,
        page=page,
        page_size=page_size,
        job_category_code=job_category_code,
    )

    jobs: list[dict[str, Any]] = []
    for descriptor in descriptors:
        description = _description_from_descriptor(descriptor)
        try:
            required_skills = extract_required_skills(description=description, explicit_required_skills=[])
        except Exception as exc:  # noqa: BLE001
            logger.warning("usajobs_skill_extract_failed", error=str(exc))
            required_skills = []
        job_like = {
            "description": description,
            "required_skills": required_skills,
            "minimum_experience_years": 0.0,
            "education_requirement": None,
        }

        eligibility = None
        if resume_like:
            try:
                eligibility = compute_eligibility(resume_like=resume_like, job_like=job_like).to_dict()
            except Exception as exc:  # noqa: BLE001
                logger.warning("usajobs_eligibility_failed", error=str(exc))

        jobs.append(
            _map_usajobs_item(
                descriptor,
                description=description,
                required_skills=required_skills,
                eligibility=eligibility,
            )
        )

    return jobs, meta
