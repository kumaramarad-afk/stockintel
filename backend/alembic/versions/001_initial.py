"""Initial stockintel schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Canonical SQL lives in /database/schema/schema.sql and is applied by Docker init.
    # Use `alembic revision --autogenerate` for subsequent model changes.


def downgrade() -> None:
    pass
