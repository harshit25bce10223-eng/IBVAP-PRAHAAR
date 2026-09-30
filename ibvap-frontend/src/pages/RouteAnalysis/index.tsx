// ─────────────────────────────────────────────────────────────────────────────
// RouteAnalysis — GIS / OPERATIONAL ROUTE ANALYSIS (USP 5 / SIH screenshot 7)
//
// Risk-Aware Route Recommendation & Border Decision Support
// The officer enters where they want to go → प्रहार compares feasible routes
// using surveillance intelligence and recommends the comparatively lower-risk route.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useCallback, useEffect } from 'react'
import { useRouteAnalysis } from '@/hooks'
import {
  RouteInputPanel,
  RouteMap,
  RouteComparisonPanel,
  RouteLegend,
  RouteRiskFactors,
  DecisionNote,
  UserJourney,
  RouteSkeleton,
} from '@/components/route-analysis'
import { ROUTE_LOCATIONS, OPERATIONAL_CONTEXTS, type RouteTimeWindow, type OperationalContext } from '@/types'

export function RouteAnalysis() {
  const {
    data,
    loadState,
    phase,
    selection,
    timeWindow,
    analyze,
    setPhase,
    setSelection,
    setTimeWindow,
    setPendingInputs,
    runSimulation,
    refetch,
  } = useRouteAnalysis()

  // Local UI state for inputs (before analysis)
  const [origin, setOrigin] = useState<typeof ROUTE_LOCATIONS[0] | null>(ROUTE_LOCATIONS[0])
  const [destination, setDestination] = useState<typeof ROUTE_LOCATIONS[0] | null>(ROUTE_LOCATIONS[4])
  const [operationalContext, setOperationalContext] = useState<OperationalContext>('Patrol')

  // When results are shown, use data's origin/destination
  const displayOrigin = data?.origin ?? origin
  const displayDestination = data?.destination ?? destination
  const displayContext = (data?.operationalContext as OperationalContext) ?? operationalContext

  const handleAnalyze = useCallback(() => {
    if (!origin || !destination) return
    setPendingInputs(origin, destination, operationalContext)
    analyze(origin, destination, operationalContext, timeWindow)
  }, [origin, destination, operationalContext, timeWindow, analyze, setPendingInputs])

  // Automatically analyze on initial load so the operational map and 3 routes are immediately visible
  useEffect(() => {
    if (!data && phase === 'input') {
      handleAnalyze()
    }
  }, [data, phase, handleAnalyze])

  const handleSimulate = useCallback(() => {
    if (!data) return
    // Simulate a new HIGH incident near Route B (the recommended one)
    // This should shift recommendation to Route C
    runSimulation(300, 280, 75, ['ROUTE-B'])
  }, [data, runSimulation])

  const handleReset = useCallback(() => {
    setPhase('input')
    setSelection(null)
    setOrigin(ROUTE_LOCATIONS[0])
    setDestination(ROUTE_LOCATIONS[4])
    setOperationalContext('Patrol')
  }, [setPhase, setSelection])

  const handleOriginChange = useCallback((loc: typeof ROUTE_LOCATIONS[0]) => {
    setOrigin(loc)
  }, [])

  const handleDestinationChange = useCallback((loc: typeof ROUTE_LOCATIONS[0]) => {
    setDestination(loc)
  }, [])

  const handleContextChange = useCallback((ctx: OperationalContext) => {
    setOperationalContext(ctx)
  }, [])

  // Loading skeleton — only during actual loading
  if (loadState === 'loading' && !data) {
    return <RouteSkeleton />
  }

  // Error state
  if (loadState === 'error' && !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <button
          onClick={() => refetch().catch(() => {})}
          className="text-xs text-ssb-amber-bright underline underline-offset-2"
        >
          Failed to load route analysis — try again
        </button>
      </div>
    )
  }

  // Results view
  const showResults = Boolean(data && (phase === 'results' || phase === 'simulating' || phase === 'analyzing'))

  return (
    <div className="h-full flex flex-col gap-3.5 overflow-y-auto p-4 md:p-6 bg-[#080B10]">
      {/* Page identity */}
      <header className="flex items-end justify-between flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold tracking-[0.14em] text-ssb-white uppercase">
            GIS / Operational Route Analysis
          </h1>
          <p className="text-xs text-ssb-text-muted mt-0.5 tracking-wide">
            Risk-Aware Route Recommendation &amp; Border Decision Support
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 font-mono text-[10px] text-cyan-400 uppercase tracking-wider">
            Sector Operations
          </span>
          <span className="text-[10px] font-mono tracking-[0.2em] text-ssb-text-muted/60 uppercase">
            SSB Border Sector · Operational Planning
          </span>
        </div>
      </header>

      {/* Input / Controls */}
      <RouteInputPanel
        origin={displayOrigin}
        destination={displayDestination}
        operationalContext={displayContext}
        timeWindow={timeWindow}
        phase={phase}
        onOriginChange={handleOriginChange}
        onDestinationChange={handleDestinationChange}
        onContextChange={handleContextChange}
        onTimeWindowChange={setTimeWindow}
        onAnalyze={handleAnalyze}
        onSimulate={handleSimulate}
        onReset={handleReset}
        availableLocations={ROUTE_LOCATIONS}
      />

      {/* Results content: show when analysis is complete */}
      {showResults && data && (
        <>
          {/* Main content: Dominant Map (left ~75%) + Route Comparison (right ~25%) */}
          <div className="h-[560px] min-h-[560px] flex gap-3.5 flex-shrink-0">
            {/* Dominant GIS Map */}
            <div className="flex-1 min-w-0 h-full">
              <RouteMap
                className="h-full w-full"
                data={data}
                timeWindow={timeWindow}
                selectedRouteId={selection.routeId}
                onRouteSelect={setSelection}
              />
            </div>

            {/* Right Panel: Complete Route Comparison — ALL 3 ROUTES VISIBLE! */}
            <div className="w-[375px] flex-shrink-0 flex flex-col h-full bg-[#0C121D] rounded-xl border border-[#1E2D40] p-3 shadow-xl overflow-hidden">
              <RouteComparisonPanel
                routes={data.routes}
                selectedRouteId={selection.routeId}
                onSelect={setSelection}
                recommendation={data.recommendation}
              />
            </div>
          </div>

          {/* Bottom bar: Legend | Risk Factors | Decision Note | User Journey */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 flex-shrink-0 pb-4">
            <RouteLegend className="h-full" />
            <RouteRiskFactors
              className="h-full"
              factors={data.riskFactors}
              routeName={data.routes.find(r => r.recommended)?.name ?? 'Route B'}
            />
            <DecisionNote className="h-full" />
            <UserJourney
              className="h-full"
              originLabel={displayOrigin?.label ?? 'Border Outpost Alpha'}
              destinationLabel={displayDestination?.label ?? 'Checkpoint Bravo'}
              recommendedRoute={data.routes.find(r => r.recommended)?.name ?? 'Route B'}
              recommendedScore={data.routes.find(r => r.recommended)?.riskScore ?? 38}
            />
          </div>
        </>
      )}
    </div>
  )
}