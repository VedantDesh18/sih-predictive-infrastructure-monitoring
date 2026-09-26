from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class RiskPredictionHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores historical ML risk predictions for model drift and calibration tracking."""

    __tablename__ = "risk_prediction_history"

    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    cost_probability: Mapped[float] = mapped_column(Float, nullable=False)
    schedule_probability: Mapped[float] = mapped_column(Float, nullable=False)
    overall_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Realized outcomes once the project completes, enabling retrospective calibration
    realized_cost_overrun: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    realized_schedule_delay: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_risk_prediction_history_proj_date", "project_id", "snapshot_date", unique=True),
    )

    def __repr__(self) -> str:
        return f"<RiskPredictionHistory(project_id='{self.project_id}', date='{self.snapshot_date}')>"
