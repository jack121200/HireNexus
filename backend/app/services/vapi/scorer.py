import os
import json

from dotenv import load_dotenv

load_dotenv()


def _make_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except ImportError:
        return None


def _make_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        import openai
        return openai.OpenAI(api_key=api_key)
    except Exception:
        return None


# ─── System prompt used by all scoring calls ─────────────────────────────────

def _build_score_prompt(mode_instruction: str) -> str:
    return f"""You are an expert technical interview evaluator.
Analyze the interview transcript and return ONLY a valid JSON object.
{mode_instruction}

JSON structure:
{{
  "overall_score": <1-10>,
  "technical_score": <1-10>,
  "communication_score": <1-10>,
  "confidence_score": <1-10>,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "improvement_areas": ["area 1", "area 2"],
  "hire_recommendation": "strong_yes | yes | maybe | no",
  "summary": "<2-3 sentence summary of the candidate's performance>",
  "topics_covered": ["topic1", "topic2"],
  "red_flags": ["flag1"] or []
}}"""


async def score_interview_transcript(
    call_id: str,
    role: str,
    transcript: str,
    interview_type: str = "job",
    db_session=None,
) -> dict:
    """
    Scores the interview transcript using an LLM.
    Saves result to DB. Called in background after end-of-call webhook.
    Tries Groq first (free), then OpenAI.
    """
    mode_instruction = (
        "This was a real job interview. Focus on hire/no-hire recommendation."
        if interview_type == "job"
        else "This was a mock practice interview. Focus on improvement areas."
    )
    system_prompt = _build_score_prompt(mode_instruction)
    user_message = f"Role: {role}\n\nInterview Transcript:\n{transcript}"

    score_data = None

    # ── Try Groq first (free tier available) ──────────────────────────────────
    groq_client = _make_groq_client()
    if groq_client and not score_data:
        try:
            response = groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
            score_data = json.loads(response.choices[0].message.content)
            print(f"[Scorer] Scored via Groq.")
        except Exception as e:
            print(f"[Scorer] Groq scoring failed: {e}")

    # ── Try OpenAI fallback ───────────────────────────────────────────────────
    openai_client = _make_openai_client()
    if openai_client and not score_data:
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                max_tokens=800,
            )
            score_data = json.loads(response.choices[0].message.content)
            print(f"[Scorer] Scored via OpenAI.")
        except Exception as e:
            print(f"[Scorer] OpenAI scoring failed: {e}")

    if not score_data:
        print(f"[Scorer] All scoring methods failed for call {call_id} — no LLM key configured.")
        score_data = {
            "overall_score": 5,
            "technical_score": 5,
            "communication_score": 5,
            "confidence_score": 5,
            "strengths": ["Interview completed successfully"],
            "improvement_areas": ["Scoring unavailable — no LLM key configured"],
            "hire_recommendation": "maybe",
            "summary": "Interview completed. Automated scoring was unavailable.",
            "topics_covered": [],
            "red_flags": [],
        }

    score_data["call_id"] = call_id
    print(
        f"[Scorer] Interview {call_id} scored: "
        f"{score_data.get('overall_score')}/10 | Rec: {score_data.get('hire_recommendation')}"
    )

    if db_session:
        try:
            from app.models.interview import Interview, InterviewStatus, InterviewType
            from app.models.application import Application, ApplicationStatus
            from app.services.notification_service import create_notification, serialize_notification
            from app.services.realtime import broadcast_user
            from sqlalchemy import select
            from datetime import datetime, timezone

            stmt = select(Interview).where(Interview.recording_url == call_id)
            interview = db_session.scalar(stmt)
            if interview:
                formatted_report = {
                    "scoring": {
                        "feedback_summary": score_data.get("summary", ""),
                        "strengths": score_data.get("strengths", []),
                        "weaknesses": score_data.get("improvement_areas", []) + score_data.get("red_flags", []),
                        "improvements": score_data.get("improvement_areas", []),
                        "skill_gaps": [],
                        "per_question": [],
                    },
                    "raw_score_data": score_data,
                }

                interview.report_json = formatted_report
                interview.overall_score = float(score_data.get("overall_score", 0)) * 10
                interview.confidence_score = float(score_data.get("confidence_score", 0)) * 10
                interview.status = InterviewStatus.completed
                interview.completed_at = datetime.now(timezone.utc)
                db_session.add(interview)

                if interview.type == InterviewType.ai and interview.application_id:
                    application = db_session.get(Application, interview.application_id)
                    if application:
                        application.status = ApplicationStatus.interview_completed
                        db_session.add(application)

                    if interview.hr_user_id:
                        hr_notif = create_notification(
                            db_session,
                            user_id=interview.hr_user_id,
                            type="interview_completed",
                            title="AI Interview Completed",
                            body=f"A candidate completed their job interview with score {interview.overall_score:.1f}/100",
                            data={
                                "interview_id": interview.id,
                                "application_id": interview.application_id,
                                "job_id": interview.job_id,
                                "overall_score": interview.overall_score,
                            },
                        )
                        db_session.flush()
                        try:
                            import asyncio
                            from app.services.notification_service import get_unread_count

                            loop = asyncio.get_running_loop()
                            unread_count = get_unread_count(db_session, user_id=interview.hr_user_id)
                            loop.create_task(
                                broadcast_user(
                                    user_id=interview.hr_user_id,
                                    event="notification.created",
                                    data={
                                        "notification": serialize_notification(hr_notif),
                                        "unread_count": unread_count,
                                    },
                                )
                            )
                        except Exception as e:
                            print(f"[Scorer] Broadcast failed: {e}")

                db_session.commit()
        except Exception as e:
            print(f"[Scorer] DB save failed for {call_id}: {e}")

    return score_data
