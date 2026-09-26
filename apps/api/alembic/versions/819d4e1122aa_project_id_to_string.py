"""Change Project ID to string

Revision ID: 819d4e1122aa
Revises: 707c6e4534a4
Create Date: 2026-09-26 12:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '819d4e1122aa'
down_revision: str | None = '707c6e4534a4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        'projects',
        'id',
        existing_type=sa.Uuid(),
        type_=sa.String(length=100),
        existing_nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        'projects',
        'id',
        existing_type=sa.String(length=100),
        type_=sa.Uuid(),
        existing_nullable=False,
        server_default=sa.text('gen_random_uuid()'),
    )
