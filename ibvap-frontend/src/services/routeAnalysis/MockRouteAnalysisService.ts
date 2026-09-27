// ─────────────────────────────────────────────────────────────────────────────
// MockRouteAnalysisService — Prototype implementation (USP 5).
//
// Returns deterministic demo data. Replace with RealRouteAnalysisService when
// the route engine API is available.
// ─────────────────────────────────────────────────────────────────────────────

import { IRouteAnalysisService } from './IRouteAnalysisService'
import type { RouteAnalysisData, RouteLocation, RouteTimeWindow, OperationalContext } from '@/types'
import { createRouteAnalysisDemo } from './mockRouteAnalysisData'

export class MockRouteAnalysisService implements IRouteAnalysisService {
  private currentAnalysisId = 'analysis-001'
  private currentDemo: RouteAnalysisData

  constructor() {
    this.currentDemo = createRouteAnalysisDemo()
  }

  async analyzeRoutes(params: {
    origin: RouteLocation
    destination: RouteLocation
    operationalContext: OperationalContext
    timeWindow: RouteTimeWindow
  }): Promise<RouteAnalysisData> {
    // Simulate network delay
    await new Promise(r => setTimeout(r, 800))

    this.currentAnalysisId = `analysis-${Date.now()}`
    this.currentDemo = createRouteAnalysisDemo(
      params.origin.id,
      params.destination.id,
      params.operationalContext,
      params.timeWindow
    )

    return this.currentDemo
  }

  async getRouteCandidates(): Promise<RouteAnalysisData['routes']> {
    await new Promise(r => setTimeout(r, 300))
    return this.currentDemo.routes
  }

  async simulateIncident(params: {
    analysisId: string
    incident: { x: number; y: number; riskScore: number; affectsRoutes: string[] }
  }): Promise<{ routes: RouteAnalysisData['routes']; recommendation: RouteAnalysisData['recommendation'] }> {
    await new Promise(r => setTimeout(r, 600))

    // Simulate: new incident near Route B increases its risk
    const updatedRoutes = this.currentDemo.routes.map(route => {
      if (params.incident.affectsRoutes.includes(route.id)) {
        const newRisk = Math.min(100, route.riskScore + params.incident.riskScore * 0.4)
        let newSeverity: RouteAnalysisData['routes'][0]['severity'] = 'LOW'
        if (newRisk >= 85) newSeverity = 'CRITICAL'
        else if (newRisk >= 65) newSeverity = 'HIGH'
        else if (newRisk >= 40) newSeverity = 'MEDIUM'

        return { ...route, riskScore: Math.round(newRisk), severity: newSeverity }
      }
      return route
    })

    // Find new recommendation (lowest risk)
    const sorted = [...updatedRoutes].sort((a, b) => a.riskScore - b.riskScore)
    const newRecommended = sorted[0]

    const newRecommendation = {
      routeId: newRecommended.id,
      confidence: Math.max(60, 100 - newRecommended.riskScore),
      reasons: [
        { label: 'Updated comparative risk analysis', description: 'New incident shifted relative risk profile' },
        { label: 'Lowest risk among feasible routes', description: `${newRecommended.name} now has the lowest risk score at ${newRecommended.riskScore}` },
      ],
    }

    // Update demo for subsequent calls
    this.currentDemo = { ...this.currentDemo, routes: updatedRoutes, recommendation: newRecommendation }

    return { routes: updatedRoutes, recommendation: newRecommendation }
  }
}