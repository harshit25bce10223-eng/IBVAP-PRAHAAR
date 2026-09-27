// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — Detection service boundary
//
// Phase 1 (current): the exported provider is a mock serving isolated
// development fixtures. No axios, no fake endpoint, no synthetic real-time
// pretending to be a live model service.
//
// Phase 2 (planned): implement this interface against the real inference API
// (see mockDetectionData README comments / “future AI model integration” in
// the component spec) and swap the singleton in `services/detection/index.ts`.
// Pages, hooks, stores and components consume ONLY this interface, so no UI
// redesign is required. No component imports mock fixtures except demo/test
// infra. A REAL provider must never silently fall back to mock data — a real
// API failure surfaces “DETECTION DATA UNAVAILABLE”, not demo rows.
//
// Planned contract (follows existing `/api/v1` conventions; final names TBD):
//   GET /api/v1/detections?...filters&sort=&page=     → DetectionResultPage
//   GET /api/v1/detections/{detection_id}             → DetectionResult
//   GET /api/v1/cameras/{camera_id}/detections        → DetectionFeed
//   GET /api/v1/cameras/{camera_id}/detections/summary → DetectionSummary
// ─────────────────────────────────────────────────────────────────────────────

import type {
  DetectionFeed,
  DetectionQuery,
  DetectionResult,
  DetectionResultPage,
  DetectionSummary,
} from '@/types/detection'

export interface IDetectionService {
  /** Paginated, filtered detection list (server-side filtering in Phase 2). */
  listDetections(query: DetectionQuery): Promise<DetectionResultPage>
  /** One detection record. Unknown ids reject so the UI exercises error paths. */
  getDetection(detectionId: string): Promise<DetectionResult>
  /** Full feed for a camera: detections + honest detector availability. */
  getFeed(cameraId: string): Promise<DetectionFeed>
  /** Structural summary counts for a camera feed — never risk values. */
  getSummary(cameraId: string): Promise<DetectionSummary>
  /** Data provenance of this provider: 'DEMO' (fixtures) or 'REAL'. */
  readonly source: 'DEMO' | 'REAL'
}