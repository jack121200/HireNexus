from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.routes import (
    auth_candidate,
    auth_hr,
    candidate_chat,
    candidate_dashboard,
    candidate_interviews,
    candidate_jobs,
    candidate_notifications,
    candidate_resumes,
    hr_applicants,
    hr_applications,
    hr_chat,
    hr_dashboard,
    hr_interviews,
    hr_jobs,
    hr_notifications,
    voice,
    ws,
)
from app.services.realtime import start_realtime, stop_realtime


settings = get_settings()
configure_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.on_event("startup")
async def _startup() -> None:
    await start_realtime()
    logger.info("startup_complete")


@app.on_event("shutdown")
async def _shutdown() -> None:
    await stop_realtime()
    logger.info("shutdown_complete")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Routers
app.include_router(auth_candidate.router)
app.include_router(auth_hr.router)

app.include_router(candidate_dashboard.router)
app.include_router(candidate_resumes.router)
app.include_router(candidate_jobs.router)
app.include_router(candidate_interviews.router)
app.include_router(candidate_notifications.router)
app.include_router(candidate_chat.router)

app.include_router(hr_dashboard.router)
app.include_router(hr_jobs.router)
app.include_router(hr_applicants.router)
app.include_router(hr_applications.router)
app.include_router(hr_interviews.router)
app.include_router(hr_notifications.router)
app.include_router(hr_chat.router)

app.include_router(voice.router)
app.include_router(ws.router)

logger.info("app_started", app_name=settings.app_name, environment=settings.environment)
