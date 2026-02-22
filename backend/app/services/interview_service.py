# file name is interview_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import APIError
from app.core.logging import get_logger
from app.models.application import Application, ApplicationStatus
from app.models.interview import Interview, InterviewStatus, InterviewType
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.services.ml import (
    QuestionContext,
    QuestionItem,
    ScoreResult,
    generate_questions,
    score_interview,
)
from app.services.notification_service import create_notification
from app.services.pagination import paginate
from app.services.resume_service import get_primary_resume, get_resume


logger = get_logger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


def _is_probe_question(question_id: str | None) -> bool:
    if not question_id:
        return False
    return "_probe_" in question_id


def _filter_scoring_questions(questions: list[QuestionItem]) -> list[QuestionItem]:
    primary = [q for q in questions if not _is_probe_question(q.id)]
    return primary or questions


def serialize_interview(interview: Interview) -> dict[str, Any]:
    """Serialize interview to dictionary."""
    return {
        "id": interview.id,
        "candidate_user_id": interview.candidate_user_id,
        "hr_user_id": interview.hr_user_id,
        "application_id": interview.application_id,
        "job_id": interview.job_id,
        "resume_id": interview.resume_id,
        "type": interview.type.value,
        "status": interview.status.value,
        "overall_score": interview.overall_score,
        "confidence_score": interview.confidence_score,
        "report": interview.report_json,
        "transcript": interview.transcript,
        "recording_url": interview.recording_url,
        "started_at": interview.started_at.isoformat() if interview.started_at else None,
        "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
        "created_at": interview.created_at.isoformat(),
    }


def build_interview_report_text(interview: Interview) -> str:
    """Build text report from interview data."""
    report = interview.report_json or {}
    scoring = report.get("scoring", {})
    per_question = scoring.get("per_question", [])

    lines = [
        f"Interview Report ({interview.type.value.upper()})",
        f"Status: {interview.status.value}",
        f"Overall Score: {interview.overall_score or 0}/100",
        f"Confidence Score: {interview.confidence_score or 0}/100",
        "",
        "Summary:",
        scoring.get("feedback_summary", "N/A"),
        "",
        "Strengths:",
        " - " + "\n - ".join(scoring.get("strengths", []) or ["N/A"]),
        "",
        "Weaknesses:",
        " - " + "\n - ".join(scoring.get("weaknesses", []) or ["N/A"]),
        "",
        "Recommended Improvements:",
        " - " + "\n - ".join(scoring.get("improvements", []) or ["N/A"]),
        "",
    ]

    if scoring.get("skill_gaps"):
        lines.extend([
            "Skill Gaps to Address:",
            " - " + "\n - ".join(scoring.get("skill_gaps", [])),
            "",
        ])

    lines.append("Per Question Breakdown:")

    for item in per_question:
        lines.extend([
            "",
            f"Q: {item.get('question', '')}",
            f"Category: {item.get('category', '')} | Difficulty: {item.get('difficulty', '')}",
            f"Answer: {item.get('answer', 'No answer provided')}",
            f"Score: {item.get('score', 0)}/100",
            f"Feedback: {item.get('feedback', '')}",
        ])
        
        if item.get("rubric_points"):
            lines.append(f"Evaluation Criteria: {'; '.join(item.get('rubric_points', []))}")

    if interview.recording_url:
        lines.extend(["", f"Recording URL: {interview.recording_url}"])

    return "\n".join(lines)


def build_interview_report_payload(interview: Interview) -> dict[str, Any]:
    """Build structured report payload for HR UI."""
    report = interview.report_json or {}
    scoring = report.get("scoring", {}) if isinstance(report, dict) else {}
    per_question = scoring.get("per_question", []) if isinstance(scoring, dict) else []

    return {
        "interview_id": interview.id,
        "status": interview.status.value,
        "type": interview.type.value,
        "overall_score": interview.overall_score,
        "confidence_score": interview.confidence_score,
        "summary": scoring.get("feedback_summary", "Interview completed."),
        "strengths": list(scoring.get("strengths", []) or []),
        "weaknesses": list(scoring.get("weaknesses", []) or []),
        "improvements": list(scoring.get("improvements", []) or []),
        "skill_gaps": list(scoring.get("skill_gaps", []) or []),
        "per_question": per_question if isinstance(per_question, list) else [],
        "transcript_highlights": [],
        "report_pdf_url": f"/api/hr/interviews/{interview.id}/report.pdf",
        "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
        "report_ready": interview.status == InterviewStatus.completed,
    }


def get_interview(db: Session, *, interview_id: int) -> Interview:
    """Get interview by ID or raise error."""
    interview = db.get(Interview, interview_id)
    if not interview:
        raise APIError(status_code=404, code="interview_not_found", detail="Interview not found")
    return interview


