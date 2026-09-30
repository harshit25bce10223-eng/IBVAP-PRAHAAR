// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — tracking components barrel
// ─────────────────────────────────────────────────────────────────────────────

export { TrackOverlay } from './TrackOverlay'
export type { TrackDisplayFilters } from './TrackOverlay'
export { TrackInspector } from './TrackInspector'
export { TrackList } from './TrackList'
export { TrackSummary } from './TrackSummary'
export { TrackTimeline } from './TrackTimeline'
export { TrackTrajectory } from './TrackTrajectory'
export { TrackStatus } from './TrackStatus'
export { TrackFilters } from './TrackFilters'
export { TrackLegend } from './TrackLegend'
export { TrackLifecycleTimeline, StateChip } from './TrackLifecycleTimeline'
export { TrackObservationTable } from './TrackObservationTable'
export {
  sortNewestFirst,
  findLatestTransition,
  lifecycleStateAt,
  findLatestReacquisition,
} from './trackLifecycle'
export type { ReacquisitionContext } from './trackLifecycle'

export {
  trajectoryQualityNotes,
  relationLabel,
  correlationStatusText,
} from './trackDetailDerive'
export type { SectionLoad } from './trackDetailDerive'

export { fitContain, fitCover, bboxToVB, pointToVB, bboxToContainer, pointsToContainer } from './geometry'
export type { FitResult, Size, Box } from './geometry'

export {
  formatTrackClassLabel,
  formatConfidence,
  describeConfidence,
  formatClock,
  formatDate,
  formatDuration,
  formatSpeed,
  formatVelocity,
  formatObservationCount,
  formatBBox,
  formatSourceLabel,
  formatTrackStatus,
  formatContinuityQuality,
  describeTrack,
} from './trackFormat'
export {
  TRACK_CLASS_STROKE,
  TRACK_CLASS_CHIP,
  toneForStatus,
  toneForQuality,
  toneForFeedState,
  toneForSource,
  toneForCameraHealth,
  badgeTone,
  textTone,
  dotTone,
} from './trackTone'
export type { TrackTone } from './trackTone'