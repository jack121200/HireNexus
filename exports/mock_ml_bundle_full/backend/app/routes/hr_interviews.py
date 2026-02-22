from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_hr
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import meta_from_page
from app.schemas.interview import InterviewListResponse, InterviewResponse
from app.services.interview_service import (
    assert_interview_access,
    build_interview_report_text,
    get_interview,
    hr_interviews,
    serialize_interview,
)


router = APIRouter(prefix="/api/hr/interviews", tags=["hr-interviews"])


@router.get("", response_model=InterviewListResponse)
def list_interviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=50),
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> InterviewListResponse:
    items, meta = hr_interviews(db, hr_user=current_user, page=page, page_size=page_size)
    return InterviewListResponse(items=items, meta=meta_from_page(meta))


@router.get("/{interview_id}", response_model=InterviewResponse)
def detail(
    interview_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    interview = get_interview(db, interview_id=interview_id)
    assert_interview_access(db, interview=interview, user=current_user)
    return InterviewResponse(interview=serialize_interview(interview))


@router.get("/{interview_id}/report.pdf")
def download_report_pdf(
    interview_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> Response:
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
