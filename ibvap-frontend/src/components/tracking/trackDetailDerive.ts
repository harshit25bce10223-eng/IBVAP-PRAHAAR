// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — pure derivations for the Track Intelligence workspace
//
// Backs the §12 trajectory-quality notes, the §20 relation vocabulary and the
// §17 display-only relation-status line. Pure functions of the record so the
// workspace wording stays verifiable without a DOM: every note appears only
// when the record itself carries the condition, and a value the record does
// not have is said to be 'not recorded' — never invented.
// ─────────────────────────────────────────────────────────────────────────────

import type { CorrelationGroup } from '@/types/eventCorrelation'
import type { Track } from '@/types/tracking'

/** Section load lifecycle shared by the workspace's record fetches. */
export type SectionLoad = 'idle' | 'loading' | 'ready' | 'error'

/**
 * §12 trajectory quality context. Conditions recorded on the track are turned
 * into operator-readable notes; an unremarkable track yields [] and the
 * workspace states that no flags were recorded.
 */
export function trajectoryQualityNotes(track: Track): string[] {
  const notes: string[] = []
  const health = track.cameraHealthContext ?? null

  if (track.continuityQuality === 'WEAK') {
    notes.push(
      'Limited continuity (WEAK) — recorded observations are sparse or unreliable; movement between them is not represented.'
    )
  } else if (track.continuityQuality === 'MODERATE') {
    notes.push(
      'Moderate continuity — some recorded observations may not connect cleanly; movement between them is not represented.'
    )
  }
  if (health?.status === 'DEGRADED') {
    notes.push('Camera is reporting DEGRADED — feed quality may have limited observation availability for this track.')
  }
  if (health?.status === 'OFFLINE') {
    notes.push('Camera is reporting OFFLINE — no further observations can be recorded while it is offline.')
  }
  if (health?.viewpointShiftDetected) {
    notes.push(
      'Viewpoint shift detected for this camera — stored positions may not align with earlier observations until the view is re-anchored.'
    )
  }
  if (track.missingObservationsNote) {
    notes.push(track.missingObservationsNote)
  } else if (track.dataCompleteness === 'PARTIAL') {
    notes.push('Data completeness PARTIAL — some observations of this track are not represented.')
  }

  return notes
}

/**
 * §20 relation vocabulary — POSSIBLE CONTINUATION / POSSIBLE SAME ENTITY stay
 * explicit as hypotheses. Unknown relation types degrade to a neutral
 * lowercase rendering, never to an identity claim.
 */
export function relationLabel(relationType: string): string {
  if (relationType === 'POSSIBLE_CONTINUATION') return 'Possible continuation'
  if (relationType === 'POSSIBLE_SAME_ENTITY') return 'Possible same entity'
  return relationType.replace(/_/g, ' ').toLowerCase()
}

/**
 * §17 relation status line for a correlation group referenced by the track.
 * Display only — correlation authority stays in Component 4; this never
 * computes a relation, and a missing strength is reported as 'not recorded'.
 */
export function correlationStatusText(load: SectionLoad, group: CorrelationGroup | null): string {
  if (load === 'ready' && group) {
    const events = `${group.eventCount} correlated event${group.eventCount === 1 ? '' : 's'}`
    return `${events} · strength ${group.correlationStrength ?? 'not recorded'} · group status ${group.status.toLowerCase()}`
  }
  if (load === 'error') return 'Relation status unavailable — correlation data could not be loaded.'
  return 'Loading relation status…'
}
