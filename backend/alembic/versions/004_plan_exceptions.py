"""Add complimentary Premium exception emails.

Revision ID: 004_plan_exceptions
Revises: 003_newsletter_pro
Create Date: 2026-09-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_plan_exceptions"
down_revision: Union[str, None] = "003_newsletter_pro"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "plan_exceptions" in inspector.get_table_names():
        return
    op.create_table(
        "plan_exceptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("plan", sa.String(length=32), server_default="premium", nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_plan_exceptions_email", "plan_exceptions", ["email"], unique=True)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "plan_exceptions" in inspector.get_table_names():
        op.drop_table("plan_exceptions")
