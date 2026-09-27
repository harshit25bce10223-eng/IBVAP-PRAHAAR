// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — Camera Health service boundary
//
// Phase 1 (current): the exported provider is a mock serving isolated
// development fixtures. No axios, no fake endpoint, no synthetic latency
// pretending to be a backend.
//
// Phase 2 (planned): implement this interface against the real backend and
// swap the singleton in `services/health/index.ts`. Components, hooks and
// stores consume ONLY this interface, so no UI redesign is required.
//
// Planned contract (follows existing `/api/v1` conventions):
//   GET /api/v1/cameras/{camera_id}/health  → CameraHealth
//   GET /api/v1/cameras/health?ids=A,B      → CameraHealth[]
// ─────────────────────────────────────────────────────────────────────────────

import type { CameraHealth } from '@/types/cameraHealth'

export interface IHealthService {
  /** Live/current health record for one camera. */
  get(cameraId: string): Promise<CameraHealth>
  /** Health records for the given cameras (all known when omitted). */
  list(cameraIds?: string[]): Promise<CameraHealth[]>
  /** Data provenance of this provider: 'DEMO' (fixtures) or 'LIVE'. */
  readonly source: 'DEMO' | 'LIVE'
}
