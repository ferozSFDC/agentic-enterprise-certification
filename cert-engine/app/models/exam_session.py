import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExamSession(Base):
    """
    A single exam session for one candidate.

    Tracks the running state of the CAT algorithm: ability estimate,
    SPRT cumulative LR, items administered, and final decision.
    """
    __tablename__ = "exam_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False
    )

    # Session state
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="in_progress"
    )
    # in_progress | completed_pass | completed_fail | abandoned

    # Running IRT estimates
    current_theta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    theta_se: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    items_administered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # SPRT state
    cumulative_lr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Domain tracking: {"1": 2, "3": 1, "5": 3, ...}
    domain_counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Configuration snapshot (frozen at session start)
    config_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=120)

    # Results (populated on completion)
    decision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    decision_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    responses: Mapped[list["ItemResponse"]] = relationship(
        back_populates="session", order_by="ItemResponse.sequence_number"
    )

    __table_args__ = (
        Index("idx_sessions_candidate", "candidate_id"),
        Index("idx_sessions_status", "status"),
    )


class ItemResponse(Base):
    """
    A single item response within an exam session.

    Records what the candidate answered, whether it was correct,
    and the CAT state snapshot after scoring this response.
    """
    __tablename__ = "item_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id"), nullable=False
    )

    # Response data
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    response: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-based option index
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # CAT state snapshot AFTER this response was scored
    theta_after: Mapped[float] = mapped_column(Float, nullable=False)
    se_after: Mapped[float] = mapped_column(Float, nullable=False)
    lr_after: Mapped[float] = mapped_column(Float, nullable=False)

    # Timing
    presented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    responded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    session: Mapped["ExamSession"] = relationship(back_populates="responses")

    __table_args__ = (
        UniqueConstraint("session_id", "sequence_number", name="uq_session_sequence"),
        UniqueConstraint("session_id", "item_id", name="uq_session_item"),
        Index("idx_responses_session", "session_id"),
        Index("idx_responses_item", "item_id"),
    )
