import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Candidate(Base):
    """
    A certification exam candidate.

    Stores identity and optional Bayesian prior from previous attempts
    or diagnostic assessments.
    """
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )  # e.g., Salesforce Contact ID
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional Bayesian prior (from prior exam attempts or practice)
    prior_theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    prior_se: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_candidates_email", "email"),
    )
