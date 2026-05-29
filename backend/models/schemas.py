"""
AI Recruitment Automation — Pydantic Schemas

Request/response models for all FastAPI endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Request Schemas ──────────────────────────────────────────────────────────

class CandidateSubmitRequest(BaseModel):
    """Form data submitted with candidate application (non-file fields)."""
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    city: str = Field(..., max_length=50)
    college: str = Field(..., max_length=150)
    role_applied: str = Field(..., max_length=50)


class StatusUpdateRequest(BaseModel):
    """Manual status override request."""
    status: str = Field(..., pattern="^(shortlisted|rejected|manual_review)$")
    notes: Optional[str] = None


# ── Response Schemas ─────────────────────────────────────────────────────────

class SubmitResponse(BaseModel):
    """Response after candidate submission."""
    candidate_id: str
    status: str
    message: str
    match_score: Optional[int] = None
    recommendation: Optional[str] = None
    task_id: Optional[str] = None  # For async processing


class CandidateResponse(BaseModel):
    """Full candidate detail response."""
    id: int
    candidate_id: str
    name: str
    email: str
    phone: Optional[str] = None
    city: Optional[str] = None
    college: Optional[str] = None
    role_applied: Optional[str] = None
    skills: list = []
    experience_years: Optional[float] = None
    education_degree: Optional[str] = None
    education_inst: Optional[str] = None
    github_url: Optional[str] = None
    github_score: Optional[int] = None
    linkedin_url: Optional[str] = None
    resume_path: Optional[str] = None
    application_date: Optional[str] = None
    status: Optional[str] = None
    filter_reason: Optional[str] = None
    match_score: Optional[int] = None
    ai_summary: Optional[str] = None
    matched_skills: list = []
    missing_skills: list = []
    experience_fit: Optional[str] = None
    education_fit: Optional[str] = None
    red_flags: list = []
    recommendation: Optional[str] = None
    best_role: Optional[str] = None
    all_role_scores: Optional[dict] = None
    role_suggestion: Optional[str] = None
    interview_round: int = 0
    interview_date: Optional[str] = None
    shortlist_priority: Optional[int] = None
    is_duplicate: bool = False
    is_spam: bool = False
    spam_reason: Optional[str] = None
    notes: Optional[str] = None
    email_sent: bool = False
    whatsapp_sent: bool = False
    sheets_synced: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CandidateListResponse(BaseModel):
    """Paginated list of candidates."""
    total: int
    candidates: list[CandidateResponse]


class AnalyticsResponse(BaseModel):
    """Dashboard analytics data."""
    total: int
    shortlisted: int
    rejected: int
    manual_review: int
    avg_score: float
    applications_by_role: dict
    score_distribution: list
    status_over_time: list
    top_skills: list


class RoleResponse(BaseModel):
    """Available role with its filtering criteria."""
    name: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: float
    min_match_score: int
    education_required: bool


class TaskStatusResponse(BaseModel):
    """Async task status response."""
    task_id: str
    status: str  # PENDING / STARTED / SUCCESS / FAILURE
    result: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
