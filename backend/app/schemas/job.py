from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=50)
    responsibilities: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    minimum_experience_years: float = Field(default=0.0, ge=0)
    education_requirement: str | None = None
    location: str | None = None
    employment_type: str | None = None


class JobResponse(BaseModel):
    id: int
    hr_user_id: int
    company_id: int
    title: str
    description: str
    responsibilities: str | None
    required_skills: list[str]
    extracted_required_skills: list[str]
    minimum_experience_years: float
    education_requirement: str | None
    location: str | None
    employment_type: str | None
    status: str
    created_at: str


class JobCreateResponse(BaseModel):
    job: JobResponse


class JobBrowseResponse(BaseModel):
    items: list[dict]
    meta: PaginationMeta


class CompanySummary(BaseModel):
    id: int
    name: str
    website: str
    domain: str


class JobDetailResponse(BaseModel):
    id: int
    hr_user_id: int
    company_id: int
    title: str
    description: str
    responsibilities: str | None
    required_skills: list[str]
    extracted_required_skills: list[str]
    minimum_experience_years: float
    education_requirement: str | None
    location: str | None
    employment_type: str | None
    status: str
    created_at: str
    company: CompanySummary | None
    hr_name: str | None
    eligibility: dict | None
    application: dict | None


class JobApplicantsResponse(BaseModel):
    items: list[dict]
    meta: PaginationMeta
