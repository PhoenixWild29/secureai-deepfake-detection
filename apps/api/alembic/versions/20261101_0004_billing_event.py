"""stripe event timestamp for webhook ordering

Revision ID: 20261101_0004
Revises: 20261031_0003
Create Date: 2026-11-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_0004"
down_revision: str | None = "20261031_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "billing_accounts",
        sa.Column("stripe_event_created", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("stripe_event_created", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "stripe_event_created")
    op.drop_column("billing_accounts", "stripe_event_created")
