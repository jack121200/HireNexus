"""Redis-backed eligibility score cache.

Pre-computes and caches candidate↔job match scores so the job listing
page reads instantly from Redis instead of recalculating on every request.

Cache key: eligibility:{candidate_user_id}:{job_id}
TTL: 86400 seconds (24 hours) — configurable via SCORE_CACHE_TTL env var
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_TTL = int(os.getenv("SCORE_CACHE_TTL", "86400"))
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_PREFIX = "eligibility"

# ── Redis connection (lazy) ───────────────────────────────────────────────────

_redis_client: Any = None


def _get_redis():
    """Lazy-init synchronous Redis client (redis-py)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        import redis

        _redis_client = redis.from_url(_REDIS_URL, decode_responses=True)
        _redis_client.ping()  # verify connection
        logger.info("score_cache: redis_connected", extra={"url": _REDIS_URL})
        return _redis_client
    except Exception as exc:
        logger.warning("score_cache: redis_unavailable", extra={"error": str(exc)})
        return None


def _cache_key(candidate_id: int, job_id: int) -> str:
    return f"{_PREFIX}:{candidate_id}:{job_id}"


# ── Public API ────────────────────────────────────────────────────────────────


def get_cached_score(candidate_id: int, job_id: int) -> dict | None:
    """Fetch pre-computed score from Redis. Returns None if not cached."""
    try:
        r = _get_redis()
        if r is None:
            return None
        raw = r.get(_cache_key(candidate_id, job_id))
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("score_cache: get_failed", extra={"error": str(exc)})
        return None


def set_cached_score(candidate_id: int, job_id: int, score_data: dict) -> None:
    """Store computed score in Redis with TTL."""
    try:
        r = _get_redis()
        if r is None:
            return
        r.setex(_cache_key(candidate_id, job_id), _CACHE_TTL, json.dumps(score_data))
    except Exception as exc:
        logger.warning("score_cache: set_failed", extra={"error": str(exc)})


def invalidate_candidate_scores(candidate_id: int) -> int:
    """Delete all cached scores for a candidate (called when they change their primary resume)."""
    try:
        r = _get_redis()
        if r is None:
            return 0
        pattern = f"{_PREFIX}:{candidate_id}:*"
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
        logger.info("score_cache: invalidated_candidate", extra={"candidate_id": candidate_id, "count": len(keys)})
        return len(keys)
    except Exception as exc:
        logger.warning("score_cache: invalidate_failed", extra={"error": str(exc)})
        return 0


def invalidate_job_scores(job_id: int) -> int:
    """Delete all cached scores for a job (called when job is updated)."""
    try:
        r = _get_redis()
        if r is None:
            return 0
        pattern = f"{_PREFIX}:*:{job_id}"
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
        return len(keys)
    except Exception as exc:
        logger.warning("score_cache: invalidate_job_failed", extra={"error": str(exc)})
        return 0


# ── Background tasks ──────────────────────────────────────────────────────────


