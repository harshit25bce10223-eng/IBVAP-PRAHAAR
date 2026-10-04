"""add_camera_health_current_shift_confidence

Add the viewpoint shift confidence to the camera_health_current snapshot.

Defect found during §34 clean-environment API validation: the ingest route
persists ``shift_confidence`` (routes.py upsert) but the column was never
added to the model or the schema, so every observation ingest on a fresh
database failed with SQLAlchemy CompileError:
"Unconsumed column names: shift_confidence" -> HTTP 500.

Revision ID: c2b17f04a9d1
Revises: a4f7c0d91b2e
Create Date: 2026-10-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'c2b17f04a9d1'
down_revision = 'a4f7c0d91b2e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('camera_health_current', sa.Column('shift_confidence', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('camera_health_current', schema=None) as batch_op:
        batch_op.drop_column('shift_confidence')
