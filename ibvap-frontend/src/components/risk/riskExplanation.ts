// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — Risk Explanation Utilities
// Pure functions for generating explainable human-readable decision narratives.
// ─────────────────────────────────────────────────────────────────────────────

import type { RiskFactor } from '@/types'

/**
 * Deterministically constructs a human-readable operational explanation
 * answering: "WHAT happened, WHERE, and WHY the engine flagged it."
 */
export function generateWhyFlaggedExplanation(
  factors: RiskFactor[],
  zoneName?: string | null
): string {
  if (!factors || factors.length === 0) {
    return 'No analytical risk factors triggered. Observation is within nominal baseline.'
  }

  const parts: string[] = []

  const hasCrossing = factors.some(f => f.code === 'RESTRICTED_ZONE_CROSSING')
  const hasHuman = factors.some(f => f.code === 'OBJECT_HUMAN')
  const hasVehicle = factors.some(f => f.code === 'OBJECT_VEHICLE')
  const hasNight = factors.some(f => f.code === 'NIGHT_TIME')
  const hasMultiCam = factors.some(f => f.code === 'MULTI_CAMERA_CONFIRMATION')
  const hasLowRel = factors.some(f => f.code === 'LOW_RELIABILITY')

  const target = hasHuman ? 'Human entity' : hasVehicle ? 'Vehicle' : 'Object'
  const location = zoneName ? `restricted ${zoneName}` : 'restricted virtual fence zone'

  if (hasCrossing) {
    parts.push(`${target} crossed ${location}`)
  } else {
    parts.push(`${target} observed near ${location}`)
  }

  const contextQualifiers: string[] = []
  if (hasNight) contextQualifiers.push('during active night hours')
  if (hasMultiCam) contextQualifiers.push('confirmed across multiple sensor views')

  if (contextQualifiers.length > 0) {
    parts.push(contextQualifiers.join(' and '))
  }

  let narrative = parts.join(' ') + '.'

  if (hasLowRel) {
    narrative += ' Score is mitigated due to low observation reliability (sensor uncertainty).'
  }

  return narrative
}
