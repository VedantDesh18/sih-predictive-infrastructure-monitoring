"""
Project model — represents an infrastructure project tracked by the system.
Links to PAIMANA/OCMS via paimana_project_id.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Project(TimestampMixin, Base):
    """Infrastructure project registered for predictive monitoring."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    paimana_project_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="active"
    )
    # Synthetic MVP portfolio attributes.  A future PAIMANA ingestion service
    # can populate these same fields without changing the risk-engine contract.
    ministry: Mapped[str] = mapped_column(String(160), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    agency: Mapped[str] = mapped_column(String(180), nullable=False)
    location: Mapped[str] = mapped_column(String(180), nullable=False)
    approved_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    revised_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    expenditure: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    planned_progress: Mapped[float] = mapped_column(nullable=False)
    physical_progress: Mapped[float] = mapped_column(nullable=False)
    planned_completion: Mapped[date] = mapped_column(Date, nullable=False)
    expected_completion: Mapped[date] = mapped_column(Date, nullable=False)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_history: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    ml_risk_predictions: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    ml_alerts: Mapped[list[dict[str, object]] | None] = mapped_column(JSON, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    __table_args__ = (
        Index("ix_projects_status", "status"),
        Index("ix_projects_ministry", "ministry"),
        Index("ix_projects_sector", "sector"),
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"
