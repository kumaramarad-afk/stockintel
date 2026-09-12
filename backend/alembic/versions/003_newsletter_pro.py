"""Add Newsletter Pro fields, daily picks, and send tracking.

Revision ID: 003_newsletter_pro
Revises: 002_reports_generated
Create Date: 2026-09-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_newsletter_pro"
down_revision: Union[str, None] = "002_reports_generated"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    user_cols = _columns("users")
    if "newsletter_subscription_status" not in user_cols:
        op.add_column(
            "users",
            sa.Column("newsletter_subscription_status", sa.String(length=50), server_default="none", nullable=False),
        )
    if "newsletter_email_preference" not in user_cols:
        op.add_column(
            "users",
            sa.Column("newsletter_email_preference", sa.String(length=50), server_default="daily", nullable=False),
        )
    if "newsletter_subscribed_at" not in user_cols:
        op.add_column("users", sa.Column("newsletter_subscribed_at", sa.DateTime(timezone=True), nullable=True))

    issue_cols = _columns("newsletter_issues")
    if "ticker" not in issue_cols:
        op.add_column("newsletter_issues", sa.Column("ticker", sa.String(length=16), nullable=True))

    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "newsletter_picks" not in tables:
        op.create_table(
            "newsletter_picks",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("pick_date", sa.Date(), nullable=False, unique=True),
            sa.Column("ticker", sa.String(length=16), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("analyst_upgrades", sa.Integer(), server_default="0", nullable=False),
            sa.Column("institutional_buying", sa.Float(), server_default="0", nullable=False),
            sa.Column("sentiment", sa.String(length=50), server_default="bullish", nullable=False),
            sa.Column("issue_id", sa.Uuid(), sa.ForeignKey("newsletter_issues.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if "newsletter_sends" not in tables:
        op.create_table(
            "newsletter_sends",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("pick_id", sa.Uuid(), sa.ForeignKey("newsletter_picks.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("click_url", sa.String(length=255), nullable=True),
        )
        op.create_index("idx_newsletter_sends_user", "newsletter_sends", ["user_id"])
        op.create_index("idx_newsletter_sends_pick", "newsletter_sends", ["pick_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "newsletter_sends" in tables:
        op.drop_table("newsletter_sends")
    if "newsletter_picks" in tables:
        op.drop_table("newsletter_picks")
    issue_cols = _columns("newsletter_issues")
    if "ticker" in issue_cols:
        op.drop_column("newsletter_issues", "ticker")
    user_cols = _columns("users")
    if "newsletter_subscribed_at" in user_cols:
        op.drop_column("users", "newsletter_subscribed_at")
    if "newsletter_email_preference" in user_cols:
        op.drop_column("users", "newsletter_email_preference")
    if "newsletter_subscription_status" in user_cols:
        op.drop_column("users", "newsletter_subscription_status")
