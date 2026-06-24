import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Integer, Float, Text, Boolean, DateTime, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    """
    An item (question) in the certification exam item bank.

    Each item has IRT parameters (discrimination, difficulty) that determine
    how it behaves in the adaptive algorithm, plus content (scenario, stem, options)
    that the candidate sees.
    """
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Blueprint mapping
    domain_id: Mapped[int] = mapped_column(Integer, nullable=False)
    objective_id: Mapped[str] = mapped_column(String(10), nullable=False)
    cc_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # IRT parameters (2PL)
    discrimination: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )  # a-parameter
    difficulty: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )  # b-parameter

    # Item content
    scenario: Mapped[str] = mapped_column(Text, nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # options format: [{"text": "...", "rationale": "..."}, ...]
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Lifecycle status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pretest"
    )
    # pretest | active | retired | flagged

    # Statistics (updated as items are administered)
    exposure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    admin_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Exposure control (Sympson-Hetter k-parameter)
    sympson_hetter_k: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )

    # Metadata
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Calibration tracking
    last_calibrated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    calibration_n: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        CheckConstraint("cc_level IN (2, 3)", name="check_cc_level"),
        CheckConstraint(
            "status IN ('pretest', 'active', 'retired', 'flagged')",
            name="check_status",
        ),
        CheckConstraint(
            "discrimination BETWEEN 0.2 AND 3.0", name="check_discrimination"
        ),
        CheckConstraint("difficulty BETWEEN -4.0 AND 4.0", name="check_difficulty"),
        CheckConstraint("domain_id BETWEEN 1 AND 8", name="check_domain"),
        Index("idx_items_domain_status", "domain_id", "status"),
        Index("idx_items_status", "status"),
    )

    @property
    def p_value(self) -> float | None:
        """Empirical proportion correct (classical difficulty)."""
        if self.admin_count == 0:
            return None
        return self.correct_count / self.admin_count
