// ─────────────────────────────────────────────────────────────────────────────
// useRouteAnalysis — Route Risk Analysis data hook (USP 5).
//
// Architecture: UI → hook/store/service → prototype data now, real route engine later.
// Components never mutate the store or touch the service directly.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from 'react'
import { useRouteAnalysisStore } from '@/store'
import type { RouteLocation, OperationalContext, RouteTimeWindow } from '@/types'

export function useRouteAnalysis() {
  const data = useRouteAnalysisStore(s => s.data)
  const loadState = useRouteAnalysisStore(s => s.loadState)
  const phase = useRouteAnalysisStore(s => s.phase)
  const selection = useRouteAnalysisStore(s => s.selection)
  const timeWindow = useRouteAnalysisStore(s => s.timeWindow)
  const fetch = useRouteAnalysisStore(s => s.fetch)
  const setPhase = useRouteAnalysisStore(s => s.setPhase)
  const setSelection = useRouteAnalysisStore(s => s.setSelection)
  const setTimeWindow = useRouteAnalysisStore(s => s.setTimeWindow)
  const setPendingInputs = useRouteAnalysisStore(s => s.setPendingInputs)
  const runSimulation = useRouteAnalysisStore(s => s.runSimulation)
  const refetch = useRouteAnalysisStore(s => s.refetch)

  return {
    data,
    loadState,
    phase,
    selection,
    timeWindow,
    analyze: fetch,
    setPhase,
    setSelection,
    setTimeWindow,
    setPendingInputs,
    runSimulation,
    refetch,
  }
}