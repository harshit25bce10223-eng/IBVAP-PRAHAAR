// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 1 — Risk domain types (render-only mirror of backend contract)
//
// The backend Risk Engine is authoritative for risk_score, severity and
// factors. This module intentionally contains NO scoring thresholds and NO
// severity mapping — severity arrives verbatim from the backend response.
// ─────────────────────────────────────────────────────────────────────────────

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface RiskFactor {
  code: string
  label: string
  points: number
  evidence: string
}

export interface RiskResult {
  risk_score: number
  severity: Severity
  factors: RiskFactor[]
}

export const SEVERITY_LABEL: Record<Severity, string> = {
  LOW:      'LOW',
  MEDIUM:   'MEDIUM',
  HIGH:     'HIGH',
  CRITICAL: 'CRITICAL',
}