from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


TESTDATA_DIR = Path(__file__).resolve().parents[2] / "testdata"
RESUME_TEXT_PATH = TESTDATA_DIR / "resumes" / "resume_backend.txt"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_candidate(client: TestClient) -> dict[str, Any]:
    payload = {
        "email": "candidate@example.com",
        "password": "StrongPass!123",
        "full_name": "Casey Candidate",
    }
    response = client.post("/api/candidate/register", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _register_hr(client: TestClient) -> dict[str, Any]:
    payload = {
        "email": "hiring@acme.com",
        "password": "StrongPass!123",
        "full_name": "Harper HR",
        "company_name": "Acme Inc",
        "company_website": "https://acme.com",
    }
    response = client.post("/api/hr/register", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _upload_resume(client: TestClient, token: str) -> dict[str, Any]:
    assert RESUME_TEXT_PATH.exists(), f"Missing test resume: {RESUME_TEXT_PATH}"
    with RESUME_TEXT_PATH.open("rb") as handle:
        files = {"file": ("resume_backend.txt", handle, "text/plain")}
        response = client.post("/api/candidate/resumes", headers=_auth_headers(token), files=files)
    assert response.status_code == 200, response.text
    return response.json()


def _post_job(client: TestClient, token: str) -> dict[str, Any]:
    payload = {
        "title": "Backend Engineer",
        "description": (
            "We need a backend engineer who can build FastAPI services, work with MySQL and Redis, "
            "and design robust APIs in Python."
        ),
        "responsibilities": "Build APIs, own services, improve reliability.",
        "required_skills": ["Python", "FastAPI", "MySQL", "Redis", "SQLAlchemy"],
        "minimum_experience_years": 2,
        "education_requirement": "bachelor",
        "location": "Remote",
        "employment_type": "Full-time",
    }
    response = client.post("/api/hr/jobs", headers=_auth_headers(token), json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_hr_domain_verification_enforced() -> None:
    with TestClient(app) as client:
        payload = {
            "email": "hr@other.com",
            "password": "StrongPass!123",
            "full_name": "Harper HR",
            "company_name": "Acme Inc",
            "company_website": "https://acme.com",
        }
        response = client.post("/api/hr/register", json=payload)
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "domain_mismatch"


def test_role_guards_block_cross_role_actions() -> None:
    with TestClient(app) as client:
        candidate = _register_candidate(client)
        candidate_token = candidate["access_token"]

        response = client.post(
            "/api/hr/jobs",
            headers=_auth_headers(candidate_token),
            json={
                "title": "Should Fail",
                "description": "Role guard should block this.",
                "required_skills": ["Python"],
                "minimum_experience_years": 1,
            },
        )
        assert response.status_code == 403


def test_candidate_hr_end_to_end_flow_with_notifications_and_ws() -> None:
    with TestClient(app) as client:
        hr = _register_hr(client)
        hr_token = hr["access_token"]

        candidate = _register_candidate(client)
        candidate_token = candidate["access_token"]

        resume = _upload_resume(client, candidate_token)
        resume_id = resume["resume"]["id"]

        job = _post_job(client, hr_token)
        job_id = job["job"]["id"]

        browse = client.get("/api/candidate/jobs", headers=_auth_headers(candidate_token))
        assert browse.status_code == 200, browse.text
        browse_body = browse.json()
        job_items = browse_body["items"]
        assert any(item["id"] == job_id for item in job_items)

        apply = client.post(
            f"/api/candidate/jobs/{job_id}/apply",
            headers=_auth_headers(candidate_token),
            json={"resume_id": resume_id},
        )
        assert apply.status_code == 200, apply.text
        apply_body = apply.json()
        application_id = apply_body["application"]["id"]
        interview_id = apply_body["interview_id"]

        questions_resp = client.get(
            f"/api/candidate/interviews/{interview_id}/questions",
            headers=_auth_headers(candidate_token),
        )
        assert questions_resp.status_code == 200, questions_resp.text
        questions = questions_resp.json()["questions"]
        assert len(questions) >= 5

        answers = [
            "I would clarify requirements, design the API contract, implement FastAPI endpoints, "
            "add tests, and monitor performance."
            for _ in questions
        ]
        complete_resp = client.post(
            f"/api/candidate/interviews/{interview_id}/complete",
            headers=_auth_headers(candidate_token),
            json={
                "answers": answers,
                "transcript": "Candidate discussed design, performance, and reliability trade-offs.",
                "recording_url": None,
            },
        )
        assert complete_resp.status_code == 200, complete_resp.text
        interview = complete_resp.json()["interview"]
        assert interview["status"] == "completed"
        assert interview["overall_score"] is not None

        applicants = client.get(
            f"/api/hr/job/{job_id}/applicants",
            headers=_auth_headers(hr_token),
        )
        assert applicants.status_code == 200, applicants.text
        applicants_body = applicants.json()
        app_items = applicants_body["items"]
        matching = [item for item in app_items if item["application"]["id"] == application_id]
        assert matching, "Expected to find our application in applicants list"
        assert matching[0]["application"]["status"] == "interview_completed"

        # Open the candidate notifications WebSocket to verify connection handshake.
        with client.websocket_connect(f"/ws/notifications?token={candidate_token}") as ws:
            connected = ws.receive_json()
            assert connected["event"] == "ws.connected"

        shortlist_resp = client.post(
            f"/api/hr/applications/{application_id}/status",
            headers=_auth_headers(hr_token),
            json={"status": "shortlisted"},
        )
        assert shortlist_resp.status_code == 200, shortlist_resp.text

        notifications = client.get("/api/candidate/notifications", headers=_auth_headers(candidate_token))
        assert notifications.status_code == 200, notifications.text
        notifications_body = notifications.json()
        assert notifications_body["unread_count"] >= 1

        shortlist_notifications = [
            item for item in notifications_body["items"] if item["type"] == "application_shortlisted"
        ]
        assert shortlist_notifications, "Expected a shortlist notification"
        shortlist_notification_id = shortlist_notifications[0]["id"]

        mark_read = client.post(
            f"/api/candidate/notifications/{shortlist_notification_id}/read",
            headers=_auth_headers(candidate_token),
        )
        assert mark_read.status_code == 200, mark_read.text
        assert mark_read.json()["unread_count"] <= notifications_body["unread_count"]

        dashboard = client.get("/api/candidate/dashboard", headers=_auth_headers(candidate_token))
        assert dashboard.status_code == 200, dashboard.text
        dash = dashboard.json()
        assert dash["jobs_applied"] == 1
        assert dash["jobs_shortlisted"] == 1
        assert dash["interview_performance"]["total_completed"] >= 1
