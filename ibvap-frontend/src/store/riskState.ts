// ─────────────────────────────────────────────────────────────────────────────
// riskState — latest evaluation results + incident feed
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import type { IncidentRecord, RiskResult, TrackEvaluationResponse } from '@/types'

interface RiskStore {
  lastEvaluations: TrackEvaluationResponse[]
  incidents: IncidentRecord[]
  loading: boolean
  error: string | null

  pushEvaluation: (resp: TrackEvaluationResponse) => void
  setIncidents: (incidents: IncidentRecord[]) => void
  prependIncident: (incident: IncidentRecord) => void
  setLoading: (v: boolean) => void
  setError: (msg: string | null) => void
}

const MAX_HELD = 5

export const useRiskStore = create<RiskStore>(set => ({
  lastEvaluations: [],
  incidents: [],
  loading: false,
  error: null,

  pushEvaluation: resp =>
    set(s => ({
      lastEvaluations: [resp, ...s.lastEvaluations].slice(0, MAX_HELD),
    })),

  setIncidents: incidents => set({ incidents }),
  prependIncident: incident =>
    set(s => ({
      incidents: [incident, ...s.incidents.filter(i => i.incident_id !== incident.incident_id)].slice(0, 25),
    })),
  setLoading: v => set({ loading: v }),
  setError: msg => set({ error: msg }),
}))

export function latestRisk(lastEvaluations: TrackEvaluationResponse[]): RiskResult | null {
  if (lastEvaluations.length === 0) return null
  const created = lastEvaluations.filter(e => e.incident.created)
  if (created.length === 0) return null
  return {
    risk_score: created[0].incident.risk_score ?? 0,
    severity: created[0].incident.severity ?? 'LOW',
    factors: created[0].incident.factors,
  }
}