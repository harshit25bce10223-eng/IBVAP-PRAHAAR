// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — tracking service barrel
// ─────────────────────────────────────────────────────────────────────────────

import type { ITrackingService } from './ITrackingService'
import { mockTrackingService } from './mockTrackingService'
import { realTrackingService } from './RealTrackingService'

/**
 * Active tracking service singleton.
 * Defaults to mockTrackingService (DEMO). In a deployed Phase-2 environment,
 * this can be switched to realTrackingService without touching UI code.
 */
export const trackingService: ITrackingService = mockTrackingService

export type { ITrackingService } from './ITrackingService'
export { mockTrackingService } from './mockTrackingService'
export { realTrackingService } from './RealTrackingService'
export { buildTrackSummary } from './trackingSummary'
export {
  MOCK_TRACKS,
  MOCK_FEEDS,
  MOCK_OBSERVATIONS,
  DEMO_NOW,
  getMockTrack,
  getMockTrackFeed,
  getMockTrackHistory,
} from './mockTrackingData'
