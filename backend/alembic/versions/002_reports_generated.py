"""Add users.reports_generated quota counter.

Revision ID: 002_reports_generated
Revises: 001_initial
Create Date: 2026-09-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_reports_generated"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "reports_generated" not in columns:
        op.add_column(
            "users",
            sa.Column("reports_generated", sa.Integer(), nullable=False, server_default="0"),
        )
    op.execute(
        """
        UPDATE users
        SET reports_generated = (
            SELECT COUNT(*) FROM report_views WHERE report_views.user_id = users.id
        )
        WHERE COALESCE(reports_generated, 0) = 0
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "reports_generated" in columns:
        op.drop_column("users", "reports_generated")
