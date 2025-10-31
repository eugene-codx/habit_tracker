"""habits_add_initial_data

Revision ID: b84044fb9deb
Revises: aa9df7c93f9f
Create Date: 2025-08-18 07:18:00.137519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b84044fb9deb'
down_revision: Union[str, None] = 'aa9df7c93f9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            'habits',
            sa.column('id', sa.Integer),
            sa.column('name', sa.String),
            sa.column('is_enabled', sa.Boolean),
            sa.column('created_at', sa.TIMESTAMP),
            sa.column('updated_at', sa.TIMESTAMP),
        ),
        [
            {"id": 1, "name": "Alcohol", "is_enabled": True},
            {"id": 2, "name": "Smoking", "is_enabled": True},
            {"id": 3, "name": "Overeating", "is_enabled": True},
            {"id": 4, "name": "Drugs", "is_enabled": False},
            {"id": 5, "name": "Caffeine", "is_enabled": False},
            {"id": 6, "name": "Gambling", "is_enabled": False},
        ]
    )


def downgrade() -> None:
    op.execute("DELETE FROM habits WHERE name IN ('Alcohol', 'Smoking', 'Overeating')")
