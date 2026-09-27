// ─────────────────────────────────────────────────────────────────────────────
// RouteAnalysisService — Interface Contract (USP 5)
//
// The ONLY thing the Route Risk Analysis UI depends on for its operational
// route comparison. Swap implementations (MockRouteAnalysisService →
// RealRouteAnalysisService) without touching any Route Analysis component.
//
// Future API equivalents:
//   POST /route/analyze
//     { origin, destination, operationalContext, timeWindow }
//   GET  /route/candidates/:analysisId
//   GET  /route/incidents/:analysisId?window=live|24h|7d|30d
//   GET  /route/coverage/:analysisId
//   GET  /route/zones/:analysisId
//   POST /route/simulate
//     { analysisId, injectedIncident }
// ─────────────────────────────────────────────────────────────────────────────

import type { RouteAnalysisData, RouteTimeWindow, RouteLocation, OperationalContext } from '@/types'

export interface IRouteAnalysisService {
  /** Analyze feasible routes between origin and destination. */
  analyzeRoutes(params: {
    origin: RouteLocation
    destination: RouteLocation
    operationalContext: OperationalContext
    timeWindow: RouteTimeWindow
  }): Promise<RouteAnalysisData>

  /** Get updated route candidates (for what-if simulation). */
  getRouteCandidates(analysisId: string): Promise<RouteAnalysisData['routes']>

  /** Inject a simulated incident and get updated recommendation. */
  simulateIncident(params: {
    analysisId: string
    incident: { x: number; y: number; riskScore: number; affectsRoutes: string[] }
  }): Promise<{ routes: RouteAnalysisData['routes']; recommendation: RouteAnalysisData['recommendation'] }>
}