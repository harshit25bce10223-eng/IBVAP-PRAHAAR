// ─────────────────────────────────────────────────────────────────────────────
// Mock Route Analysis prototype data — DEMO ONLY (USP 5).
//
// Centralized so the Route Analysis page never hardcodes cartographic values.
// Consistent with the rest of the prototype (CAM-01/CAM-02/CAM-07/CAM-12,
// TRK-014, INC-024 risk 82 HIGH). Map geometry lives in a 1200 × 520 viewBox
// that matches the dominant full-width map area at 1920 × 1080.
//
//   Prototype Data → same UI → Real Route Engine/API → Actual operational system
// ─────────────────────────────────────────────────────────────────────────────

import type { RouteAnalysisData, RouteLocation, RouteTimeWindow, OperationalContext } from '@/types'
import { ROUTE_LOCATIONS } from '@/types/routeAnalysis'

// Helper to generate SVG path from points
function pointsToPath(points: { x: number; y: number }[]): string {
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
}

// ─── Route geometries (A: direct through restricted, B: recommended around, C: alternative) ───
const ROUTE_A_POINTS = [
  { x: 180, y: 420 }, // BOP Alpha
  { x: 280, y: 380 },
  { x: 380, y: 330 },
  { x: 430, y: 260 }, // Near restricted zone
  { x: 480, y: 200 },
  { x: 530, y: 150 },
  { x: 650, y: 120 }, // Checkpoint Bravo
]

const ROUTE_B_POINTS = [
  { x: 180, y: 420 }, // BOP Alpha
  { x: 220, y: 380 },
  { x: 260, y: 330 },
  { x: 300, y: 280 }, // Goes around restricted zone (south)
  { x: 360, y: 250 },
  { x: 420, y: 220 },
  { x: 490, y: 190 },
  { x: 550, y: 160 },
  { x: 650, y: 120 }, // Checkpoint Bravo
]

const ROUTE_C_POINTS = [
  { x: 180, y: 420 }, // BOP Alpha
  { x: 200, y: 360 },
  { x: 250, y: 300 },
  { x: 320, y: 240 }, // Goes further south, longer
  { x: 400, y: 200 },
  { x: 480, y: 170 },
  { x: 560, y: 150 },
  { x: 650, y: 120 }, // Checkpoint Bravo
]

const routeAPath = pointsToPath(ROUTE_A_POINTS)
const routeBPath = pointsToPath(ROUTE_B_POINTS)
const routeCPath = pointsToPath(ROUTE_C_POINTS)

// Calculate distances
function calcDistance(points: { x: number; y: number }[]): number {
  let total = 0
  for (let i = 1; i < points.length; i++) {
    const dx = points[i].x - points[i - 1].x
    const dy = points[i].y - points[i - 1].y
    total += Math.hypot(dx, dy)
  }
  // Scale: 1200 viewBox units ≈ 12 km (roughly)
  return Math.round((total / 1200) * 12 * 10) / 10
}

const DIST_A = calcDistance(ROUTE_A_POINTS) // ~5.2 km
const DIST_B = calcDistance(ROUTE_B_POINTS) // ~4.8 km
const DIST_C = calcDistance(ROUTE_C_POINTS) // ~5.0 km

