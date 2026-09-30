// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — pure lifecycle derivation helpers (§8–§10, §13, §23)
//
// Everything here reads RECORDED transition records only. No transition is
// ever synthesized from the frontend clock, and a derived value that cannot
// be supported by the records returns null (rendered as N/A, never invented).
// ─────────────────────────────────────────────────────────────────────────────

import type { TrackLifecycleEvent, TrackStatus } from '@/types/tracking'

/** Newest-first ordered copy (backend returns newest-first; this guards anyway). */
export function sortNewestFirst(history: TrackLifecycleEvent[]): TrackLifecycleEvent[] {
  return history
    .slice()
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
}

/** Latest recorded transition whose newStatus matches, else null. */
export function findLatestTransition(
  history: TrackLifecycleEvent[],
  status: TrackStatus
): TrackLifecycleEvent | null {
  let best: TrackLifecycleEvent | null = null
  for (const h of history) {
    if (h.newStatus !== status) continue
    if (!best || new Date(h.timestamp).getTime() > new Date(best.timestamp).getTime()) best = h
  }
  return best
}

/**
 * Lifecycle state at a point in time, derived from recorded transitions:
 * the transition with the latest timestamp ≤ `iso`. Returns null when no
 * record covers that instant (rendered as '—', never assumed).
 */
export function lifecycleStateAt(
  history: TrackLifecycleEvent[],
  iso: string | null | undefined
): TrackStatus | null {
  if (!iso || history.length === 0) return null
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return null
  let state: TrackStatus | null = null
  let bestTime = -Infinity
  for (const h of history) {
    const ht = new Date(h.timestamp).getTime()
    if (Number.isNaN(ht) || ht > t) continue
    if (ht > bestTime) {
      bestTime = ht
      state = h.newStatus
    }
  }
  return state
}

export interface ReacquisitionContext {
  /** The recorded LOST transition. */
  lost: TrackLifecycleEvent
  /** The recorded REACQUIRED transition that followed it. */
  reacquired: TrackLifecycleEvent
  /** Wall-clock gap between the two transitions, in seconds. */
  gapSec: number
}

/**
 * Most recent recorded LOST → REACQUIRED pair. The pair is a continuity
 * hypothesis recorded by the provider — this helper never asserts identity
 * or that the same entity returned (§10, §20).
 */
export function findLatestReacquisition(
  history: TrackLifecycleEvent[]
): ReacquisitionContext | null {
  const ordered = history
    .slice()
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
  let lost: TrackLifecycleEvent | null = null
  let best: ReacquisitionContext | null = null
  for (const h of ordered) {
    if (h.newStatus === 'LOST') lost = h
    if (h.newStatus === 'REACQUIRED' && lost) {
      const gapSec = Math.round(
        (new Date(h.timestamp).getTime() - new Date(lost.timestamp).getTime()) / 1000
      )
      best = { lost, reacquired: h, gapSec }
      lost = null
    }
  }
  return best
}
