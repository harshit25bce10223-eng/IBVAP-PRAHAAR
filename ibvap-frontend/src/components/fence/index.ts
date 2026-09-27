// ─────────────────────────────────────────────────────────────────────────────
// Barrel export for Component 1 — Fence & Zone components
// ─────────────────────────────────────────────────────────────────────────────

export { FenceOverlay } from './FenceOverlay'
export { FenceZonePanel } from './FenceZonePanel'
export {
  validateZonePolygon,
  computePolygonArea,
  doSegmentsIntersect,
  formatActiveTimeWindow,
  formatMonitoredObjects,
  formatZoneRuleSummary,
} from './polygonValidation'
export type { PolygonValidationResult } from './polygonValidation'
