"""Pydantic schemas for admin and auth endpoints."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    """Login request for JWT token."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class CandidateCreate(BaseModel):
    """Request to register a new candidate."""
    email: str
    first_name: str
    last_name: str
    external_id: str | None = None


class CandidateResponse(BaseModel):
    """Candidate as returned by the API."""
    id: UUID
    email: str
    first_name: str
    last_name: str
    external_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExamConfigCreate(BaseModel):
    """Request to create exam configuration."""
    name: str
    theta_c: float = 0.0
    delta: float = Field(default=0.2, ge=0.05, le=0.5)
    alpha: float = Field(default=0.05, ge=0.01, le=0.20)
    beta: float = Field(default=0.05, ge=0.01, le=0.20)
    max_items: int = Field(default=40, ge=10, le=100)
    min_items: int = Field(default=5, ge=1, le=20)
    time_limit_minutes: int = Field(default=120, ge=30, le=300)
    w_info: float = Field(default=0.7, ge=0.0, le=1.0)
    w_content: float = Field(default=0.3, ge=0.0, le=1.0)
    starting_theta: float = Field(default=0.0, ge=-4.0, le=4.0)
    domain_weights: dict[str, float]
    max_exposure_rate: float = Field(default=0.25, ge=0.1, le=1.0)
    is_active: bool = False


class ExamConfigResponse(BaseModel):
    """Exam config as returned by the API."""
    id: int
    name: str
    is_active: bool
    theta_c: float
    delta: float
    alpha: float
    beta: float
    max_items: int
    min_items: int
    time_limit_minutes: int
    w_info: float
    w_content: float
    starting_theta: float
    domain_weights: dict[str, float]
    max_exposure_rate: float
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsSessionSummary(BaseModel):
    """Aggregate session statistics."""
    total_sessions: int
    completed_sessions: int
    pass_count: int
    fail_count: int
    pass_rate: float
    avg_items_administered: float
    avg_items_pass: float
    avg_items_fail: float
    median_items: int


class AnalyticsDomainCoverage(BaseModel):
    """Domain coverage across all sessions."""
    domain_id: int
    target_weight: float
    actual_proportion: float
    deficit: float
    total_items_from_domain: int