// ─── Build the demo data ───
export function createRouteAnalysisDemo(
  originId: string = 'BOP-ALPHA',
  destinationId: string = 'CHK-BRAVO',
  operationalContext: OperationalContext = 'Patrol',
  timeWindow: RouteTimeWindow = 'LIVE'
): RouteAnalysisData {
  const origin = ROUTE_LOCATIONS.find(l => l.id === originId) ?? ROUTE_LOCATIONS[0]
  const destination = ROUTE_LOCATIONS.find(l => l.id === destinationId) ?? ROUTE_LOCATIONS[4]

  return {
    sectorRef: 'SECTOR-7',
    coords: '27.72°N 88.15°E',
    origin,
    destination,
    operationalContext,
    routes: [
      {
        id: 'ROUTE-A',
        name: 'Route A',
        riskScore: 64,
        severity: 'MEDIUM',
        geometry: {
          points: ROUTE_A_POINTS,
          path: routeAPath,
          distanceKm: DIST_A,
          estimatedTimeMin: 46,
        },
        historicalIncidents: 4,
        currentAlerts: 1,
        coverage: 82,
        terrain: 'MODERATE',
        restrictedZoneExposure: 68,
        recommended: false,
      },
      {
        id: 'ROUTE-B',
        name: 'Route B',
        riskScore: 38,
        severity: 'LOW',
        geometry: {
          points: ROUTE_B_POINTS,
          path: routeBPath,
          distanceKm: DIST_B,
          estimatedTimeMin: 42,
        },
        historicalIncidents: 1,
        currentAlerts: 0,
        coverage: 94,
        terrain: 'MODERATE',
        restrictedZoneExposure: 12,
        recommended: true,
      },
      {
        id: 'ROUTE-C',
        name: 'Route C',
        riskScore: 57,
        severity: 'MEDIUM',
        geometry: {
          points: ROUTE_C_POINTS,
          path: routeCPath,
          distanceKm: DIST_C,
          estimatedTimeMin: 44,
        },
        historicalIncidents: 3,
        currentAlerts: 1,
        coverage: 71,
        terrain: 'HIGH',
        restrictedZoneExposure: 25,
        recommended: false,
      },
    ],
    incidents: [
      {
        id: 'INC-024',
        riskScore: 82,
        band: 'HIGH',
        title: 'Restricted Zone Breach',
        cameraId: 'CAM-02',
        x: 492,
        y: 140,
        affectsRoutes: ['ROUTE-A'],
      },
      {
        id: 'INC-031',
        riskScore: 45,
        band: 'MEDIUM',
        title: 'Unusual Dwell Near Trail',
        cameraId: 'CAM-03',
        x: 770,
        y: 295,
        affectsRoutes: ['ROUTE-A', 'ROUTE-C'],
      },
      {
        id: 'INC-018',
        riskScore: 38,
        band: 'LOW',
        title: 'Wildlife Activity',
        cameraId: 'CAM-12',
        x: 165,
        y: 120,
        affectsRoutes: [],
      },
    ],
    cameraCoverage: [
      {
        id: 'CAM-01',
        state: 'ONLINE',
        x: 200,
        y: 270,
        coversRoutes: ['ROUTE-A', 'ROUTE-B'],
        coverageQuality: 'HIGH',
      },
      {
        id: 'CAM-02',
        state: 'ONLINE',
        x: 430,
        y: 210,
        coversRoutes: ['ROUTE-A', 'ROUTE-B', 'ROUTE-C'],
        coverageQuality: 'HIGH',
      },
      {
        id: 'CAM-03',
        state: 'ONLINE',
        x: 700,
        y: 300,
        coversRoutes: ['ROUTE-A', 'ROUTE-C'],
        coverageQuality: 'MEDIUM',
      },
      {
        id: 'CAM-07',
        state: 'DEGRADED',
        x: 900,
        y: 390,
        coversRoutes: ['ROUTE-C'],
        coverageQuality: 'LOW',
      },
      {
        id: 'CAM-12',
        state: 'ONLINE',
        x: 165,
        y: 120,
        coversRoutes: ['ROUTE-B'],
        coverageQuality: 'HIGH',
      },
    ],
    restrictedZones: [
      {
        id: 'ZONE-RZ',
        label: 'RESTRICTED ZONE',
        path: 'M320,155 L475,130 L505,240 L355,270 Z',
        info: 'High-priority buffer — entry requires cleared track authorisation.',
        affectsRoutes: ['ROUTE-A'],
        exposureByRoute: { 'ROUTE-A': 68, 'ROUTE-B': 12, 'ROUTE-C': 25 },
      },
      {
        id: 'ZONE-VF',
        label: 'VIRTUAL FENCE',
        path: 'M0,250 Q120,233 240,240 Q360,247 480,231 Q600,215 720,230 Q840,245 960,225 Q1080,207 1200,221',
        info: 'Perimeter sensing line — breach here raises a zone alert.',
        affectsRoutes: ['ROUTE-A', 'ROUTE-B', 'ROUTE-C'],
        exposureByRoute: { 'ROUTE-A': 15, 'ROUTE-B': 8, 'ROUTE-C': 10 },
      },
    ],
    recommendation: {
      routeId: 'ROUTE-B',
      confidence: 87,
      reasons: [
        { label: 'Lower current incident density', description: 'Zero active alerts along Route B vs 1 on Route A' },
        { label: 'Higher available surveillance coverage', description: '94% camera coverage vs 82% (A) and 71% (C)' },
        { label: 'Lower historical incident concentration', description: '1 historical event vs 4 (A) and 3 (C)' },
        { label: 'Favourable terrain context', description: 'Avoids steep hilly sections and restricted zone exposure' },
      ],
    },
    riskFactors: [
      { key: 'historicalDensity', label: 'Historical Incident Density', level: 'LOW', description: 'Only 1 historical incident in 7D window near Route B' },
      { key: 'currentAlerts', label: 'Current Active Alerts', level: 'LOW', description: 'Zero active alerts affecting recommended route' },
      { key: 'restrictedZoneExposure', label: 'Restricted Zone Exposure', level: 'LOW', description: '12% exposure vs 68% (Route A) and 25% (Route C)' },
      { key: 'cameraCoverage', label: 'Camera Coverage', level: 'LOW', description: '94% surveillance coverage along route' },
      { key: 'recentEntityActivity', label: 'Recent Entity Activity', level: 'LOW', description: 'No recent track activity near Route B corridor' },
      { key: 'terrainContext', label: 'Terrain Context', level: 'MEDIUM', description: 'Moderate terrain; no steep elevation changes' },
    ],
    terrain: {
      forestPaths: [
        'M150,55 q60,50 20,110 q-70,40 -130,0 q-40,-60 0,-100 z',
        'M520,330 q80,-30 120,40 q10,80 -70,100 q-90,10 -110,-55 z',
        'M860,380 q65,-25 100,30 q5,70 -70,82 q-80,12 -90,-50 z',
        'M980,120 q55,-20 90,25 q5,60 -65,70 q-70,10 -80,-40 z',
      ],
      hillPaths: [
        'M40,330 L95,275 L150,330 Z',
        'M120,400 L185,330 L250,400 Z',
        'M290,310 L355,265 L420,310 Z',
        'M620,240 L690,185 L760,240 Z',
        'M880,260 L945,205 L1010,260 Z',
        'M1060,420 L1120,365 L1180,420 Z',
      ],
      roadPaths: [
        'M110,515 L340,320 L520,310 L760,360 L960,440',
        'M380,515 L500,420 L650,370 L880,280 L1120,240',
        'M620,515 L700,440 L820,400',
      ],
      fencePaths: [
        'M0,250 Q120,233 240,240 Q360,247 480,231 Q600,215 720,230 Q840,245 960,225 Q1080,207 1200,221',
      ],
      waterPaths: [
        'M50,480 Q150,470 250,490 Q350,510 450,480',
        'M800,500 Q950,485 1100,510',
      ],
    },
    borderRef: {
      label: 'INDIA — NEPAL',
      path: 'M0,205 Q120,188 240,195 Q360,202 480,186 Q600,170 720,185 Q840,200 960,180 Q1080,162 1200,176',
    },
  }
}

// Default export for initial load
export const ROUTE_ANALYSIS_DEMO = createRouteAnalysisDemo()