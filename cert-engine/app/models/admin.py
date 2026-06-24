import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdminUser(Base):
    """Admin user for item management and analytics."""
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="viewer"
    )  # viewer | editor | admin
    api_key_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ExamConfig(Base):
    """
    Exam configuration parameters.

    One config is active at a time. Configuration is frozen into
    exam_sessions.config_snapshot when a session starts, so changing
    the config does not affect in-progress sessions.
    """
    __tablename__ = "exam_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # SPRT parameters
    theta_c: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    alpha: Mapped[float] = mapped_column(Float, nullable=False, default=0.05)
    beta: Mapped[float] = mapped_column(Float, nullable=False, default=0.05)

    # Exam structure
    max_items: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    min_items: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)

    # Item selection weights
    w_info: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    w_content: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)

    # Starting theta for new candidates (no prior)
    starting_theta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Domain weights: {"1": 0.15, "2": 0.12, "3": 0.20, ...}
    domain_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Exposure control
    max_exposure_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_snapshot(self) -> dict:
        """Serialize config to a JSON-safe dict for session freezing."""
        return {
            "config_id": self.id,
            "theta_c": self.theta_c,
            "delta": self.delta,
            "alpha": self.alpha,
            "beta": self.beta,
            "max_items": self.max_items,
            "min_items": self.min_items,
            "time_limit_minutes": self.time_limit_minutes,
            "w_info": self.w_info,
            "w_content": self.w_content,
            "starting_theta": self.starting_theta,
            "domain_weights": self.domain_weights,
            "max_exposure_rate": self.max_exposure_rate,
        }
