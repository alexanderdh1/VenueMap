"""add composite index on events venue_id start_datetime

Revision ID: c85744bc172a
Revises: 94a33daf89c3
Create Date: 2026-05-02 13:00:24.710429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c85744bc172a'
down_revision: Union[str, Sequence[str], None] = '94a33daf89c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_events_venue_start", "events", ["venue_id", "start_datetime"])


def downgrade() -> None:
    op.drop_index("ix_events_venue_start", table_name="events")
