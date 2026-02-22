# file name is candidate_interviews.py

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIError
from app.core.dependencies import get_current_candidate
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.interview import Interview
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.common import meta_from_page
from app.schemas.interview import (
    InterviewCompleteRequest,
    InterviewListResponse,
    InterviewQuestionsResponse,
    InterviewResponse,
    MockInterviewCreateRequest,
)
from app.services.dashboard_service import candidate_dashboard, hr_dashboard
from app.services.interview_service import (
    assert_interview_access,
    candidate_interviews,
    complete_interview,
    create_mock_interview,
    build_interview_report_text,
    ensure_interview_questions,
    get_interview,
    serialize_interview,
    _question_context_from_resume_job,
)
from app.services.ml import (
    QuestionContext,
    QuestionItem,
    detect_skip_intent,
    generate_dynamic_question,
    generate_greeting_reply,
    generate_interview_reply,
)
from app.services.notification_service import get_unread_count, serialize_notification
from app.services.realtime import broadcast_user


router = APIRouter(prefix="/api/candidate/interviews", tags=["candidate-interviews"])
logger = get_logger(__name__)


def _target_for_years(years: float, seed: int) -> int:
    """Calculate target question count based on experience level."""
    if years <= 1:
        return 5 + (seed % 2)  # 5-6 questions
    elif years <= 2:
        return 6 + (seed % 3)  # 6-8 questions
    elif years <= 5:
        return 8 + (seed % 3)  # 8-10 questions
    elif years <= 10:
        return 10 + (seed % 3)  # 10-12 questions
    else:
        return 12 + (seed % 3)  # 12-14 questions


def _load_dynamic_questions(report: dict) -> list[QuestionItem]:
    questions: list[QuestionItem] = []
    for item in report.get("dynamic_questions", []) or []:
        try:
            questions.append(QuestionItem.from_dict(item))
        except Exception:
            continue
    return questions


def _get_context_for_interview(db: Session, interview: Interview, report: dict) -> QuestionContext:
    if interview.type.value == "ai":
        if not interview.job_id or not interview.resume_id:
            raise APIError(status_code=400, code="interview_context_missing", detail="Interview context missing")
        job = db.get(Job, interview.job_id)
        resume = db.get(Resume, interview.resume_id)
        if not job or not resume:
            raise APIError(status_code=404, code="interview_context_not_found", detail="Interview context not found")
        return _question_context_from_resume_job(resume=resume, job=job)

    context_dict = report.get("context") or {}
    if not context_dict:
        raise APIError(status_code=400, code="mock_context_missing", detail="Mock interview context missing")
    return QuestionContext.from_dict(context_dict)


def _text_similarity_ratio(a: str, b: str) -> float:
    tokens_a = {token for token in a.lower().split() if token}
    tokens_b = {token for token in b.lower().split() if token}
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a.intersection(tokens_b))
    union = len(tokens_a.union(tokens_b))
    if union == 0:
        return 0.0
    return overlap / union


@router.get("", response_model=InterviewListResponse)
def list_interviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> InterviewListResponse:
    """List all interviews for the current candidate."""
    items, meta = candidate_interviews(db, candidate=current_user, page=page, page_size=page_size)
    return InterviewListResponse(items=items, meta=meta_from_page(meta))


