import json, hmac, hashlib, os
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.vapi.scorer import score_interview_transcript
from app.models.interview import Interview

router = APIRouter(prefix="/vapi", tags=["vapi-webhook"])

WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET", "")

def verify_signature(payload: bytes, signature: str) -> bool:
    if not WEBHOOK_SECRET:
        return True  # Skip in local dev
    expected = hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")

@router.post("/webhook")
async def handle_vapi_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    body = await request.body()
    sig = request.headers.get("x-vapi-signature", "")

    if not verify_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid Vapi signature")

    data = json.loads(body)
    msg = data.get("message", {})
    event_type = msg.get("type", "")

    # ── call.start ────────────────────────────────────────────────────────────
    if event_type == "call-start":
        call_id = msg.get("call", {}).get("id")
        metadata = msg.get("call", {}).get("metadata", {})
        print(f"[Vapi] Call started: {call_id} | type: {metadata.get('interview_type')}")
        
        # We find the interview by its ID from metadata
        local_interview_id = metadata.get("local_interview_id")
        if local_interview_id:
            interview = db.get(Interview, local_interview_id)
            if interview:
                interview.recording_url = call_id  # We temporarily store call_id here to link it later
                db.commit()
                
        return {"status": "ok"}

    # ── end-of-call-report ────────────────────────────────────────────────────
    if event_type == "end-of-call-report":
        call_id = msg.get("call", {}).get("id")
        metadata = msg.get("call", {}).get("metadata", {})
        transcript = msg.get("transcript", "")
        duration_seconds = msg.get("durationSeconds", 0)
        recording_url = msg.get("recordingUrl", "")
        ended_reason = msg.get("endedReason", "unknown")

        print(f"[Vapi] Call ended: {call_id} | duration: {duration_seconds}s | reason: {ended_reason}")

        local_interview_id = metadata.get("local_interview_id")
        if local_interview_id:
            interview = db.get(Interview, local_interview_id)
            if interview:
                interview.transcript = transcript
                interview.recording_url = recording_url
                db.commit()

        # Trigger AI scoring in background
        if transcript and len(transcript) > 100:
            background_tasks.add_task(
                score_interview_transcript,
                call_id=call_id,
                role=metadata.get("focus_skills", ["sde"])[0] if metadata.get("interview_type") == "mock" else metadata.get("job_role", "sde"),
                transcript=transcript,
                interview_type=metadata.get("interview_type", "job"),
                db_session=db
            )

        return {"status": "ok"}

    # ── status-update ─────────────────────────────────────────────────────────
    if event_type == "status-update":
        status = msg.get("status")
        print(f"[Vapi] Status update: {status}")
        return {"status": "ok"}

    return {"status": "ok", "event": event_type}
