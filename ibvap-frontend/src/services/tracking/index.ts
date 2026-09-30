// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — tracking service barrel
//
// Mode decides the provider: DEMO serves isolated fixtures; REAL calls the live
// /api/v1 backend. There is NO silent fallback — a REAL provider surfaces
// failures as "TRACKING DATA UNAVAILABLE" and never shows demo tracks in REAL
// mode (spec §25, §28). No component imports mock fixtures directly except
// demo/test infrastructure.
// ─────────────────────────────────────────────────────────────────────────────

import type { ITrackingService } from './ITrackingService'
import { mockTrackingService } from './mockTrackingService'
import { realTrackingService } from './RealTrackingService'

// Determine mode from environment - defaults to DEMO for development.
// Set VITE_TRACKING_MODE=REAL to point the workspace at the live backend.
const isRealMode = import.meta.env.VITE_TRACKING_MODE === 'REAL'

export const trackingService: ITrackingService = isRealMode ? realTrackingService : mockTrackingService

export type { ITrackingService } from './ITrackingService'
export { mockTrackingService } from './mockTrackingService'
export { realTrackingService } from './RealTrackingService'
export { buildTrackSummary } from './trackingSummary'
export {
  MOCK_TRACKS,
  MOCK_FEEDS,
  MOCK_OBSERVATIONS,
  MOCK_LIFECYCLE,
  MOCK_CANDIDATES,
  DEMO_NOW,
  getMockTrack,
  getMockTrackFeed,
  getMockTrackHistory,
  getMockTrackLifecycle,
  getMockTrackCandidates,
} from './mockTrackingData'
