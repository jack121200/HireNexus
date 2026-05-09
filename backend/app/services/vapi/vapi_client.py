import httpx
from typing import Optional

from app.core.config import get_settings
from app.core.exceptions import APIError

VAPI_BASE_URL = "https://api.vapi.ai"


async def create_vapi_web_call(
    system_prompt: str,
    variable_values: dict,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Creates a Vapi web call with a fully inline assistant definition.
    The system_prompt is injected at runtime — no static Vapi dashboard assistant required.
    Returns: Vapi call object with 'id' field.
    """
    settings = get_settings()

    private_key = settings.vapi_private_key
    if not private_key:
        raise APIError(
            status_code=500,
            code="vapi_config_error",
            detail="VAPI_PRIVATE_KEY is not set in your .env file.",
        )

    candidate_name = variable_values.get("candidateName", "Candidate")
    interview_type = variable_values.get("interviewType", "technical")
    role_name = variable_values.get("roleName", "Software Engineer")
    duration = variable_values.get("duration", "30")

    first_message = (
        f"Hi {candidate_name}, I'm Sarah from HireNexus. "
        f"I'll be conducting your {interview_type} interview today for the {role_name} role. "
        f"This will take about {duration} minutes. Shall we begin?"
    )

    # ── Always use inline assistant — works reliably without dashboard setup ──
    payload = {
        "assistant": {
            "name": "Sarah — HireNexus AI Interviewer",
            "firstMessage": first_message,
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "maxTokens": 500,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    }
                ],
            },
            "voice": {
                "provider": "playht",
                "voiceId": "jennifer",
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": "en",
            },
            "endCallFunctionEnabled": True,
            "endCallPhrases": [
                "thank you for your time",
                "interview is now complete",
                "we'll be in touch",
                "that concludes our interview",
            ],
            "silenceTimeoutSeconds": 30,
            "maxDurationSeconds": 3600,
            "backgroundSound": "off",
        },
        "metadata": metadata or {},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{VAPI_BASE_URL}/call/web",
            headers={
                "Authorization": f"Bearer {private_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code not in (200, 201):
        raise APIError(
            status_code=502,
            code="vapi_request_failed",
            detail=f"Vapi call creation failed: {response.status_code} - {response.text}",
        )

    return response.json()
