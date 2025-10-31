"""Add initial data

Revision ID: 396adff1b13f
Revises: 2e81fbaf9100
Create Date: 2025-03-28 10:59:02.152572

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '396adff1b13f'
down_revision: str | None = '2e81fbaf9100'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            'roles',
            sa.column('name', sa.String),
            sa.column('created_at', sa.TIMESTAMP),
            sa.column('updated_at', sa.TIMESTAMP),
        ),
        [
            {"name": "User"},
            {"name": "Moderator"},
            {"name": "Admin"},
            {"name": "SuperAdmin"},
        ]
    )


def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE name IN ('User', 'Moderator', 'Admin', 'SuperAdmin')")