@router.get("/by-application/{application_id}", response_model=InterviewResponse)
def get_by_application(
    application_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    """Get interview by application ID."""
    stmt = select(Interview).where(Interview.application_id == application_id).order_by(Interview.id.desc()).limit(1)
    interview = db.scalar(stmt)
    if not interview:
        raise APIError(status_code=404, code="interview_not_found", detail="Interview not found for application")
    assert_interview_access(db, interview=interview, user=current_user)
    return InterviewResponse(interview=serialize_interview(interview))


@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview_detail(
    interview_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    """Get interview details by ID."""
    interview = get_interview(db, interview_id=interview_id)
    assert_interview_access(db, interview=interview, user=current_user)
    return InterviewResponse(interview=serialize_interview(interview))


@router.get("/{interview_id}/questions", response_model=InterviewQuestionsResponse)
def get_questions(
    interview_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> InterviewQuestionsResponse:
    """Get interview questions."""
    interview = get_interview(db, interview_id=interview_id)
    assert_interview_access(db, interview=interview, user=current_user)
    questions = ensure_interview_questions(db, interview=interview)
    return InterviewQuestionsResponse(interview_id=interview.id, questions=[q.to_dict() for q in questions])


@router.post("/{interview_id}/complete", response_model=InterviewResponse)
async def complete(
    interview_id: int,
    payload: InterviewCompleteRequest,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    """Complete interview and generate scores."""
    interview = get_interview(db, interview_id=interview_id)
    assert_interview_access(db, interview=interview, user=current_user)

    interview, notifications = complete_interview(
        db,
        interview=interview,
        answers=payload.answers,
        transcript=payload.transcript,
        recording_url=payload.recording_url,
    )

    db.commit()
    for notification in notifications:
        db.refresh(notification)

    # Broadcast notifications and dashboard updates to involved users
    touched_user_ids = {interview.candidate_user_id}
    if interview.hr_user_id:
        touched_user_ids.add(interview.hr_user_id)

    for user_id in touched_user_ids:
        unread = get_unread_count(db, user_id=user_id)
        user_notifications = [n for n in notifications if n.user_id == user_id]
        for notification in user_notifications:
            await broadcast_user(
                user_id=user_id,
                event="notification.created",
                data={
                    "notification": serialize_notification(notification),
                    "unread_count": unread,
                },
            )

    # Dashboard updates
    candidate_summary = candidate_dashboard(db, candidate=current_user)
    await broadcast_user(
        user_id=current_user.id,
        event="dashboard.updated",
        data={"summary": candidate_summary},
    )
    if interview.hr_user_id:
        hr_user = db.get(User, interview.hr_user_id)
        if hr_user:
            hr_summary = hr_dashboard(db, hr_user=hr_user)
            await broadcast_user(
                user_id=hr_user.id,
                event="dashboard.updated",
                data={"summary": hr_summary},
            )

    return InterviewResponse(interview=serialize_interview(interview))


@router.post("/mock", response_model=InterviewResponse)
def create_mock(
    payload: MockInterviewCreateRequest,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    """Create a mock interview for practice."""
    interview = create_mock_interview(
        db,
        candidate=current_user,
        role=payload.role,
        years_experience=payload.years_experience,
        resume_id=payload.resume_id,
        jd_text=payload.jd_text,
    )
    return InterviewResponse(interview=serialize_interview(interview))


@router.get("/{interview_id}/report.pdf")
def download_report_pdf(
    interview_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> Response:
    """Download interview report as PDF."""
    interview = get_interview(db, interview_id=interview_id)
    assert_interview_access(db, interview=interview, user=current_user)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    report_text = build_interview_report_text(interview)
    for line in report_text.split("\n"):
        pdf.multi_cell(0, 6, line)

    output = pdf.output(dest="S").encode("latin-1", errors="ignore")
    return Response(
        content=output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=interview_{interview_id}_report.pdf"},
    )


@router.post("/{interview_id}/followup")
def followup(
    interview_id: int,
    payload: dict,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """Generate follow-up question based on candidate's answer."""
    interview = get_interview(db, interview_id=interview_id)
    assert_interview_access(db, interview=interview, user=current_user)

    questions = ensure_interview_questions(db, interview=interview)
    question_id = str(payload.get("question_id", "")).strip()
    answer = str(payload.get("answer", "")).strip()

    # Find the question
    question = next((q for q in questions if q.id == question_id), None)
    if not question and questions:
        question = questions[0]
    if not question:
        return {"followup": ""}

    # Get context
    if interview.type.value == "ai":
        if not interview.job_id or not interview.resume_id:
            return {"followup": ""}
        job = db.get(Job, interview.job_id)
        resume = db.get(Resume, interview.resume_id)
        if not job or not resume:
            return {"followup": ""}
        context = _question_context_from_resume_job(resume=resume, job=job)
    else:
        report = dict(interview.report_json or {})
        context_dict = report.get("context") or {}
        if not context_dict:
            return {"followup": ""}
        context = QuestionContext.from_dict(context_dict)

    # Get asked questions for context
    report = dict(interview.report_json or {})
    asked_questions: list[QuestionItem] = []
    for item in report.get("dynamic_questions", []) or []:
        try:
            asked_questions.append(QuestionItem.from_dict(item))
        except Exception:
            continue

    # Generate reply
    reply_payload = generate_interview_reply(
        context=context,
        question=question,
        answer=answer,
        transcript=str(payload.get("transcript", "")),
        asked_questions=asked_questions,
    )
    followup_text = str(reply_payload.get("followup") or "")

    # Store followup
    followups = list(report.get("followups", []))
    followups.append({
        "question_id": question.id,
        "answer": answer,
        "followup": followup_text,
        "reply": reply_payload.get("reply", ""),
    })
    report["followups"] = followups
    interview.report_json = report
    db.add(interview)
    db.flush()

    return {
        "reply": reply_payload.get("reply", ""),
        "followup": followup_text,
        "move_on": bool(reply_payload.get("move_on", False)),
    }


@router.post("/{interview_id}/greeting-reply")
def greeting_reply(
    interview_id: int,
    payload: dict,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """Generate interviewer's reply to candidate's greeting."""
    interview = get_interview(db, interview_id=interview_id)
    assert_interview_access(db, interview=interview, user=current_user)

    # Get context
    if interview.type.value == "ai":
        if not interview.job_id or not interview.resume_id:
            return {"reply": ""}
        job = db.get(Job, interview.job_id)
        resume = db.get(Resume, interview.resume_id)
        if not job or not resume:
            return {"reply": ""}
        context = _question_context_from_resume_job(resume=resume, job=job)
    else:
        report = dict(interview.report_json or {})
        context_dict = report.get("context") or {}
        if not context_dict:
            return {"reply": ""}
        context = QuestionContext.from_dict(context_dict)

    reply = generate_greeting_reply(
        context=context,
        transcript=str(payload.get("transcript", "")),
    )
    if reply:
        return {"reply": reply}
    return {"reply": "Great, thanks for sharing. Let's get started with the interview."}


@router.post("/{interview_id}/turn")
def interview_turn(
    interview_id: int,
    payload: dict,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """
    Unified conversational turn endpoint.

    Handles acknowledgement + followup + next question progression in one request.
    """
    started_at = time.perf_counter()
    interview = get_interview(db, interview_id=interview_id)
    assert_interview_access(db, interview=interview, user=current_user)

    report = dict(interview.report_json or {})
    asked_questions = _load_dynamic_questions(report)
    asked_count = len(asked_questions)
    context = _get_context_for_interview(db, interview, report)

    target_count = int(report.get("target_count") or 0)
    if not target_count:
        target_count = _target_for_years(context.years_experience, interview.id or 1)
        report["target_count"] = target_count

    current_question_id = str(payload.get("current_question_id") or "").strip()
    answer_text = str(payload.get("answer_text") or "").strip()
    turn_type = str(payload.get("turn_type") or "answer").strip().lower()
    transcript_tail = str(payload.get("transcript_tail") or payload.get("transcript") or "")

    turn_state = dict(report.get("turn_state") or {})
    probe_counts = dict(turn_state.get("probe_counts") or {})
    recent_prompts = list(turn_state.get("recent_prompts") or [])
    fallback_reason = None

    current_question = next((q for q in asked_questions if q.id == current_question_id), None)
    if not current_question and asked_questions:
        current_question = asked_questions[-1]

    # Initial question bootstrap
    if not current_question:
        if asked_count >= target_count:
            return {
                "reply_text": "Great work. Interview is complete.",
                "next_question": None,
                "move_on": True,
                "probe_used": False,
                "done": True,
                "asked_count": asked_count,
                "total_count": target_count,
            }

        first_question = generate_dynamic_question(
            context=context,
            asked_questions=asked_questions,
            transcript=transcript_tail,
            seed=interview.id or 1,
            index=asked_count,
            target_count=target_count,
            allow_template_fallback=interview.type.value != "ai",
        )
        asked_questions.append(first_question)
        asked_count += 1
        report["dynamic_questions"] = [q.to_dict() for q in asked_questions]
        report["asked_count"] = asked_count
        turn_state["recent_prompts"] = (recent_prompts + [first_question.question])[-10:]
        report["turn_state"] = turn_state
        interview.report_json = report
        db.add(interview)
        db.flush()
        return {
            "reply_text": "Thanks. Let's begin.",
            "next_question": first_question.to_dict(),
            "move_on": True,
            "probe_used": False,
            "done": False,
            "asked_count": asked_count,
            "total_count": target_count,
        }

    probe_limit = 1
    question_key = current_question.id
    probe_count = int(probe_counts.get(question_key, 0))
    skip_detected = turn_type in {"skip", "pass"} or detect_skip_intent(answer_text)
    probe_used = False
    move_on = False
    move_on_reason = "unknown"
    reply_text = ""
    next_question: QuestionItem | None = None

    if skip_detected:
        if probe_count < probe_limit:
            probe_used = True
            move_on = False
            move_on_reason = "dont_know_probe"
            probe_counts[question_key] = probe_count + 1
            reply_text = "No worries. One quick attempt and then we'll move ahead."
            probe_text = "What would be your first practical step if you had to start solving this now?"
            next_question = QuestionItem(
                id=f"{current_question.id}_probe_{probe_counts[question_key]}",
                question=probe_text,
                difficulty=current_question.difficulty,
                category=current_question.category,
                rubric_points=current_question.rubric_points,
            )
        else:
            move_on = True
            move_on_reason = "dont_know_move_on"
            reply_text = "Understood. Let's move to the next question."
    else:
        reply_payload = generate_interview_reply(
            context=context,
            question=current_question,
            answer=answer_text,
            transcript=transcript_tail,
            asked_questions=asked_questions,
        )
        reply_text = str(reply_payload.get("reply") or "Thanks.").strip()
        followup_text = str(reply_payload.get("followup") or "").strip()
        move_on = bool(reply_payload.get("move_on", False))
        fallback_reason = reply_payload.get("fallback_reason")

        if followup_text and not move_on:
            # Block semantically repetitive probes.
            similarities = [_text_similarity_ratio(followup_text, old_prompt) for old_prompt in recent_prompts[-4:]]
            high_similarity = max(similarities) if similarities else 0.0
            if high_similarity >= 0.72:
                move_on = True
                move_on_reason = "repeat_blocked"
            elif probe_count >= probe_limit:
                move_on = True
                move_on_reason = "probe_limit_reached"
            else:
                probe_used = True
                move_on = False
                move_on_reason = "llm_probe"
                probe_counts[question_key] = probe_count + 1
                next_question = QuestionItem(
                    id=f"{current_question.id}_probe_{probe_counts[question_key]}",
                    question=followup_text,
                    difficulty=current_question.difficulty,
                    category=current_question.category,
                    rubric_points=current_question.rubric_points,
                )
        elif move_on:
            move_on_reason = "model_move_on"
        elif probe_count < probe_limit:
            probe_used = True
            move_on = False
            move_on_reason = "default_probe"
            probe_counts[question_key] = probe_count + 1
            next_question = QuestionItem(
                id=f"{current_question.id}_probe_{probe_counts[question_key]}",
                question="Can you give one concrete example from your work to support that?",
                difficulty=current_question.difficulty,
                category=current_question.category,
                rubric_points=current_question.rubric_points,
            )
        else:
            move_on = True
            move_on_reason = "probe_limit_reached"

    done = False
    if move_on:
        if asked_count >= target_count:
            done = True
        else:
            next_question = generate_dynamic_question(
                context=context,
                asked_questions=asked_questions,
                transcript=transcript_tail,
                seed=interview.id or 1,
                index=asked_count,
                target_count=target_count,
                allow_template_fallback=interview.type.value != "ai",
            )
            asked_questions.append(next_question)
            asked_count += 1
            move_on_reason = move_on_reason or "next_question_generated"

    report["dynamic_questions"] = [q.to_dict() for q in asked_questions]
    report["asked_count"] = asked_count

    turn_history = list(report.get("turn_history") or [])
    turn_history.append(
        {
            "question_id": current_question.id,
            "turn_type": turn_type,
            "skip_detected": skip_detected,
            "probe_used": probe_used,
            "move_on": move_on,
            "move_on_reason": move_on_reason,
        }
    )
    report["turn_history"] = turn_history[-30:]

    if next_question:
        recent_prompts.append(next_question.question)

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    turn_state.update(
        {
            "probe_counts": probe_counts,
            "recent_prompts": recent_prompts[-10:],
            "last_move_on_reason": move_on_reason,
            "last_turn_latency_ms": elapsed_ms,
            "last_fallback_reason": fallback_reason,
        }
    )
    report["turn_state"] = turn_state

    interview.report_json = report
    db.add(interview)
    db.flush()

    logger.info(
        "interview_turn_processed",
        interview_id=interview.id,
        question_id=current_question.id,
        probe_used=probe_used,
        move_on=move_on,
        done=done,
        asked_count=asked_count,
        total_count=target_count,
        move_on_reason=move_on_reason,
        dont_know_detected=skip_detected,
        llm_fallback_reason=fallback_reason,
        turn_latency_ms=elapsed_ms,
    )

    return {
        "reply_text": reply_text,
        "next_question": next_question.to_dict() if next_question else None,
        "move_on": move_on,
        "probe_used": probe_used,
        "done": done,
        "asked_count": asked_count,
        "total_count": target_count,
    }


@router.post("/{interview_id}/next-question")
def next_question(
    interview_id: int,
    payload: dict,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """Generate the next dynamic question in the interview."""
    interview = get_interview(db, interview_id=interview_id)
    assert_interview_access(db, interview=interview, user=current_user)

    report = dict(interview.report_json or {})
    
    # Get asked questions
    asked_questions: list[QuestionItem] = []
    for item in report.get("dynamic_questions", []) or []:
        try:
            asked_questions.append(QuestionItem.from_dict(item))
        except Exception:
            continue
    asked_count = len(asked_questions)

    # Get or calculate target count
    target_count = int(report.get("target_count") or 0)

    # Get context
    if interview.type.value == "ai":
        if not interview.job_id or not interview.resume_id:
            return {"done": True, "asked_count": asked_count, "total_count": target_count}
        job = db.get(Job, interview.job_id)
        resume = db.get(Resume, interview.resume_id)
        if not job or not resume:
            return {"done": True, "asked_count": asked_count, "total_count": target_count}
        context = _question_context_from_resume_job(resume=resume, job=job)
    else:
        context_dict = report.get("context") or {}
        if not context_dict:
            return {"done": True, "asked_count": asked_count, "total_count": target_count}
        context = QuestionContext.from_dict(context_dict)

    # Calculate target if not set
    if not target_count:
        target_count = _target_for_years(context.years_experience, interview.id or 1)
        report["target_count"] = target_count
        interview.report_json = report
        db.add(interview)
        db.flush()

    # Check if we're done
    if asked_count >= target_count:
        return {"done": True, "asked_count": asked_count, "total_count": target_count}

    # Generate next question
    transcript = str(payload.get("transcript", ""))
    question = generate_dynamic_question(
        context=context,
        asked_questions=asked_questions,
        transcript=transcript,
        seed=interview.id or 1,
        index=asked_count,
        target_count=target_count,
    )

    # Store the question
    asked_questions.append(question)
    report["dynamic_questions"] = [q.to_dict() for q in asked_questions]
    report["asked_count"] = asked_count + 1
    report.setdefault("target_count", target_count)
    interview.report_json = report
    db.add(interview)
    db.flush()

    return {
        "question": question.to_dict(),
        "done": False,
        "asked_count": asked_count + 1,
        "total_count": target_count,
    }
