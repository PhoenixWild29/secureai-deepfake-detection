"""signed report attestations

Revision ID: 20261101_0007
Revises: 20261101_0006
Create Date: 2026-11-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_0007"
down_revision: str | None = "20261101_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_attestations",
        sa.Column("job_id", sa.String(length=32), primary_key=True),
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column("algorithm", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("job_attestations")
