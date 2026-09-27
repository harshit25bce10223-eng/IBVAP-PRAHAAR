// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — detection components barrel
// ─────────────────────────────────────────────────────────────────────────────

export { DetectionOverlay } from './DetectionOverlay'
export type { DetectionDisplayFilters } from './DetectionOverlay'
export { DetectionInspector } from './DetectionInspector'
export { DetectionSummary } from './DetectionSummary'
export { DetectionList } from './DetectionList'
export { DetectionStatus } from './DetectionStatus'
export { DetectionFilters } from './DetectionFilters'
export { DetectionLegend } from './DetectionLegend'

export { fitContain, fitCover, bboxToVB, bboxToContainer } from './geometry'
export type { FitResult, Size, Box } from './geometry'

export {
  formatClassLabel,
  formatConfidence,
  describeConfidence,
  formatClock,
  formatDate,
  formatDetectionCount,
  formatBBox,
  formatFrameInfo,
  formatSourceLabel,
  describeDetection,
} from './detectionFormat'
export {
  CLASS_STROKE,
  CLASS_CHIP,
  badgeTone,
  textTone,
  dotTone,
  toneForFeedState,
  toneForDetectionState,
  toneForQuality,
} from './detectionTone'
export type { DetectionTone } from './detectionTone'