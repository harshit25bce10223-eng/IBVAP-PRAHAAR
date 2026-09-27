// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — Evaluation Service
//
// POST /track_and_evaluate is the contract the real Tracking module will
// eventually call. This UI drives it with simulated observations so the
// whole pipeline (geometry → membership → rules → risk → incident) is live.
// ─────────────────────────────────────────────────────────────────────────────

import { api } from './api'
import type { TrackEvaluationResponse, TrackObservation } from '@/types'

export interface EvaluationService {
  evaluate(observation: TrackObservation): Promise<TrackEvaluationResponse>
}

export const evaluationService: EvaluationService = {
  async evaluate(observation) {
    const { data } = await api.post<TrackEvaluationResponse>('/evaluation/track_and_evaluate', observation)
    return data
  },
}