def assert_interview_access(db: Session, *, interview: Interview, user: User) -> None:
    """Assert user has access to interview."""
    if user.role == UserRole.candidate and interview.candidate_user_id == user.id:
        return

    if user.role == UserRole.hr:
        if interview.type != InterviewType.ai:
            raise APIError(status_code=403, code="interview_forbidden", detail="Forbidden")

        # HR can access interviews tied to their jobs or candidates who applied to their jobs
        if interview.hr_user_id == user.id:
            return
        if interview.job_id:
            job = db.get(Job, interview.job_id)
            if job and job.hr_user_id == user.id:
                return

    raise APIError(status_code=403, code="interview_forbidden", detail="Forbidden")


def _question_context_from_resume_job(*, resume: Resume, job: Job) -> QuestionContext:
    """Build question context from resume and job."""
    parsed = resume.parsed_json or {}
    projects = parsed.get("projects", [])
    highlights = parsed.get("highlights", [])
    years = resume.estimated_experience_years or parsed.get("estimated_experience_years", 0.0)

    required_skills = list(job.required_skills or [])
    required_skills += list(job.extracted_required_skills or [])

    return QuestionContext(
        role=job.title,
        years_experience=float(years or 0.0),
        resume_skills=tuple(resume.extracted_skills or []),
        resume_projects=tuple(projects),
        resume_highlights=tuple(highlights),
        job_required_skills=tuple(required_skills),
        job_responsibilities=tuple([job.responsibilities] if job.responsibilities else []),
        job_description=job.description or "",
    )


def ensure_interview_questions(db: Session, *, interview: Interview) -> list[QuestionItem]:
    """Ensure interview has questions, generating if needed."""
    report = dict(interview.report_json or {})
    
    # Check for dynamic questions first (for real-time interviews)
    questions_data = list(report.get("dynamic_questions", []))
    
    # Fallback to static questions
    if not questions_data:
        questions_data = list(report.get("questions", []))

    if questions_data:
        try:
            parsed_questions = [QuestionItem.from_dict(item) for item in questions_data]
            # Validate that we actually got valid questions
            if parsed_questions and all(hasattr(q, 'question') and q.question for q in parsed_questions):
                logger.info("using_existing_questions", interview_id=interview.id, count=len(parsed_questions))
                return parsed_questions
            else:
                logger.warning("existing_questions_invalid", interview_id=interview.id)
        except Exception as exc:
            logger.warning("failed_to_parse_existing_questions", interview_id=interview.id, error=str(exc))

    # Generate new questions
    if interview.type == InterviewType.ai:
        if not interview.job_id or not interview.resume_id:
            raise APIError(status_code=400, code="interview_context_missing", detail="Interview context missing")
        job = db.get(Job, interview.job_id)
        resume = db.get(Resume, interview.resume_id)
        if not job or not resume:
            raise APIError(status_code=404, code="interview_context_not_found", detail="Interview context not found")
        context = _question_context_from_resume_job(resume=resume, job=job)
    else:
        context_dict = report.get("context")
        if not context_dict:
            raise APIError(status_code=400, code="mock_context_missing", detail="Mock interview context missing")
        try:
            context = QuestionContext.from_dict(context_dict)
        except Exception as exc:
            logger.error("failed_to_parse_context", interview_id=interview.id, error=str(exc))
            raise APIError(status_code=400, code="invalid_context", detail="Invalid interview context") from exc

    # Generate questions with retry logic
    logger.info("generating_interview_questions", interview_id=interview.id, type=interview.type.value)
    
    max_retries = 3
    questions = None
    last_error = None
    
    for attempt in range(max_retries):
        try:
            questions = generate_questions(context=context, count=8, seed=(interview.id or 1) + attempt)
            if questions and len(questions) > 0:
                logger.info("generated_questions_successfully", interview_id=interview.id, count=len(questions), attempt=attempt + 1)
                break
            else:
                logger.warning("generated_empty_questions", interview_id=interview.id, attempt=attempt + 1)
        except Exception as exc:
            last_error = exc
            logger.warning("question_generation_attempt_failed", interview_id=interview.id, attempt=attempt + 1, error=str(exc))
    
    if not questions or len(questions) == 0:
        error_msg = f"Failed to generate questions after {max_retries} attempts"
        if last_error:
            error_msg += f": {str(last_error)}"
        logger.error("question_generation_failed", interview_id=interview.id, error=error_msg)
        raise APIError(status_code=500, code="question_generation_failed", detail=error_msg)

    # Save questions
    report["questions"] = [q.to_dict() for q in questions]
    report.setdefault("answers", [])
    interview.report_json = report
    db.add(interview)
    
    try:
        db.flush()
    except Exception as exc:
        logger.error("failed_to_save_questions", interview_id=interview.id, error=str(exc))
        raise APIError(status_code=500, code="failed_to_save_questions", detail="Failed to save generated questions") from exc
    
    logger.info("saved_interview_questions", interview_id=interview.id, count=len(questions))
    return questions


