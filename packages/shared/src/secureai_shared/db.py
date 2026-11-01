"""SQLAlchemy models for jobs, workspaces, and Stripe billing."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class JobRow(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    org_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    object_key: Mapped[str] = mapped_column(String(512))
    object_etag: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    prediction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BillingAccountRow(Base):
    """Personal Stripe customer. Team subscriptions live on the organization."""

    __tablename__ = "billing_accounts"
    __table_args__ = (UniqueConstraint("stripe_customer_id"),)

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    plan: Mapped[str] = mapped_column(String(16), nullable=False, server_default="free")
    subscription_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Unix seconds of the last Stripe event applied to this account. Older events are ignored.
    stripe_event_created: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrganizationRow(Base):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("stripe_customer_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    plan: Mapped[str] = mapped_column(String(16), nullable=False, server_default="free")
    subscription_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Unix seconds of the last Stripe event applied to this workspace.
    stripe_event_created: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrganizationMemberRow(Base):
    __tablename__ = "organization_members"

    org_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StripeEventRow(Base):
    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CheckoutIntentRow(Base):
    """Plan recorded when this API created a Checkout session.

    checkout.session.completed often has no line items. The webhook uses this
    row only when the event also has no price id, and only if `price_id` is
    still a configured Pro or Team price. metadata.plan is not consulted.
    """

    __tablename__ = "checkout_intents"

    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    plan: Mapped[str] = mapped_column(String(16), nullable=False)
    price_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
