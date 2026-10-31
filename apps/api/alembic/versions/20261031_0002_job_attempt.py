"""job attempt counter and object etag

Revision ID: 20261031_0002
Revises: 20261031_0001
Create Date: 2026-10-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261031_0002"
down_revision: str | None = "20261031_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("jobs", sa.Column("object_etag", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "object_etag")
    op.drop_column("jobs", "attempt")
