"""quota placeholder for a deleted job

Revision ID: 20261101_0010
Revises: 20261101_0009
Create Date: 2026-11-01

Deleting a job removes the ``jobs`` row, the video, and any attestation.
The monthly cap still counts a job that had already counted. This table
stores that fact without the filename, the score, or the object key.
``created_at`` is the original job time.

The statements match ``JobTombstoneRow`` in ``packages/shared``.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_0010"
down_revision: str | None = "20261101_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_tombstones",
        sa.Column("job_id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("org_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_job_tombstones_user_created",
        "job_tombstones",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_job_tombstones_org_created",
        "job_tombstones",
        ["org_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_tombstones_org_created", table_name="job_tombstones")
    op.drop_index("ix_job_tombstones_user_created", table_name="job_tombstones")
    op.drop_table("job_tombstones")
