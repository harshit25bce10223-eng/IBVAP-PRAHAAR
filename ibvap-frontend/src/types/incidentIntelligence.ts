// ─────────────────────────────────────────────────────────────────────────────
// प्रहार — Incident Intelligence types
//
// Contract for the dedicated Incident Intelligence screen (SIH screenshot 5):
// correlated events → explainable risk → trusted evidence. Distinct from the
// events log and from the Command Center.
//
//   Prototype Data → same UI → Real API → Actual investigation system
// ─────────────────────────────────────────────────────────────────────────────

import type { GoldenIncidentStep, RiskBand } from './commandDashboard'

// ─── Explainable risk factors ────────────────────────────────────────────────
export type RiskContributionTone = 'critical' | 'warning' | 'info' | 'safe'

export interface RiskFactorContribution {
  label: string
  points: number
  tone: RiskContributionTone
}

// ─── Evidence record ─────────────────────────────────────────────────────────
export interface IncidentEvidence {
  evidenceId: string
  cameraId: string
  timestamp: string
  media: string
  sha256: string
  ledgerTx: string
  integrity: string
  custody: string
}

// ─── Evidence integrity pipeline ─────────────────────────────────────────────
export interface EvidencePipelineStep {
  label: string
  detail: string
  verified: boolean
}

// ─── Re-ID / camera-chain context ────────────────────────────────────────────
export interface ReIdentificationContext {
  trackId: string
  cameraChain: string
  relationLabel: string
  confidencePct: number
}

// ─── Human-in-the-loop review ────────────────────────────────────────────────
export interface HumanReviewContext {
  title: string
  note: string
}

// ─── Full Incident Intelligence dataset ──────────────────────────────────────
export interface IncidentIntelligenceData {
  incidentId: string
  riskScore: number
  band: RiskBand
  correlationCount: number
  timelineTitle: string
  timeline: GoldenIncidentStep[]
  riskFactors: RiskFactorContribution[]
  bandBrackets: Array<{ label: RiskBand; range: string }>
  decisionNote: string
  reId: ReIdentificationContext
  evidence: IncidentEvidence
  pipeline: EvidencePipelineStep[]
  security: Array<{ label: string; ok: boolean }>
  review: HumanReviewContext
}