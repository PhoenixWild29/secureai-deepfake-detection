"""billing accounts, organizations, and job workspace

Revision ID: 20261031_0003
Revises: 20261031_0002
Create Date: 2026-10-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261031_0003"
down_revision: str | None = "20261031_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("org_id", sa.String(length=32), nullable=True))
    op.create_index("ix_jobs_org_id", "jobs", ["org_id"])

    op.create_table(
        "billing_accounts",
        sa.Column("user_id", sa.String(length=255), primary_key=True),
        sa.Column("plan", sa.String(length=16), nullable=False, server_default="free"),
        sa.Column("subscription_status", sa.String(length=32), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("stripe_customer_id", name="uq_billing_accounts_stripe_customer_id"),
    )
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("plan", sa.String(length=16), nullable=False, server_default="free"),
        sa.Column("subscription_status", sa.String(length=32), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("stripe_customer_id", name="uq_organizations_stripe_customer_id"),
    )
    op.create_table(
        "organization_members",
        sa.Column("org_id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=255), primary_key=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])
    op.create_table(
        "stripe_events",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("stripe_events")
    op.drop_index("ix_organization_members_user_id", table_name="organization_members")
    op.drop_table("organization_members")
    op.drop_table("organizations")
    op.drop_table("billing_accounts")
    op.drop_index("ix_jobs_org_id", table_name="jobs")
    op.drop_column("jobs", "org_id")
