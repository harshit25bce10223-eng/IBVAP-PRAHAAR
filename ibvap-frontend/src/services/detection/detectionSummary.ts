// ─────────────────────────────────────────────────────────────────────────────
// buildSummary — structural detection summary (Component 5)
//
// Pure, domain-neutral aggregation of a feed's detections: total count,
// per-class counts and low-confidence count. Nothing here interprets a
// detection as a threat, risk, identity or correlation — counts only (§116).
// ─────────────────────────────────────────────────────────────────────────────

import type { DetectionFeed, DetectionQuality, DetectionResult, DetectionSummary } from '@/types/detection'

const LOW_CONFIDENCE_MIN = 0.5

export function buildSummary(
  cameraId: string,
  detections: DetectionResult[],
  lastUpdatedAt?: string | null
): DetectionSummary {
  const byClass = { PERSON: 0, VEHICLE: 0, ANIMAL: 0, OBJECT: 0, UNKNOWN: 0 }
  const qualitySummary: Partial<Record<DetectionQuality, number>> = {}
  let lowConfidenceCount = 0

  for (const d of detections) {
    byClass[d.class] = (byClass[d.class] ?? 0) + 1
    qualitySummary[d.quality] = (qualitySummary[d.quality] ?? 0) + 1
    if (d.confidence !== null && d.confidence < LOW_CONFIDENCE_MIN) lowConfidenceCount += 1
  }

  return {
    cameraId,
    total: detections.length,
    byClass,
    lowConfidenceCount,
    qualitySummary,
    lastUpdatedAt: lastUpdatedAt ?? null,
  }
}

/** Convenience: build a summary from a feed record. */
export function buildFeedSummary(feed: DetectionFeed): DetectionSummary {
  return buildSummary(feed.cameraId, feed.detections, feed.lastUpdatedAt)
}