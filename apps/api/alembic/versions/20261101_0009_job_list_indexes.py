"""job list keyset indexes

Revision ID: 20261101_0009
Revises: 20261101_0008
Create Date: 2026-11-01

Personal history is ``user_id`` with ``org_id`` null, newest ``created_at``
then ``id``. Workspace history is one ``org_id`` with the same order. The page
predicate is ``(created_at, id) < (before, before_id)``. ``ix_jobs_user_id``
and ``ix_jobs_org_id`` cannot satisfy that order.

The statements match ``JobRow`` in ``packages/shared``. ``ix_jobs_status``
stays.

"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261101_0009"
down_revision: str | None = "20261101_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_jobs_personal_created_id ON jobs "
        "(user_id, created_at DESC, id DESC) WHERE org_id IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_jobs_org_created_id ON jobs "
        "(org_id, created_at DESC, id DESC) WHERE org_id IS NOT NULL"
    )
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_index("ix_jobs_org_id", table_name="jobs")


def downgrade() -> None:
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_org_id", "jobs", ["org_id"])
    op.drop_index("ix_jobs_personal_created_id", table_name="jobs")
    op.drop_index("ix_jobs_org_created_id", table_name="jobs")
