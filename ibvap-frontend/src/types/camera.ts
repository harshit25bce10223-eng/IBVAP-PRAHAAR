// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — Camera detail types
// ─────────────────────────────────────────────────────────────────────────────

import type { CameraStatus } from './surveillance'

/** Operator-visible feed freshness. Distinct from camera/backend health. */
export type FeedState = 'LIVE' | 'BUFFERING' | 'STALE' | 'OFFLINE' | 'DEGRADED'

export interface CameraDetail {
  id: string
  label: string
  status: CameraStatus
  resolution: { width: number; height: number } // e.g. 1280x720
  fps: number
  lastHeartbeat: string
  uptimeSeconds: number
  /** Configurable deployment profile (SSB sector context), shown only when set. */
  sectorProfile?: string
  /** Optional viewpoint-shift signal from the Camera Health interface. */
  viewpointShiftDetected?: boolean
  /** Optional fence-confidence override from the Camera Health interface. */
  fenceConfidenceOverride?: 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface CameraHealthMetric {
  label: string
  value: string
  ok: boolean
}

export interface UncertaintyState {
  reliability: 'HIGH' | 'MEDIUM' | 'LOW'
  note: string
}

// Demo deployment configuration (not live telemetry). Sector profiles are
// operator-configured context; health values arrive via the health interface.
export const DEFAULT_CAMERAS: CameraDetail[] = [
  {
    id: 'CAM-07',
    label: 'Northern Perimeter',
    status: 'online',
    resolution: { width: 1280, height: 720 },
    fps: 25,
    lastHeartbeat: new Date().toISOString(),
    uptimeSeconds: 7 * 3600 + 42 * 60,
    sectorProfile: 'INDO-NEPAL / FOOTHILL',
  },
  {
    id: 'CAM-12',
    label: 'East Fence Line',
    status: 'online',
    resolution: { width: 1920, height: 1080 },
    fps: 30,
    lastHeartbeat: new Date().toISOString(),
    uptimeSeconds: 23 * 3600 + 5 * 60,
    sectorProfile: 'INDO-BHUTAN / HILLY-FOREST',
  },
  {
    id: 'CAM-03',
    label: 'Checkpoint Gate',
    status: 'degraded',
    resolution: { width: 1920, height: 1080 },
    fps: 30,
    lastHeartbeat: new Date().toISOString(),
    uptimeSeconds: 51 * 60,
    sectorProfile: 'INDO-NEPAL / RURAL FRINGE',
  },
  {
    id: 'CAM-19',
    label: 'Field Edge Post',
    status: 'offline',
    resolution: { width: 1280, height: 720 },
    fps: 25,
    lastHeartbeat: new Date(Date.now() - 11 * 60_000).toISOString(),
    uptimeSeconds: 0,
    sectorProfile: 'INDO-NEPAL / RURAL FRINGE',
  },
  {
    id: 'CAM-05',
    label: 'Riverbed Approach',
    status: 'degraded',
    resolution: { width: 1920, height: 1080 },
    fps: 0,
    lastHeartbeat: new Date().toISOString(),
    uptimeSeconds: 12 * 3600,
    sectorProfile: 'INDO-NEPAL / RIVERINE',
  },
  {
    id: 'CAM-08',
    label: 'Ridge Patrol Post',
    status: 'degraded',
    resolution: { width: 1280, height: 720 },
    fps: 8,
    lastHeartbeat: new Date(Date.now() - 45_000).toISOString(),
    uptimeSeconds: 4 * 3600,
    sectorProfile: 'INDO-BHUTAN / HILLY-FOREST',
  },
  {
    id: 'CAM-09',
    label: 'Sector HQ Gate',
    status: 'online',
    resolution: { width: 1920, height: 1080 },
    fps: 30,
    lastHeartbeat: new Date().toISOString(),
    uptimeSeconds: 48 * 3600,
    sectorProfile: 'INDO-NEPAL / FOOTHILL',
  },
  {
    id: 'CAM-14',
    label: 'Dense Forest Watch',
    status: 'online',
    resolution: { width: 1920, height: 1080 },
    fps: 25,
    lastHeartbeat: new Date().toISOString(),
    uptimeSeconds: 18 * 3600,
    sectorProfile: 'INDO-BHUTAN / HILLY-FOREST',
  },
]