// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — structural track summary
//
// Pure, domain-neutral aggregation of tracks for dashboard and wall surfaces:
// total count, active count, by-class and by-status counts.
// Never calculates risk, severity, or threat scores (§128, §185, §186).
// ─────────────────────────────────────────────────────────────────────────────

import type { DetectionClass } from '@/types/detection'
import type { Track, TrackStatus, TrackSummary } from '@/types/tracking'

export function buildTrackSummary(
  cameraId: string,
  tracks: Track[],
  lastUpdatedAt?: string | null
): TrackSummary {
  const byClass: Partial<Record<DetectionClass, number>> = {
    PERSON: 0,
    VEHICLE: 0,
    ANIMAL: 0,
    OBJECT: 0,
    UNKNOWN: 0,
  }

  const byStatus: Partial<Record<TrackStatus, number>> = {
    ACTIVE: 0,
    TENTATIVE: 0,
    LOST: 0,
    REACQUIRED: 0,
    ENDED: 0,
    STALE: 0,
    INVALID: 0,
    UNKNOWN: 0,
  }

  let totalActive = 0

  for (const t of tracks) {
    byClass[t.objectClass] = (byClass[t.objectClass] ?? 0) + 1
    byStatus[t.status] = (byStatus[t.status] ?? 0) + 1
    if (t.status === 'ACTIVE' || t.status === 'REACQUIRED') {
      totalActive += 1
    }
  }

  return {
    cameraId,
    totalActive,
    totalTracks: tracks.length,
    byClass,
    byStatus,
    lastUpdatedAt: lastUpdatedAt ?? null,
  }
}