def rescore_candidate_vs_all_jobs(candidate_id: int, db_session_factory) -> None:
    """
    Background task: compute + cache this candidate's score against all open jobs.
    Called after a candidate uploads or changes their primary resume.

    Args:
        candidate_id: The candidate's user ID.
        db_session_factory: A callable that returns a new DB Session (get_db).
    """
    from sqlalchemy import select

    from app.models.job import Job
    from app.models.resume import Resume
    from app.services.ml import compute_eligibility
    from app.services.ml.gap_analyzer import enrich_gaps_with_suggestions, gaps_to_dict

    try:
        db = next(db_session_factory())

        # Fetch candidate's primary resume
        resume: Resume | None = (
            db.execute(
                select(Resume)
                .where(Resume.user_id == candidate_id, Resume.is_primary.is_(True))
                .limit(1)
            )
            .scalars()
            .first()
        )
        if not resume:
            logger.info("score_cache: no_primary_resume", extra={"candidate_id": candidate_id})
            return

        resume_like = {
            "raw_text": resume.raw_text,
            "skills": resume.extracted_skills,
            "estimated_experience_years": resume.estimated_experience_years,
            "education_level": resume.education_level,
            "parsed_json": resume.parsed_json,
        }

        # Fetch all open jobs
        jobs = db.execute(select(Job).where(Job.status == "open")).scalars().all()
        logger.info("score_cache: rescoring_candidate", extra={"candidate_id": candidate_id, "jobs": len(jobs)})

        for job in jobs:
            try:
                job_like = {
                    "description": job.description,
                    "required_skills": job.required_skills,
                    "minimum_experience_years": job.minimum_experience_years,
                    "education_requirement": job.education_requirement,
                }
                result = compute_eligibility(resume_like=resume_like, job_like=job_like)
                result_dict = result.to_dict()

                # Enrich with gap suggestions
                missing = list(result.missing_skills)
                candidate_skills = list(resume.extracted_skills or [])
                enriched_gaps = enrich_gaps_with_suggestions(missing, candidate_skills)
                result_dict["skill_gaps"] = gaps_to_dict(enriched_gaps)

                set_cached_score(candidate_id, job.id, result_dict)
            except Exception as exc:
                logger.warning(
                    "score_cache: job_score_failed",
                    extra={"candidate_id": candidate_id, "job_id": job.id, "error": str(exc)},
                )

        db.close()
        logger.info("score_cache: rescore_complete", extra={"candidate_id": candidate_id, "scored": len(jobs)})

    except Exception as exc:
        logger.error("score_cache: rescore_candidate_crashed", extra={"error": str(exc)})


def rescore_job_vs_all_candidates(job_id: int, db_session_factory) -> None:
    """
    Background task: compute + cache all candidates' scores against a new job.
    Called when HR posts or updates a job.

    Args:
        job_id: The job's ID.
        db_session_factory: A callable that returns a new DB Session (get_db).
    """
    from sqlalchemy import select

    from app.models.job import Job
    from app.models.resume import Resume
    from app.models.user import User, UserRole
    from app.services.ml import compute_eligibility
    from app.services.ml.gap_analyzer import enrich_gaps_with_suggestions, gaps_to_dict

    try:
        db = next(db_session_factory())

        job: Job | None = db.get(Job, job_id)
        if not job:
            logger.warning("score_cache: job_not_found", extra={"job_id": job_id})
            return

        job_like = {
            "description": job.description,
            "required_skills": job.required_skills,
            "minimum_experience_years": job.minimum_experience_years,
            "education_requirement": job.education_requirement,
        }

        # All candidate primary resumes
        resumes = (
            db.execute(
                select(Resume)
                .join(User, User.id == Resume.user_id)
                .where(Resume.is_primary.is_(True), User.role == UserRole.candidate)
            )
            .scalars()
            .all()
        )
        logger.info("score_cache: rescoring_job", extra={"job_id": job_id, "candidates": len(resumes)})

        for resume in resumes:
            try:
                resume_like = {
                    "raw_text": resume.raw_text,
                    "skills": resume.extracted_skills,
                    "estimated_experience_years": resume.estimated_experience_years,
                    "education_level": resume.education_level,
                    "parsed_json": resume.parsed_json,
                }
                result = compute_eligibility(resume_like=resume_like, job_like=job_like)
                result_dict = result.to_dict()

                missing = list(result.missing_skills)
                candidate_skills = list(resume.extracted_skills or [])
                enriched_gaps = enrich_gaps_with_suggestions(missing, candidate_skills)
                result_dict["skill_gaps"] = gaps_to_dict(enriched_gaps)

                set_cached_score(resume.user_id, job_id, result_dict)
            except Exception as exc:
                logger.warning(
                    "score_cache: candidate_score_failed",
                    extra={"job_id": job_id, "user_id": resume.user_id, "error": str(exc)},
                )

        db.close()
        logger.info("score_cache: rescore_job_complete", extra={"job_id": job_id, "scored": len(resumes)})

    except Exception as exc:
        logger.error("score_cache: rescore_job_crashed", extra={"error": str(exc)})
