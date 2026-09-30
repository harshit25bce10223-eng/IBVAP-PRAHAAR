// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — Evaluation Service
//
// POST /track_and_evaluate is the contract the real Tracking module will
// eventually call. This UI drives it with simulated observations so the
// whole pipeline (geometry → membership → rules → risk → incident) is live.
//
// When the backend is unavailable (demo / Vercel deployment without a live
// backend), we fall back to a safe local mock so no 500 errors appear in
// the browser console and the simulator keeps running normally.
// ─────────────────────────────────────────────────────────────────────────────

import { api } from './api'
import type { TrackEvaluationResponse, TrackObservation } from '@/types'

export interface EvaluationService {
  evaluate(observation: TrackObservation): Promise<TrackEvaluationResponse>
}

/** Silent offline fallback — returned when the backend is unreachable. */
function buildOfflineFallback(observation: TrackObservation): TrackEvaluationResponse {
  return {
    track_id: observation.track_id,
    evaluation: {
      zones: [],
      risk_score: 0,
      rule_results: [],
    },
    incident: { created: false },
    event: { created: false, event_id: null },
  } as unknown as TrackEvaluationResponse
}

export const evaluationService: EvaluationService = {
  async evaluate(observation) {
    try {
      const { data } = await api.post<TrackEvaluationResponse>(
        '/evaluation/track_and_evaluate',
        observation
      )
      return data
    } catch {
      // Backend unavailable (e.g. demo deployment without live API).
      // Return a safe no-op response; the simulator & UI continue normally.
      return buildOfflineFallback(observation)
    }
  },
}