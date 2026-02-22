# file name is candidate_interviews.py

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIError
from app.core.dependencies import get_current_candidate
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
    generate_dynamic_question,
    generate_greeting_reply,
    generate_interview_reply,
)
from app.services.notification_service import get_unread_count, serialize_notification
from app.services.realtime import broadcast_user


router = APIRouter(prefix="/api/candidate/interviews", tags=["candidate-interviews"])


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
