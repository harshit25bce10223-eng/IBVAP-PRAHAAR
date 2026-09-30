"""add_unique_member_correlation_event

Revision ID: a4f7c0d91b2e
Revises: ed2783c7ad30
Create Date: 2026-09-27 00:00:00.000000

Adds a unique constraint on correlation_group_members (correlation_id, event_id)
guaranteeing deterministic grouping under concurrent ingestion.
"""

from alembic import op
import sqlalchemy as sa

revision = 'a4f7c0d91b2e'
down_revision = 'ed2783c7ad30'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM correlation_group_members "
        "WHERE id NOT IN (SELECT MIN(id) FROM correlation_group_members "
        "GROUP BY correlation_id, event_id)"
    )
    with op.batch_alter_table('correlation_group_members', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_correlation_members_group_event', ['correlation_id', 'event_id']
        )


def downgrade() -> None:
    with op.batch_alter_table('correlation_group_members', schema=None) as batch_op:
        batch_op.drop_constraint('uq_correlation_members_group_event', type_='unique')