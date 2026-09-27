"""add_anpr_tables

Component 7 — ANPR + Vehicle Intelligence

Adds Component 7 ANPR tables:

  vehicle_sightings   — canonical vehicle sighting entity
  plate_reads         — plate observation records (raw + normalized)
  plate_candidates    — per-read OCR candidates
  anpr_configs        — per-camera ANPR configuration

Revision ID: e1467df5c282
Revises: a1b2c3d4e5f6
Create Date: 2026-09-19 20:55:59.912272

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


revision = 'e1467df5c282'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. vehicle_sightings ───────────────────────────────────────────────────
    op.create_table(
        'vehicle_sightings',
        sa.Column('sighting_id', sa.String(length=64), nullable=False),
        sa.Column('camera_id', sa.String(length=64), nullable=False),
        sa.Column('track_id', sa.String(length=64), nullable=True),
        sa.Column('detection_id', sa.String(length=64), nullable=True),
        sa.Column('vehicle_id', sa.String(length=64), nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('vehicle_class', sa.String(length=32), nullable=False, server_default='UNKNOWN'),
        sa.Column('vehicle_color', sa.String(length=32), nullable=True),
        sa.Column('vehicle_direction', sa.String(length=16), nullable=False, server_default='UNKNOWN'),
        sa.Column('plate_read_id', sa.String(length=64), nullable=True),
        sa.Column('plate_quality', sa.String(length=32), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('detection_quality', sa.String(length=32), nullable=True),
        sa.Column('camera_health_state', sa.String(length=32), nullable=True),
        sa.Column('camera_health_context_json', sa.Text(), nullable=True),
        sa.Column('location_context', sa.String(length=256), nullable=True),
        sa.Column('sector_id', sa.String(length=64), nullable=True),
        sa.Column('zone_id', sa.String(length=64), nullable=True),
        sa.Column('watchlist_status', sa.String(length=32), nullable=False, server_default='NOT_CHECKED'),
        sa.Column('evidence_id', sa.String(length=64), nullable=True),
        sa.Column('event_id', sa.String(length=64), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('incident_id', sa.String(length=64), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=512), nullable=True),
        sa.Column('plate_crop_url', sa.String(length=512), nullable=True),
        sa.Column('provider', sa.String(length=64), nullable=True),
        sa.Column('source', sa.String(length=16), nullable=False, server_default='LIVE'),
        sa.Column('revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('sync_state', sa.String(length=16), nullable=False, server_default='LOCAL_ONLY'),
        sa.Column('sync_payload_hash', sa.String(length=64), nullable=True),
        sa.Column('edge_device_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint('sighting_id'),
    )
    with op.batch_alter_table('vehicle_sightings', schema=None) as batch_op:
        batch_op.create_index('ix_vs_camera_time', ['camera_id', 'observed_at'])
        batch_op.create_index('ix_vs_track', ['track_id'])
        batch_op.create_index('ix_vs_detection', ['detection_id'])
        batch_op.create_index('ix_vs_vehicle', ['vehicle_id'])
        batch_op.create_index('ix_vs_plate', ['plate_read_id'])
        batch_op.create_index('ix_vs_quality', ['plate_quality'])
        batch_op.create_index('ix_vs_class', ['vehicle_class'])
        batch_op.create_index('ix_vs_direction', ['vehicle_direction'])
        batch_op.create_index('ix_vs_incident', ['incident_id'])
        batch_op.create_index('ix_vs_event', ['event_id'])
        batch_op.create_index('ix_vs_correlation', ['correlation_id'])
        batch_op.create_index('ix_vs_evidence', ['evidence_id'])
        batch_op.create_index('ix_vs_provider', ['provider'])
        batch_op.create_index('ix_vs_sync', ['sync_state'])

    # ── 2. plate_reads ─────────────────────────────────────────────────────────
    op.create_table(
        'plate_reads',
        sa.Column('plate_read_id', sa.String(length=64), nullable=False),
        sa.Column('sighting_id', sa.String(length=64), sa.ForeignKey('vehicle_sightings.sighting_id'), nullable=False),
        sa.Column('raw_read', sa.String(length=64), nullable=False),
        sa.Column('normalized_read', sa.String(length=64), nullable=True),
        sa.Column('display_read', sa.String(length=64), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('character_confidence', sa.Text(), nullable=True),
        sa.Column('format_status', sa.String(length=32), nullable=False, server_default='UNKNOWN_FORMAT'),
        sa.Column('quality', sa.String(length=32), nullable=False, server_default='UNKNOWN'),
        sa.Column('crop_reference', sa.String(length=128), nullable=True),
        sa.Column('source_frame_ref', sa.String(length=64), nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=True),
        sa.Column('provider_version', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('plate_read_id'),
        sa.UniqueConstraint('sighting_id', name='uq_pr_sighting'),
    )
    with op.batch_alter_table('plate_reads', schema=None) as batch_op:
        batch_op.create_index('ix_pr_normalized', ['normalized_read'])
        batch_op.create_index('ix_pr_raw', ['raw_read'])

    # ── 3. plate_candidates ────────────────────────────────────────────────────
    op.create_table(
        'plate_candidates',
        sa.Column('candidate_id', sa.String(length=64), nullable=False),
        sa.Column('sighting_id', sa.String(length=64), sa.ForeignKey('vehicle_sightings.sighting_id'), nullable=False),
        sa.Column('plate_read_id', sa.String(length=64), sa.ForeignKey('plate_reads.plate_read_id'), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('raw_read', sa.String(length=64), nullable=False),
        sa.Column('normalized_read', sa.String(length=64), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('character_confidence', sa.Text(), nullable=True),
        sa.Column('format_status', sa.String(length=32), nullable=False, server_default='UNKNOWN_FORMAT'),
        sa.PrimaryKeyConstraint('candidate_id'),
    )
    with op.batch_alter_table('plate_candidates', schema=None) as batch_op:
        batch_op.create_index('ix_pc_plate_read', ['plate_read_id'])
        batch_op.create_index('ix_pc_sighting', ['sighting_id'])
        batch_op.create_index('ix_pc_rank', ['sighting_id', 'rank'])

    # ── 4. anpr_configs ────────────────────────────────────────────────────────
    op.create_table(
        'anpr_configs',
        sa.Column('config_id', sa.String(length=64), nullable=False),
        sa.Column('camera_id', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('tracker_name', sa.String(length=128), nullable=True),
        sa.Column('tracker_version', sa.String(length=64), nullable=True),
        sa.Column('association_profile', sa.String(length=64), nullable=True),
        sa.Column('max_sighting_age_sec', sa.Integer(), nullable=True),
        sa.Column('association_config_json', sa.Text(), nullable=True),
        sa.Column('sample_rate', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('min_frame_interval_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('region_profile', sa.String(length=64), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('configuration_version', sa.String(length=32), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint('config_id'),
    )
    with op.batch_alter_table('anpr_configs', schema=None) as batch_op:
        batch_op.create_index('ix_anc_camera', ['camera_id'])
        batch_op.create_index('ix_anc_active', ['active'])


def downgrade() -> None:
    with op.batch_alter_table('anpr_configs', schema=None) as batch_op:
        batch_op.drop_index('ix_anc_active')
        batch_op.drop_index('ix_anc_camera')
    op.drop_table('anpr_configs')

    with op.batch_alter_table('plate_candidates', schema=None) as batch_op:
        batch_op.drop_index('ix_pc_rank')
        batch_op.drop_index('ix_pc_sighting')
        batch_op.drop_index('ix_pc_plate_read')
    op.drop_table('plate_candidates')

    with op.batch_alter_table('plate_reads', schema=None) as batch_op:
        batch_op.drop_index('ix_pr_raw')
        batch_op.drop_index('ix_pr_normalized')
    op.drop_table('plate_reads')

    with op.batch_alter_table('vehicle_sightings', schema=None) as batch_op:
        batch_op.drop_index('ix_vs_sync')
        batch_op.drop_index('ix_vs_provider')
        batch_op.drop_index('ix_vs_evidence')
        batch_op.drop_index('ix_vs_correlation')
        batch_op.drop_index('ix_vs_event')
        batch_op.drop_index('ix_vs_incident')
        batch_op.drop_index('ix_vs_direction')
        batch_op.drop_index('ix_vs_class')
        batch_op.drop_index('ix_vs_quality')
        batch_op.drop_index('ix_vs_plate')
        batch_op.drop_index('ix_vs_vehicle')
        batch_op.drop_index('ix_vs_detection')
        batch_op.drop_index('ix_vs_track')
        batch_op.drop_index('ix_vs_camera_time')
    op.drop_table('vehicle_sightings')