def create_mock_interview(
    db: Session,
    *,
    candidate: User,
    role: str,
    years_experience: float,
    resume_id: int | None,
    jd_text: str,
) -> Interview:
    """Create a mock interview for practice."""
    if candidate.role != UserRole.candidate:
        raise APIError(status_code=403, code="candidate_required", detail="Candidate role required")

    # Validate inputs
    if not role or not role.strip():
        raise APIError(status_code=400, code="invalid_role", detail="Role cannot be empty")
    
    if years_experience < 0:
        years_experience = 0.0

    # Get resume
    resume = get_resume(db, resume_id=resume_id, user=candidate) if resume_id else get_primary_resume(db, user_id=candidate.id)

    resume_skills = tuple(resume.extracted_skills or []) if resume else tuple()
    parsed = resume.parsed_json if resume else {}

    context = QuestionContext(
        role=role.strip(),
        years_experience=max(0.0, float(years_experience)),
        resume_skills=resume_skills,
        resume_projects=tuple(parsed.get("projects", [])),
        resume_highlights=tuple(parsed.get("highlights", [])),
        job_required_skills=tuple(),
        job_responsibilities=tuple(),
        job_description=jd_text.strip() if jd_text else "",
    )

    interview = Interview(
        candidate_user_id=candidate.id,
        hr_user_id=None,
        application_id=None,
        job_id=None,
        resume_id=resume.id if resume else None,
        type=InterviewType.mock,
        status=InterviewStatus.started,
        report_json={
            "context": context.to_dict(),
            "questions": [],
            "answers": [],
            "dynamic_questions": [],
        },
        transcript="",
    )
    db.add(interview)
    
    try:
        db.flush()
    except Exception as exc:
        logger.error("failed_to_create_interview", error=str(exc))
        raise APIError(status_code=500, code="interview_creation_failed", detail="Failed to create interview") from exc
    
    logger.info("created_mock_interview", interview_id=interview.id, role=role, years=years_experience)
    return interview


