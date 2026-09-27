// ─────────────────────────────────────────────────────────────────────────────
// routeAnalysisState — Zustand slice for the Route Risk Analysis (USP 5).
//
// UI → hook → store → (Mock)RouteAnalysisService → prototype data now, real
// route engine later. Only the dataset is shared through the store.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { routeAnalysisService } from '@/services/routeAnalysis'
import type { RouteAnalysisData, RouteAnalysisPhase, RouteAnalysisSelection, RouteTimeWindow, RouteLocation, OperationalContext } from '@/types'

export interface RouteAnalysisState {
  data: RouteAnalysisData | null
  loadState: 'idle' | 'loading' | 'ready' | 'error'
  phase: RouteAnalysisPhase
  selection: RouteAnalysisSelection
  timeWindow: RouteTimeWindow
  // Origin/destination for re-analysis
  pendingOrigin: RouteLocation | null
  pendingDestination: RouteLocation | null
  pendingContext: OperationalContext | null

  fetch: (origin: RouteLocation, destination: RouteLocation, context: OperationalContext, window: RouteTimeWindow) => Promise<void>
  setPhase: (phase: RouteAnalysisPhase) => void
  setSelection: (routeId: string | null) => void
  setTimeWindow: (window: RouteTimeWindow) => void
  setPendingInputs: (origin: RouteLocation, destination: RouteLocation, context: OperationalContext) => void
  runSimulation: (incidentX: number, incidentY: number, riskScore: number, affectsRoutes: string[]) => Promise<void>
  refetch: () => Promise<void>
}

export const useRouteAnalysisStore = create<RouteAnalysisState>(set => ({
  data: null,
  loadState: 'idle',
  phase: 'input',
  selection: { routeId: null },
  timeWindow: 'LIVE',
  pendingOrigin: null,
  pendingDestination: null,
  pendingContext: null,

  fetch: async (origin, destination, context, window) => {
    set({ loadState: 'loading', phase: 'analyzing' })
    try {
      const data = await routeAnalysisService.analyzeRoutes({ origin, destination, operationalContext: context, timeWindow: window })
      const recId = data.recommendation.routeId ?? 'ROUTE-B'
      set({
        data,
        loadState: 'ready',
        phase: 'results',
        pendingOrigin: origin,
        pendingDestination: destination,
        pendingContext: context,
        selection: { routeId: recId },
      })
    } catch {
      set({ loadState: 'error', phase: 'input' })
    }
  },

  setPhase: phase => set({ phase }),

  setSelection: routeId => set({ selection: { routeId } }),

  setTimeWindow: window => set({ timeWindow: window }),

  setPendingInputs: (origin, destination, context) => set({ pendingOrigin: origin, pendingDestination: destination, pendingContext: context }),

  runSimulation: async (incidentX, incidentY, riskScore, affectsRoutes) => {
    const { data } = useRouteAnalysisStore.getState()
    if (!data) return
    set({ phase: 'simulating' })
    try {
      const { routes, recommendation } = await routeAnalysisService.simulateIncident({
        analysisId: 'current',
        incident: { x: incidentX, y: incidentY, riskScore, affectsRoutes },
      })
      set({
        data: { ...data, routes, recommendation },
        phase: 'results',
      })
    } catch {
      set({ phase: 'results' })
    }
  },

  refetch: async () => {
    const { pendingOrigin, pendingDestination, pendingContext, timeWindow } = useRouteAnalysisStore.getState()
    if (!pendingOrigin || !pendingDestination || !pendingContext) return
    await useRouteAnalysisStore.getState().fetch(pendingOrigin, pendingDestination, pendingContext, timeWindow)
  },
}))