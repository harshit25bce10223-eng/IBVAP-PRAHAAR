"""add_tracking_engine_tables

Component 6 — Tracking Engine

Adds Component 6 tracking engine tables and extends the legacy 'tracks' table
with lifecycle, provider, cross-component reference, and edge-sync columns.

New tables:
  track_observations   — per-detection observation records
  track_history        — lifecycle state-change audit log
  track_candidates     — cross-camera continuation hypotheses (never identity)
  tracking_configs     — per-camera tracking configuration

Extended table (batch ALTER — SQLite + PostgreSQL compatible):
  tracks  — adds all Component 6 columns while keeping legacy Component 1 columns

Revision ID: a1b2c3d4e5f6
Revises: efd16ef3cf27
Create Date: 2026-09-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision = 'a1b2c3d4e5f6'
down_revision = 'efd16ef3cf27'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend the existing 'tracks' table ─────────────────────────────────
    # Legacy columns already present (from migration fbfa7c0cef4c):
    #   track_id, camera_id, object_type, current_bbox_json, previous_bbox_json,
    #   current_membership_json, previous_membership_json, path_json,
    #   first_seen, last_seen, created_at, updated_at
    #
    # All new columns use server_default to keep existing rows valid.
    # Note: ix_tracks_camera_id already exists from initial migration.

    with op.batch_alter_table('tracks', schema=None) as batch_op:
        # ── Lifecycle ──────────────────────────────────────────────────────────
        batch_op.add_column(sa.Column(
            'status', sa.String(length=16), nullable=False, server_default='UNKNOWN'
        ))
        batch_op.add_column(sa.Column(
            'object_class', sa.String(length=32), nullable=False, server_default='UNKNOWN'
        ))

        # ── Lifecycle timestamps (separate from legacy first_seen/last_seen) ──
        batch_op.add_column(sa.Column(
            'first_seen_at', sa.DateTime(timezone=True), nullable=True
        ))
        batch_op.add_column(sa.Column(
            'last_seen_at', sa.DateTime(timezone=True), nullable=True
        ))

        # ── Current detection reference ────────────────────────────────────────
        batch_op.add_column(sa.Column(
            'current_detection_id', sa.String(length=64), nullable=True
        ))

        # ── Current bbox (flat normalized columns) ─────────────────────────────
        batch_op.add_column(sa.Column('current_bbox_x', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('current_bbox_y', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('current_bbox_width', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('current_bbox_height', sa.Float(), nullable=True))

        # ── Observation counter ────────────────────────────────────────────────
        batch_op.add_column(sa.Column(
            'observation_count', sa.Integer(), nullable=False, server_default='0'
        ))

        # ── Quality / confidence ───────────────────────────────────────────────
        batch_op.add_column(sa.Column('continuity_quality', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True))

        # ── Source & provider provenance ───────────────────────────────────────
        batch_op.add_column(sa.Column(
            'source', sa.String(length=16), nullable=False, server_default='UNKNOWN'
        ))
        batch_op.add_column(sa.Column('provider', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('tracker_name', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tracker_version', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('algorithm_version', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('configuration_version', sa.String(length=64), nullable=True))

        # ── Downstream component soft references ───────────────────────────────
        batch_op.add_column(sa.Column('event_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('correlation_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('incident_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('evidence_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('entity_candidate_id', sa.String(length=64), nullable=True))

        # ── Geographical context ───────────────────────────────────────────────
        batch_op.add_column(sa.Column('sector_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('region_profile', sa.String(length=64), nullable=True))

        # ── Camera Health context snapshot ─────────────────────────────────────
        batch_op.add_column(sa.Column('health_context_json', sa.Text(), nullable=True))

        # ── Class change tracking ──────────────────────────────────────────────
        batch_op.add_column(sa.Column('previous_class', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('class_revision_reason', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('class_revised_at', sa.DateTime(timezone=True), nullable=True))

        # ── Gap / reacquisition counters ───────────────────────────────────────
        batch_op.add_column(sa.Column(
            'gap_count', sa.Integer(), nullable=False, server_default='0'
        ))
        batch_op.add_column(sa.Column(
            'reacquisition_count', sa.Integer(), nullable=False, server_default='0'
        ))
        batch_op.add_column(sa.Column('last_gap_started_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_reacquired_at', sa.DateTime(timezone=True), nullable=True))

        # ── Data completeness ──────────────────────────────────────────────────
        batch_op.add_column(sa.Column(
            'data_completeness', sa.String(length=16), nullable=False, server_default='UNKNOWN'
        ))
        batch_op.add_column(sa.Column('missing_observations_note', sa.String(length=512), nullable=True))

        # ── Optimistic locking + edge sync ─────────────────────────────────────
        batch_op.add_column(sa.Column(
            'revision', sa.Integer(), nullable=False, server_default='1'
        ))
        batch_op.add_column(sa.Column(
            'schema_version', sa.String(length=16), nullable=False, server_default='2.0'
        ))
        batch_op.add_column(sa.Column(
            'sync_state', sa.String(length=16), nullable=False, server_default='LOCAL_ONLY'
        ))
        batch_op.add_column(sa.Column('sync_payload_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('edge_device_id', sa.String(length=64), nullable=True))

        # ── Indexes on new columns ─────────────────────────────────────────────
        batch_op.create_index('ix_tracks_camera_status',    ['camera_id', 'status'])
        batch_op.create_index('ix_tracks_camera_class',     ['camera_id', 'object_class'])
        batch_op.create_index('ix_tracks_camera_time',      ['camera_id', 'last_seen_at'])
        batch_op.create_index('ix_tracks_status',           ['status'])
        batch_op.create_index('ix_tracks_first_seen',       ['first_seen_at'])
        batch_op.create_index('ix_tracks_last_seen',        ['last_seen_at'])
        batch_op.create_index('ix_tracks_current_detection',['current_detection_id'])
        batch_op.create_index('ix_tracks_event',            ['event_id'])
        batch_op.create_index('ix_tracks_incident',         ['incident_id'])
        batch_op.create_index('ix_tracks_correlation',      ['correlation_id'])
        batch_op.create_index('ix_tracks_evidence',         ['evidence_id'])
        batch_op.create_index('ix_tracks_sector',           ['sector_id'])
        batch_op.create_index('ix_tracks_region',           ['region_profile'])
        batch_op.create_index('ix_tracks_source',           ['source'])
        batch_op.create_index('ix_tracks_provider',         ['provider'])
        batch_op.create_index('ix_tracks_sync_state',       ['sync_state'])

    # ── 2. Create track_observations ──────────────────────────────────────────
    op.create_table(
        'track_observations',
        sa.Column('observation_id', sa.String(length=64), nullable=False),
        sa.Column('track_id', sa.String(length=64), nullable=False),
        sa.Column('detection_id', sa.String(length=64), nullable=True),
        sa.Column('camera_id', sa.String(length=64), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=True),
        sa.Column('bbox_x', sa.Float(), nullable=True),
        sa.Column('bbox_y', sa.Float(), nullable=True),
        sa.Column('bbox_width', sa.Float(), nullable=True),
        sa.Column('bbox_height', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('quality', sa.String(length=16), nullable=True),
        sa.Column('occlusion', sa.String(length=16), nullable=True),
        sa.Column('velocity', sa.Float(), nullable=True),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('direction', sa.String(length=32), nullable=True),
        sa.Column('object_class', sa.String(length=32), nullable=True),
        sa.Column('source', sa.String(length=16), nullable=False, server_default='UNKNOWN'),
        sa.Column('provider', sa.String(length=64), nullable=True),
        sa.Column('frame_id', sa.String(length=64), nullable=True),
        sa.Column('frame_number', sa.Integer(), nullable=True),
        sa.Column('evidence_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.track_id'], name='fk_tobs_track'),
        sa.PrimaryKeyConstraint('observation_id'),
        sa.UniqueConstraint('track_id', 'detection_id', name='uq_obs_track_detection'),
    )
    with op.batch_alter_table('track_observations', schema=None) as batch_op:
        batch_op.create_index('ix_tobs_track_time',  ['track_id', 'observed_at'])
        batch_op.create_index('ix_tobs_detection',   ['detection_id'])
        batch_op.create_index('ix_tobs_camera',      ['camera_id'])
        batch_op.create_index('ix_tobs_observed',    ['observed_at'])
        batch_op.create_index('ix_tobs_sequence',    ['track_id', 'sequence'])

    # ── 3. Create track_history ───────────────────────────────────────────────
    op.create_table(
        'track_history',
        sa.Column('history_id', sa.String(length=64), nullable=False),
        sa.Column('track_id', sa.String(length=64), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.String(length=16), nullable=True),
        sa.Column('new_status', sa.String(length=16), nullable=False),
        sa.Column('reason', sa.String(length=256), nullable=True),
        sa.Column('trigger_detection_id', sa.String(length=64), nullable=True),
        sa.Column('provider', sa.String(length=64), nullable=True),
        sa.Column('provider_version', sa.String(length=64), nullable=True),
        sa.Column('configuration_version', sa.String(length=64), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.track_id'], name='fk_thist_track'),
        sa.PrimaryKeyConstraint('history_id'),
    )
    with op.batch_alter_table('track_history', schema=None) as batch_op:
        batch_op.create_index('ix_thist_track_time', ['track_id', 'timestamp'])
        batch_op.create_index('ix_thist_track',      ['track_id'])
        batch_op.create_index('ix_thist_timestamp',  ['timestamp'])

    # ── 4. Create track_candidates ────────────────────────────────────────────
    op.create_table(
        'track_candidates',
        sa.Column('candidate_id', sa.String(length=64), nullable=False),
        sa.Column('source_track_id', sa.String(length=64), nullable=False),
        sa.Column('target_camera_id', sa.String(length=64), nullable=False),
        sa.Column('candidate_track_id', sa.String(length=64), nullable=True),
        sa.Column('relation_type', sa.String(length=32), nullable=False, server_default='POSSIBLE_CONTINUATION'),
        sa.Column('strength', sa.Float(), nullable=True),
        sa.Column('reason', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='OPEN'),
        sa.Column('source', sa.String(length=16), nullable=False, server_default='UNKNOWN'),
        sa.Column('provider', sa.String(length=64), nullable=True),
        sa.Column('gap_duration_sec', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_track_id'], ['tracks.track_id'], name='fk_tcand_source_track'),
        sa.PrimaryKeyConstraint('candidate_id'),
    )
    with op.batch_alter_table('track_candidates', schema=None) as batch_op:
        batch_op.create_index('ix_tcand_source',        ['source_track_id'])
        batch_op.create_index('ix_tcand_target_camera', ['target_camera_id'])
        batch_op.create_index('ix_tcand_candidate',     ['candidate_track_id'])
        batch_op.create_index('ix_tcand_status',        ['status'])
        batch_op.create_index('ix_tcand_expires',       ['expires_at'])

    # ── 5. Create tracking_configs ────────────────────────────────────────────
    op.create_table(
        'tracking_configs',
        sa.Column('config_id', sa.String(length=64), nullable=False),
        sa.Column('camera_id', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('tracker_name', sa.String(length=128), nullable=True),
        sa.Column('tracker_version', sa.String(length=64), nullable=True),
        sa.Column('association_profile', sa.String(length=64), nullable=True),
        sa.Column('max_track_age_sec', sa.Integer(), nullable=True),
        sa.Column('association_config_json', sa.Text(), nullable=True),
        sa.Column('sample_rate', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('min_frame_interval_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('region_profile', sa.String(length=64), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('configuration_version', sa.String(length=32), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('config_id'),
    )
    with op.batch_alter_table('tracking_configs', schema=None) as batch_op:
        batch_op.create_index('ix_trcfg_camera', ['camera_id'])
        batch_op.create_index('ix_trcfg_active', ['active'])


def downgrade() -> None:
    # Remove new tables
    with op.batch_alter_table('tracking_configs', schema=None) as batch_op:
        batch_op.drop_index('ix_trcfg_active')
        batch_op.drop_index('ix_trcfg_camera')
    op.drop_table('tracking_configs')

    with op.batch_alter_table('track_candidates', schema=None) as batch_op:
        batch_op.drop_index('ix_tcand_expires')
        batch_op.drop_index('ix_tcand_status')
        batch_op.drop_index('ix_tcand_candidate')
        batch_op.drop_index('ix_tcand_target_camera')
        batch_op.drop_index('ix_tcand_source')
    op.drop_table('track_candidates')

    with op.batch_alter_table('track_history', schema=None) as batch_op:
        batch_op.drop_index('ix_thist_timestamp')
        batch_op.drop_index('ix_thist_track')
        batch_op.drop_index('ix_thist_track_time')
    op.drop_table('track_history')

    with op.batch_alter_table('track_observations', schema=None) as batch_op:
        batch_op.drop_index('ix_tobs_sequence')
        batch_op.drop_index('ix_tobs_observed')
        batch_op.drop_index('ix_tobs_camera')
        batch_op.drop_index('ix_tobs_detection')
        batch_op.drop_index('ix_tobs_track_time')
    op.drop_table('track_observations')

    # Remove added columns from tracks (batch mode for SQLite)
    with op.batch_alter_table('tracks', schema=None) as batch_op:
        for idx in [
            'ix_tracks_sync_state', 'ix_tracks_provider', 'ix_tracks_source',
            'ix_tracks_region', 'ix_tracks_sector', 'ix_tracks_evidence',
            'ix_tracks_correlation', 'ix_tracks_incident', 'ix_tracks_event',
            'ix_tracks_current_detection', 'ix_tracks_last_seen', 'ix_tracks_first_seen',
            'ix_tracks_status', 'ix_tracks_camera_time', 'ix_tracks_camera_class',
            'ix_tracks_camera_status',
        ]:
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass  # index may not exist on some dialects

        for col in [
            'status', 'object_class', 'first_seen_at', 'last_seen_at',
            'current_detection_id',
            'current_bbox_x', 'current_bbox_y', 'current_bbox_width', 'current_bbox_height',
            'observation_count', 'continuity_quality', 'confidence',
            'source', 'provider', 'tracker_name', 'tracker_version',
            'algorithm_version', 'configuration_version',
            'event_id', 'correlation_id', 'incident_id', 'evidence_id', 'entity_candidate_id',
            'sector_id', 'region_profile', 'health_context_json',
            'previous_class', 'class_revision_reason', 'class_revised_at',
            'gap_count', 'reacquisition_count', 'last_gap_started_at', 'last_reacquired_at',
            'data_completeness', 'missing_observations_note',
            'revision', 'schema_version', 'sync_state', 'sync_payload_hash', 'edge_device_id',
        ]:
            try:
                batch_op.drop_column(col)
            except Exception:
                pass  # column may not exist on older schema
