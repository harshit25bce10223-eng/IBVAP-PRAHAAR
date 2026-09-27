// ─────────────────────────────────────────────────────────────────────────────
// प्रहार — Command Center types (Main Command Dashboard, Sub-Component 2)
//
// Canonical contracts for the unified operational picture: KPIs, the GIS /
// digital-twin layer, active incidents, camera intelligence, system health and
// supporting context. Mirrors the prototype → real-API seam: UI depends only
// on these types, never on hardcoded values inside JSX.
// ─────────────────────────────────────────────────────────────────────────────

// ─── Risk bands (must match the project-wide incident language) ──────────────
export type RiskBand = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export const riskBandFor = (score: number): RiskBand => {
  if (score >= 85) return 'CRITICAL'
  if (score >= 65) return 'HIGH'
  if (score >= 40) return 'MEDIUM'
  return 'LOW'
}

/** Severity → semantic token class (label + dot). Never colour-only. */
export const RISK_BAND_STYLE: Record<RiskBand, { text: string; dot: string; badge: 'critical' | 'warning' | 'safe' | 'info' }> = {
  CRITICAL: { text: 'text-ssb-red-bright',   dot: 'bg-ssb-red-bright',   badge: 'critical' },
  HIGH:     { text: 'text-ssb-red-bright',   dot: 'bg-ssb-red-bright',   badge: 'critical' },
  MEDIUM:   { text: 'text-ssb-amber-bright', dot: 'bg-ssb-amber-bright', badge: 'warning'  },
  LOW:      { text: 'text-ssb-green-bright', dot: 'bg-ssb-green-bright', badge: 'safe'     },
}

// ─── KPI / operational summary ───────────────────────────────────────────────
export interface DashboardKpis {
  totalCameras: number
  onlineCameras: number
  offlineCameras: number
  activeIncidents: number
  incidentHigh: number
  incidentMedium: number
  livePersons: number
  liveVehicles: number
  liveAnimals: number
  systemHealthPct: number
  healthLabel: string
  riskSummary: { critical: number; high: number; medium: number; low: number }
}

// ─── Active incident row (right-hand dominant panel) ─────────────────────────
export interface DashboardIncident {
  id: string
  riskScore: number
  band: RiskBand
  cameraId: string
  title: string
  trackId: string
  correlatedCameras: number
  summary: string
  /** True for the single showcase incident (INC-024). */
  isGolden?: boolean
}

// ─── Golden incident timeline step (the 6-step chain) ────────────────────────
export interface GoldenIncidentStep {
  /** Step order, e.g. "01". */
  step: string
  time: string
  text: string
  cameraId: string
}

export interface GoldenIncident {
  incidentId: string
  entityId: string
  riskScore: number
  band: RiskBand
  correlationCount: number
  steps: GoldenIncidentStep[]
}

// ─── Camera intelligence cards ───────────────────────────────────────────────
export type CameraIntelState = 'ONLINE' | 'DEGRADED' | 'OFFLINE'

export interface DashboardCameraIntel {
  id: string
  state: CameraIntelState
  classification: string
  classConfidence: number
  trackId?: string
  note: string
  stateLabel: string
}

// ─── Human vs animal compact context ─────────────────────────────────────────
export interface HumanAnimalClassification {
  kind: 'ANIMAL' | 'HUMAN'
  confidence: number
  outcome: string
}

export interface HumanAnimalCardData {
  title: string
  cameraId: string
  results: HumanAnimalClassification[]
  purpose: string
}

// ─── System health panel ─────────────────────────────────────────────────────
export type SystemSubState = 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'READY' | 'VERIFIED' | 'STABLE'

export interface SystemHealthEntry {
  name: string
  state: SystemSubState
  monospace: boolean
}

// ─── Activity stream ─────────────────────────────────────────────────────────
export interface ActivityEvent {
  time: string
  text: string
  tone: 'critical' | 'warning' | 'info' | 'safe'
}

// ─── Evidence / trust indicator ──────────────────────────────────────────────
export interface EvidenceTrustInfo {
  state: string
  algorithm: 'SHA-256'
  ledger: string
  security: Array<{ label: string; ok: boolean }>
}

// ─── Alignment of the full dashboard dataset ─────────────────────────────────
export interface CommandDashboardData {
  kpis: DashboardKpis
  goldenIncident: GoldenIncident
  incidents: DashboardIncident[]
  cameras: DashboardCameraIntel[]
  humanAnimal: HumanAnimalCardData
  systemHealth: SystemHealthEntry[]
  activity: ActivityEvent[]
  evidence: EvidenceTrustInfo
}