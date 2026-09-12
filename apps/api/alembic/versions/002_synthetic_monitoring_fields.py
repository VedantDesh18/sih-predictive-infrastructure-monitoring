"""Add MVP synthetic monitoring portfolio fields.

Revision ID: 002
Revises: 001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("ministry", sa.String(length=160), nullable=True))
    op.add_column("projects", sa.Column("sector", sa.String(length=100), nullable=True))
    op.add_column("projects", sa.Column("agency", sa.String(length=180), nullable=True))
    op.add_column("projects", sa.Column("location", sa.String(length=180), nullable=True))
    op.add_column("projects", sa.Column("approved_cost", sa.Numeric(16, 2), nullable=True))
    op.add_column("projects", sa.Column("revised_cost", sa.Numeric(16, 2), nullable=True))
    op.add_column("projects", sa.Column("expenditure", sa.Numeric(16, 2), nullable=True))
    op.add_column("projects", sa.Column("planned_progress", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("physical_progress", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("planned_completion", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("expected_completion", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("condition", sa.String(length=50), nullable=True))
    op.add_column("projects", sa.Column("risk_history", sa.JSON(), nullable=True))
    op.add_column(
        "projects", sa.Column("is_synthetic", sa.Boolean(), server_default=sa.text("true"), nullable=False)
    )
    op.create_index("ix_projects_ministry", "projects", ["ministry"])
    op.create_index("ix_projects_sector", "projects", ["sector"])


def downgrade() -> None:
    op.drop_index("ix_projects_sector", table_name="projects")
    op.drop_index("ix_projects_ministry", table_name="projects")
    for column in [
        "is_synthetic", "risk_history", "condition", "expected_completion", "planned_completion",
        "physical_progress", "planned_progress", "expenditure", "revised_cost", "approved_cost",
        "location", "agency", "sector", "ministry",
    ]:
        op.drop_column("projects", column)
