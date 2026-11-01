"""checkout session plan recorded at creation

Revision ID: 20261101_0005
Revises: 20261101_0004
Create Date: 2026-11-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_0005"
down_revision: str | None = "20261101_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checkout_intents",
        sa.Column("session_id", sa.String(length=255), primary_key=True),
        sa.Column("plan", sa.String(length=16), nullable=False),
        sa.Column("price_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("checkout_intents")
