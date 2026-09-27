// ─────────────────────────────────────────────────────────────────────────────
// Route Analysis Service — Barrel
// ─────────────────────────────────────────────────────────────────────────────

export type { IRouteAnalysisService } from './IRouteAnalysisService'
export { MockRouteAnalysisService } from './MockRouteAnalysisService'
export { createRouteAnalysisDemo, ROUTE_ANALYSIS_DEMO } from './mockRouteAnalysisData'

// Singleton instance for the prototype
import { MockRouteAnalysisService } from './MockRouteAnalysisService'
export const routeAnalysisService = new MockRouteAnalysisService()