// ─────────────────────────────────────────────────────────────────────────────
// प्रहार — GIS / Digital Twin types
//
// Contract for the dedicated operational GIS screen (SIH screenshot 4): the map
// is the dominant view. Centralized so the UI never hardcodes cartographic
// values; mirrors the future seam:
//   Prototype Data → same UI → real GIS / API → actual operational system
// ─────────────────────────────────────────────────────────────────────────────

import type { RiskBand } from './commandDashboard'

// ─── Layer / time-window controls ────────────────────────────────────────────
export type GisLayerId =
  | 'cameras'
  | 'tracks'
  | 'incidents'
  | 'restrictedZones'
  | 'riskHeat'
  | 'historical'

export type GisTimeWindow = 'LIVE' | '24H' | '7D'

// ─── Camera markers ──────────────────────────────────────────────────────────
export type GisCameraState = 'ONLINE' | 'DEGRADED' | 'OFFLINE'

export interface GisCamera {
  id: string
  state: GisCameraState
  x: number
  y: number
  sectorId: string
}

// ─── Entity trajectory (the Golden Incident, major map element) ──────────────
export interface GisTrackPoint {
  x: number
  y: number
  at: string
}

export interface GisTrackCameraTransition {
  from: string
  to: string
  at: string
  note: string
}

export interface GisTrack {
  id: string
  label: string
  classification: string
  confidence: number
  direction: string
  points: GisTrackPoint[]
  cameraTransitions: GisTrackCameraTransition[]
}

// ─── Incident markers ────────────────────────────────────────────────────────
export interface GisIncident {
  id: string
  riskScore: number
  band: RiskBand
  cameraId: string
  trackId: string
  title: string
  reason: string
  correlationCount: number
  x: number
  y: number
  isGolden?: boolean
}

// ─── Zones / perimeter overlays ──────────────────────────────────────────────
export type GisZoneKind = 'RESTRICTED' | 'FENCE' | 'FOREST' | 'SECTOR'

export interface GisZone {
  id: string
  label: string
  kind: GisZoneKind
  /** SVG polygon/path in map viewBox coordinates. */
  path: string
  info: string
}

// ─── Risk heatmap hotspots ───────────────────────────────────────────────────
export type RiskHeatLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export interface RiskHotspot {
  id: string
  label: string
  level: RiskHeatLevel
  x: number
  y: number
  radius: number
  note: string
}

// ─── Historical activity (repeating pattern locations) ───────────────────────
export type HistoricalKind = 'BREACH' | 'PATROL' | 'ANIMAL' | 'CROSSING'

export interface HistoricalActivity {
  id: string
  kind: HistoricalKind
  label: string
  x: number
  y: number
  count: number
  window: GisTimeWindow
}

// ─── Border reference / terrain context ──────────────────────────────────────
export interface GisBorderRef {
  label: string
  /** Dashed international reference line across the map. */
  path: string
}

// ─── Forest-zone context (human vs animal, compact) ─────────────────────────
export interface ForestZoneContext {
  cameraId: string
  zoneLabel: string
  animal: { confidence: number; outcome: string }
  human: { confidence: number; outcome: string }
  note: string
}

// ─── Full GIS dataset ────────────────────────────────────────────────────────
export interface GisData {
  sectorRef: string
  coords: string
  terrain: { forestPaths: string[]; hillPaths: string[]; roadPaths: string[] }
  borderRef: GisBorderRef
  cameras: GisCamera[]
  tracks: GisTrack[]
  incidents: GisIncident[]
  zones: GisZone[]
  riskHeat: RiskHotspot[]
  historicalActivity: HistoricalActivity[]
  forestZone: ForestZoneContext
}

// ─── Selection model (bottom context strip) ──────────────────────────────────
export type GisSelection =
  | { type: 'incident'; incident: GisIncident }
  | { type: 'zone'; zone: GisZone }
  | { type: 'hotspot'; hotspot: RiskHotspot }
  | { type: 'historical'; activity: HistoricalActivity }
  | { type: 'none' }