def complete_interview(
    db: Session,
    *,
    interview: Interview,
    answers: list[str],
    transcript: str,
    recording_url: str | None,
) -> tuple[Interview, list[Any]]:
    """Complete interview and generate scoring."""
    logger.info("completing_interview", interview_id=interview.id, answer_count=len(answers))
    
    # Ensure we have questions
    try:
        questions = ensure_interview_questions(db, interview=interview)
    except Exception as exc:
        logger.error("failed_to_ensure_questions", interview_id=interview.id, error=str(exc))
        raise APIError(status_code=500, code="question_retrieval_failed", detail="Failed to retrieve interview questions") from exc
    questions_for_scoring = _filter_scoring_questions(questions)
    if len(questions_for_scoring) != len(questions):
        logger.info(
            "scoring_questions_filtered",
            interview_id=interview.id,
            total_questions=len(questions),
            scoring_questions=len(questions_for_scoring),
        )

    # Validate and normalize answers
    normalized_answers = []
    for i, ans in enumerate(answers):
        cleaned = (ans or "").strip()
        if not cleaned:
            logger.warning("empty_answer_detected", interview_id=interview.id, question_index=i)
            cleaned = "No answer provided"
        normalized_answers.append(cleaned)
    
    # Pad answers if needed
    while len(normalized_answers) < len(questions_for_scoring):
        normalized_answers.append("No answer provided")
        logger.warning(
            "padding_missing_answer",
            interview_id=interview.id,
            total_questions=len(questions_for_scoring),
            provided_answers=len(answers),
        )
    if len(normalized_answers) > len(questions_for_scoring):
        normalized_answers = normalized_answers[: len(questions_for_scoring)]

    # Validate transcript
    if not transcript or not transcript.strip():
        logger.warning("empty_transcript", interview_id=interview.id)
        # Build transcript from questions and answers
        transcript_parts = []
        for q, a in zip(questions_for_scoring, normalized_answers):
            transcript_parts.append(f"AI: {q.question}")
            transcript_parts.append(f"Candidate: {a}")
        transcript = "\n".join(transcript_parts)

    logger.info(
        "scoring_interview",
        interview_id=interview.id,
        questions=len(questions_for_scoring),
        answers=len(normalized_answers),
        transcript_length=len(transcript),
    )

    # Score the interview with better error handling
    score: ScoreResult | None = None
    scoring_error = None
    
    try:
        score = score_interview(questions=questions_for_scoring, answers=normalized_answers, transcript=transcript)
        
        # Validate score result
        if not score or not hasattr(score, 'overall_score'):
            raise ValueError("Invalid score result returned")
        
        logger.info("scoring_successful", interview_id=interview.id, overall_score=score.overall_score, confidence=score.confidence_score)
        
    except Exception as exc:
        scoring_error = str(exc)
        logger.error("scoring_failed", interview_id=interview.id, error=scoring_error, exc_type=type(exc).__name__)
        
        # Create a meaningful default score based on answer presence
        answered_count = sum(1 for a in normalized_answers if a and a != "No answer provided")
        completion_rate = (answered_count / len(questions_for_scoring)) * 100 if questions_for_scoring else 0
        
        score = ScoreResult(
            per_question=tuple(),
            overall_score=max(0.0, completion_rate * 0.3),  # Give some credit for attempting
            confidence_score=0.0,
            feedback_summary=f"Scoring system encountered an error: {scoring_error}. Please review answers manually.",
            strengths=tuple(["Attempted the interview"] if answered_count > 0 else []),
            weaknesses=tuple(["Scoring system error - manual review needed"]),
            improvements=tuple([
                "Please contact support to review this interview",
                "Consider retaking the interview if possible"
            ]),
            skill_gaps=tuple(),
        )

    # Update interview
    report = dict(interview.report_json or {})
    report["answers"] = normalized_answers
    report["scoring"] = score.to_dict()
    report["completed_at"] = _utcnow().isoformat()
    
    if scoring_error:
        report["scoring_error"] = scoring_error

    interview.report_json = report
    interview.transcript = transcript
    interview.recording_url = recording_url or interview.recording_url
    interview.overall_score = score.overall_score
    interview.confidence_score = score.confidence_score
    interview.status = InterviewStatus.completed
    interview.completed_at = _utcnow()
    db.add(interview)

    notifications: list[Any] = []

    # Update application status if AI interview
    if interview.type == InterviewType.ai and interview.application_id:
        application = db.get(Application, interview.application_id)
        if application:
            application.status = ApplicationStatus.interview_completed
            db.add(application)
            logger.info("updated_application_status", application_id=interview.application_id)

        # Notify HR
        if interview.hr_user_id:
            notifications.append(
                create_notification(
                    db,
                    user_id=interview.hr_user_id,
                    type="interview_completed",
                    title="Interview Completed",
                    body=f"A candidate completed their AI interview with score {score.overall_score:.1f}/100",
                    data={
                        "interview_id": interview.id,
                        "application_id": interview.application_id,
                        "job_id": interview.job_id,
                        "overall_score": score.overall_score,
                    },
                )
            )

    # Notify candidate
    notifications.append(
        create_notification(
            db,
            user_id=interview.candidate_user_id,
            type="interview_report_ready",
            title="Interview Report Ready",
            body=f"Your interview report is ready. Overall score: {score.overall_score:.1f}/100",
            data={
                "interview_id": interview.id,
                "type": interview.type.value,
                "overall_score": score.overall_score,
                "confidence_score": score.confidence_score,
            },
        )
    )

    try:
        db.flush()
    except Exception as exc:
        logger.error("failed_to_save_completion", interview_id=interview.id, error=str(exc))
        raise APIError(status_code=500, code="completion_save_failed", detail="Failed to save interview completion") from exc
    
    logger.info("completed_interview", interview_id=interview.id, overall_score=score.overall_score, confidence=score.confidence_score)
    return interview, notifications


def candidate_interviews(db: Session, *, candidate: User, page: int, page_size: int):
    """Get paginated list of candidate's interviews."""
    if candidate.role != UserRole.candidate:
        raise APIError(status_code=403, code="candidate_required", detail="Candidate role required")

    stmt: Select = (
        select(Interview)
        .where(Interview.candidate_user_id == candidate.id)
        .order_by(Interview.created_at.desc(), Interview.id.desc())
    )
    interviews, meta = paginate(db, stmt, page=page, page_size=page_size)
    return [serialize_interview(interview) for interview in interviews], meta


def hr_interviews(db: Session, *, hr_user: User, page: int, page_size: int):
    """Get paginated list of HR's accessible interviews."""
    if hr_user.role != UserRole.hr:
        raise APIError(status_code=403, code="hr_required", detail="HR role required")

    hr_job_ids = select(Job.id).where(Job.hr_user_id == hr_user.id)
    candidate_ids_stmt = select(Application.candidate_user_id).where(Application.job_id.in_(hr_job_ids))

    stmt: Select = (
        select(Interview)
        .where(
            Interview.type == InterviewType.ai,
            (Interview.hr_user_id == hr_user.id)
            | (Interview.job_id.in_(hr_job_ids))
            | (Interview.candidate_user_id.in_(candidate_ids_stmt))
        )
        .order_by(Interview.created_at.desc(), Interview.id.desc())
    )

    interviews, meta = paginate(db, stmt, page=page, page_size=page_size)
    return [serialize_interview(interview) for interview in interviews], meta
