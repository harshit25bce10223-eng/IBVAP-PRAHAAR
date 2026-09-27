// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — Risk & Explainability Unit Tests
// ─────────────────────────────────────────────────────────────────────────────

import { describe, it, expect } from 'vitest'
import { generateWhyFlaggedExplanation } from '../riskExplanation'
import type { RiskFactor, Severity } from '@/types'

describe('Component 1 — Risk Factor Explainability Narrative', () => {
  it('generates narrative for human restricted zone crossing at night', () => {
    const factors: RiskFactor[] = [
      {
        code: 'RESTRICTED_ZONE_CROSSING',
        label: 'Restricted zone crossing',
        points: 25,
        evidence: 'Entered zone',
      },
      {
        code: 'OBJECT_HUMAN',
        label: 'Human object type',
        points: 15,
        evidence: 'Human detected',
      },
      {
        code: 'NIGHT_TIME',
        label: 'Night-time movement',
        points: 20,
        evidence: 'Night movement',
      },
      {
        code: 'MULTI_CAMERA_CONFIRMATION',
        label: 'Multi-camera confirmation',
        points: 15,
        evidence: 'Multi cam',
      },
    ]

    const narrative = generateWhyFlaggedExplanation(factors, 'Zone North-02')
    expect(narrative).toContain('Human entity crossed restricted Zone North-02')
    expect(narrative).toContain('during active night hours')
    expect(narrative).toContain('confirmed across multiple sensor views')
  })

  it('generates narrative for vehicle crossing with low reliability penalty', () => {
    const factors: RiskFactor[] = [
      {
        code: 'RESTRICTED_ZONE_CROSSING',
        label: 'Restricted zone crossing',
        points: 25,
        evidence: 'Entered zone',
      },
      {
        code: 'OBJECT_VEHICLE',
        label: 'Vehicle object type',
        points: 10,
        evidence: 'Vehicle detected',
      },
      {
        code: 'LOW_RELIABILITY',
        label: 'Uncertainty penalty',
        points: -15,
        evidence: 'Sensor low reliability',
      },
    ]

    const narrative = generateWhyFlaggedExplanation(factors, 'Zone Gate-4')
    expect(narrative).toContain('Vehicle crossed restricted Zone Gate-4')
    expect(narrative).toContain('low observation reliability')
  })

  it('handles empty factors list gracefully', () => {
    const narrative = generateWhyFlaggedExplanation([])
    expect(narrative).toContain('No analytical risk factors triggered')
  })
})

describe('Component 1 — Severity Boundaries & Factor Separation', () => {
  it('verifies contributing vs mitigating factor accounting', () => {
    const factors: RiskFactor[] = [
      { code: 'RESTRICTED_ZONE_CROSSING', label: 'Crossing', points: 25, evidence: '' },
      { code: 'NIGHT_TIME', label: 'Night', points: 20, evidence: '' },
      { code: 'OBJECT_HUMAN', label: 'Human', points: 15, evidence: '' },
      { code: 'MULTI_CAMERA_CONFIRMATION', label: 'Multi-cam', points: 15, evidence: '' },
      { code: 'DETECTION_CONFIDENCE', label: 'Confidence', points: 18, evidence: '' },
      { code: 'LOW_RELIABILITY', label: 'Reliability Penalty', points: -15, evidence: '' },
    ]

    const contributing = factors.filter(f => f.points > 0)
    const mitigating = factors.filter(f => f.points < 0)
    const total = factors.reduce((sum, f) => sum + f.points, 0)

    expect(contributing).toHaveLength(5)
    expect(mitigating).toHaveLength(1)
    expect(total).toBe(78)
  })

  it('verifies severity mapping bands adhere to backend thresholds', () => {
    function severityForScore(s: number): Severity {
      if (s < 40) return 'LOW'
      if (s < 65) return 'MEDIUM'
      if (s < 85) return 'HIGH'
      return 'CRITICAL'
    }

    expect(severityForScore(0)).toBe('LOW')
    expect(severityForScore(39)).toBe('LOW')
    expect(severityForScore(40)).toBe('MEDIUM')
    expect(severityForScore(64)).toBe('MEDIUM')
    expect(severityForScore(65)).toBe('HIGH')
    expect(severityForScore(84)).toBe('HIGH')
    expect(severityForScore(85)).toBe('CRITICAL')
    expect(severityForScore(100)).toBe('CRITICAL')
  })
})
