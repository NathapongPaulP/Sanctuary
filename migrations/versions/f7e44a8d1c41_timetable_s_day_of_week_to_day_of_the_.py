"""TimeTable's day_of_week to day_of_the_week

Revision ID: f7e44a8d1c41
Revises: e66163a74ff5
Create Date: 2026-09-24 16:37:31.363362

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7e44a8d1c41'
down_revision: Union[str, Sequence[str], None] = 'e66163a74ff5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename in place (autogenerate emitted add + drop, which fails on existing
    # rows and would lose data). Postgres updates the CHECK expression itself.
    op.alter_column('timetable', 'day_of_week', new_column_name='day_of_the_week')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('timetable', 'day_of_the_week', new_column_name='day_of_week')
