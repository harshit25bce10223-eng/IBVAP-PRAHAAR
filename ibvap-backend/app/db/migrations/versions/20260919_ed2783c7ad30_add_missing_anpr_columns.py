"""add_missing_anpr_columns

Add missing columns to ANPR tables that were missing from the initial migration.

Revision ID: ed2783c7ad30
Revises: e1467df5c282
Create Date: 2026-09-19 21:03:09.744070

"""
from alembic import op
import sqlalchemy as sa


revision = 'ed2783c7ad30'
down_revision = 'e1467df5c282'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── vehicle_sightings missing columns ──────────────────────────────────────
    # Add columns one at a time to avoid circular dependency issues with SQLite batch mode
    op.add_column('vehicle_sightings', sa.Column('provider_version', sa.String(length=64), nullable=True))
    op.add_column('vehicle_sightings', sa.Column('schema_version', sa.String(length=16), nullable=False, server_default='1.0'))
    op.add_column('vehicle_sightings', sa.Column('sync_state', sa.String(length=16), nullable=False, server_default='LOCAL_ONLY'))
    op.add_column('vehicle_sightings', sa.Column('sync_payload_hash', sa.String(length=64), nullable=True))
    op.add_column('vehicle_sightings', sa.Column('edge_device_id', sa.String(length=64), nullable=True))
    op.add_column('vehicle_sightings', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.add_column('vehicle_sightings', sa.Column('thumbnail_url', sa.String(length=512), nullable=True))
    op.add_column('vehicle_sightings', sa.Column('plate_crop_url', sa.String(length=512), nullable=True))
    op.add_column('vehicle_sightings', sa.Column('source', sa.String(length=16), nullable=False, server_default='LIVE'))
    op.add_column('vehicle_sightings', sa.Column('revision', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    with op.batch_alter_table('vehicle_sightings', schema=None) as batch_op:
        batch_op.drop_column('provider_version')
        batch_op.drop_column('schema_version')
        batch_op.drop_column('sync_state')
        batch_op.drop_column('sync_payload_hash')
        batch_op.drop_column('edge_device_id')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('thumbnail_url')
        batch_op.drop_column('plate_crop_url')
        batch_op.drop_column('source')
        batch_op.drop_column('revision')