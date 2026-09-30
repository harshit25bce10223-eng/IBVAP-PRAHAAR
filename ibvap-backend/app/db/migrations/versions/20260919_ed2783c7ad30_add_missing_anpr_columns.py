"""add_missing_anpr_columns

Add the two columns that were genuinely missing from the initial ANPR migration
(vehicle_sightings.provider_version / schema_version).

NOTE (fixed): this migration previously re-added 8 columns that the initial
migration (e1467df5c282) already creates — sync_state, sync_payload_hash,
edge_device_id, updated_at, thumbnail_url, plate_crop_url, source, revision.
On a fresh database `alembic upgrade head` failed with "duplicate column name".
Only the two real gaps remain.

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
    # Only columns not present in the initial ANPR migration.
    op.add_column('vehicle_sightings', sa.Column('provider_version', sa.String(length=64), nullable=True))
    op.add_column('vehicle_sightings', sa.Column('schema_version', sa.String(length=16), nullable=False, server_default='1.0'))


def downgrade() -> None:
    with op.batch_alter_table('vehicle_sightings', schema=None) as batch_op:
        batch_op.drop_column('schema_version')
        batch_op.drop_column('provider_version')