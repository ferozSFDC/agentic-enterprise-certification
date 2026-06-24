"""Pydantic schemas for item management endpoints."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ItemOption(BaseModel):
    """A single option in an item."""
    text: str
    rationale: str = ""


class ItemCreate(BaseModel):
    """Request to create a new item."""
    domain_id: int = Field(ge=1, le=8)
    objective_id: str = Field(pattern=r"^\d+\.\d+$")
    cc_level: int = Field(ge=2, le=3)
    discrimination: float = Field(default=1.0, ge=0.2, le=3.0)
    difficulty: float = Field(default=0.0, ge=-4.0, le=4.0)
    scenario: str
    stem: str
    options: list[ItemOption] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    status: str = Field(default="pretest", pattern=r"^(pretest|active|retired|flagged)$")
    author: str | None = None


class ItemUpdate(BaseModel):
    """Request to update an existing item."""
    domain_id: int | None = Field(default=None, ge=1, le=8)
    objective_id: str | None = Field(default=None, pattern=r"^\d+\.\d+$")
    cc_level: int | None = Field(default=None, ge=2, le=3)
    discrimination: float | None = Field(default=None, ge=0.2, le=3.0)
    difficulty: float | None = Field(default=None, ge=-4.0, le=4.0)
    scenario: str | None = None
    stem: str | None = None
    options: list[ItemOption] | None = Field(default=None, min_length=4, max_length=4)
    correct_index: int | None = Field(default=None, ge=0, le=3)
    author: str | None = None


class ItemStatusUpdate(BaseModel):
    """Request to change item lifecycle status."""
    status: str = Field(pattern=r"^(pretest|active|retired|flagged)$")


class ItemResponse(BaseModel):
    """Item as returned by the API (full details for admin)."""
    id: UUID
    domain_id: int
    objective_id: str
    cc_level: int
    discrimination: float
    difficulty: float
    scenario: str
    stem: str
    options: list[ItemOption]
    correct_index: int
    status: str
    exposure_count: int
    admin_count: int
    correct_count: int
    sympson_hetter_k: float
    p_value: float | None
    author: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ItemStats(BaseModel):
    """Statistical summary for an item."""
    id: UUID
    admin_count: int
    correct_count: int
    p_value: float | None
    discrimination: float
    difficulty: float
    exposure_rate: float  # exposure_count / total_sessions


class ItemImportRequest(BaseModel):
    """Bulk import request."""
    items: list[ItemCreate]


class ItemImportResponse(BaseModel):
    """Bulk import result."""
    imported: int
    errors: list[str]
