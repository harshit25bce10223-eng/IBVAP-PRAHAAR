// ─────────────────────────────────────────────────────────────────────────────
// प्रहार — Route Risk Analysis types (USP 5)
//
// Contract for the dedicated operational route planning screen: the map is the
// dominant view with comparative route analysis. Centralized so the UI never
// hardcodes cartographic values; mirrors the future seam:
//   Prototype Data → same UI → real Route Engine / API → actual operational system
// ─────────────────────────────────────────────────────────────────────────────

import type { RiskBand } from './commandDashboard'

// ─── Location / POI ───────────────────────────────────────────────────────────
export interface RouteLocation {
  id: string
  label: string
  /** Map viewBox coordinates (1200 × 520) */
  x: number
  y: number
  sectorId: string
}

// ─── Route geometry ───────────────────────────────────────────────────────────
export interface RoutePoint {
  x: number
  y: number
  /** Distance from previous point in meters */
  segmentDistance?: number
}

export interface RouteGeometry {
  points: RoutePoint[]
  /** SVG path string for rendering */
  path: string
  /** Total distance in km */
  distanceKm: number
  /** Estimated time in minutes */
  estimatedTimeMin: number
}

// ─── Route candidate ──────────────────────────────────────────────────────────
export interface RouteCandidate {
  id: string
  name: string
  /** 0-100 risk score */
  riskScore: number
  /** Risk severity band */
  severity: RiskBand
  geometry: RouteGeometry
  /** Historical incident count along/near this route */
  historicalIncidents: number
  /** Current active alerts affecting this route */
  currentAlerts: number
  /** Camera surveillance coverage percentage (0-100) */
  coverage: number
  /** Terrain difficulty context */
  terrain: 'LOW' | 'MODERATE' | 'HIGH'
  /** Restricted zone exposure score (0-100) */
  restrictedZoneExposure: number
  /** Whether this is the recommended route */
  recommended: boolean
}

// ─── Incidents affecting routes ───────────────────────────────────────────────
export interface RouteIncident {
  id: string
  riskScore: number
  band: RiskBand
  title: string
  cameraId: string
  /** Map viewBox coordinates */
  x: number
  y: number
  /** Which route(s) this incident affects */
  affectsRoutes: string[]
}

// ─── Camera coverage along routes ────────────────────────────────────────────
export interface RouteCameraCoverage {
  id: string
  state: 'ONLINE' | 'DEGRADED' | 'OFFLINE'
  /** Map viewBox coordinates */
  x: number
  y: number
  /** Which route(s) this camera covers */
  coversRoutes: string[]
  /** Coverage quality for this route segment */
  coverageQuality: 'HIGH' | 'MEDIUM' | 'LOW'
}

// ─── Restricted zones ─────────────────────────────────────────────────────────
export interface RouteRestrictedZone {
  id: string
  label: string
  /** SVG polygon/path in map viewBox coordinates */
  path: string
  info: string
  /** Which route(s) this zone affects */
  affectsRoutes: string[]
  /** Exposure level for each affected route */
  exposureByRoute: Record<string, number>
}

// ─── Risk factor breakdown ───────────────────────────────────────────────────
export type RouteRiskFactorKey =
  | 'historicalDensity'
  | 'currentAlerts'
  | 'restrictedZoneExposure'
  | 'cameraCoverage'
  | 'recentEntityActivity'
  | 'terrainContext'

export interface RouteRiskFactor {
  key: RouteRiskFactorKey
  label: string
  /** LOW | MEDIUM | HIGH */
  level: 'LOW' | 'MEDIUM' | 'HIGH'
  description: string
}

// ─── Recommendation reasoning ─────────────────────────────────────────────────
export interface RecommendationReason {
  label: string
  description: string
}

// ─── Full route analysis dataset ──────────────────────────────────────────────
export interface RouteAnalysisData {
  sectorRef: string
  coords: string
  /** User-selected origin */
  origin: RouteLocation
  /** User-selected destination */
  destination: RouteLocation
  /** Operational context: Patrol | Movement | Logistics | Inspection | Other */
  operationalContext: string
  /** All feasible route candidates */
  routes: RouteCandidate[]
  /** Incidents currently affecting routes */
  incidents: RouteIncident[]
  /** Camera coverage along routes */
  cameraCoverage: RouteCameraCoverage[]
  /** Restricted zones */
  restrictedZones: RouteRestrictedZone[]
  /** The active recommendation */
  recommendation: {
    routeId: string
    confidence: number
    reasons: RecommendationReason[]
  }
  /** Risk factor breakdown for the recommended route */
  riskFactors: RouteRiskFactor[]
  /** Terrain context for the map */
  terrain: {
    forestPaths: string[]
    hillPaths: string[]
    roadPaths: string[]
    fencePaths: string[]
    waterPaths: string[]
  }
  /** Border reference */
  borderRef: {
    label: string
    path: string
  }
}

// ─── UI State ─────────────────────────────────────────────────────────────────
export type RouteAnalysisPhase =
  | 'input'           // User entering start/destination
  | 'analyzing'       // Analyzing routes
  | 'results'         // Showing route comparison
  | 'simulating'      // What-if simulation running

export interface RouteAnalysisSelection {
  routeId: string | null
}

// ─── Time window for historical data ──────────────────────────────────────────
export type RouteTimeWindow = 'LIVE' | '24H' | '7D' | '30D'

// ─── Available locations for prototype ────────────────────────────────────────
export const ROUTE_LOCATIONS: RouteLocation[] = [
  { id: 'BOP-ALPHA', label: 'Border Outpost Alpha', x: 180, y: 420, sectorId: 'S7-W' },
  { id: 'BOP-BRAVO', label: 'Border Outpost Bravo', x: 320, y: 450, sectorId: 'S7-SW' },
  { id: 'BOP-CHARLIE', label: 'Border Outpost Charlie', x: 80, y: 280, sectorId: 'S7-NW' },
  { id: 'CHK-ALPHA', label: 'Checkpoint Alpha', x: 480, y: 180, sectorId: 'S7-C' },
  { id: 'CHK-BRAVO', label: 'Checkpoint Bravo', x: 650, y: 120, sectorId: 'S7-NE' },
  { id: 'CHK-CHARLIE', label: 'Checkpoint Charlie', x: 920, y: 200, sectorId: 'S7-E' },
  { id: 'CHK-DELTA', label: 'Checkpoint Delta', x: 1050, y: 350, sectorId: 'S7-SE' },
  { id: 'FWD-BASE', label: 'Forward Operating Base', x: 550, y: 400, sectorId: 'S7-C' },
  { id: 'LOG-HUB', label: 'Logistics Hub', x: 200, y: 100, sectorId: 'S7-N' },
]

export const OPERATIONAL_CONTEXTS = [
  'Patrol',
  'Movement',
  'Logistics',
  'Inspection',
  'Other',
] as const

export type OperationalContext = typeof OPERATIONAL_CONTEXTS[number]