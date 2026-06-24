"""Pydantic schemas for exam session endpoints."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ItemPresentation(BaseModel):
    """An item as presented to the candidate (no correct answer revealed)."""
    id: UUID
    scenario: str
    stem: str
    options: list[str]  # Just the text, no rationale or correctness
    sequence: int


class ExamStartRequest(BaseModel):
    """Request to begin a new exam session."""
    prior_theta: float | None = None  # Optional Bayesian prior


class ExamStartResponse(BaseModel):
    """Response when exam starts — includes first item."""
    session_id: UUID
    item: ItemPresentation
    time_limit_minutes: int
    max_items: int


class ExamRespondRequest(BaseModel):
    """Candidate submits a response."""
    item_id: UUID
    response: int = Field(ge=0, le=3, description="0-based index of selected option")
    presented_at: datetime
    responded_at: datetime


class ExamRespondResponse(BaseModel):
    """Response after processing — either next item or final decision."""
    status: str  # "continue" | "completed"
    items_administered: int
    next_item: ItemPresentation | None = None
    decision: str | None = None  # "PASS" | "FAIL"
    confidence: float | None = None
    reason: str | None = None  # "sprt_pass", "sprt_fail", "ceiling_reached"


class ExamStatusResponse(BaseModel):
    """Current exam session state (for reconnection)."""
    session_id: UUID
    status: str
    items_administered: int
    elapsed_minutes: float
    time_limit_minutes: int
    current_sequence: int
    decision: str | None = None
    confidence: float | None = None
