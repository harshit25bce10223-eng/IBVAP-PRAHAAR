// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — ANPR + Vehicle Intelligence Types
// Decision-support language only. Never "Confirmed", never "Verified".
// ─────────────────────────────────────────────────────────────────────────────

export type PlateQuality = 'GOOD' | 'FAIR' | 'POOR' | 'UNREADABLE' | 'PARTIAL' | 'GLARE' | 'MOTION_BLUR' | 'OCCLUDED' | 'EXTREME_ANGLE' | 'DIRTY' | 'LOW_LIGHT' | 'UNKNOWN'
export type VehicleClass = 'PERSONAL_CAR' | 'SUV' | 'TRUCK' | 'BUS' | 'VAN' | 'MOTORCYCLE' | 'SCOOTER' | 'TRACTOR' | 'THREE_WHEELER' | 'UTILITY' | 'OTHER' | 'UNKNOWN'
export type VehicleColor = 'WHITE' | 'BLACK' | 'GREY' | 'SILVER' | 'RED' | 'BLUE' | 'GREEN' | 'YELLOW' | 'BROWN' | 'OTHER' | 'UNKNOWN'
export type VehicleDirection = 'NORTH' | 'SOUTH' | 'EAST' | 'WEST' | 'INBOUND' | 'OUTBOUND' | 'UNKNOWN'
export type PlateFormatStatus = 'VALID_FORMAT' | 'POSSIBLE_FORMAT' | 'INVALID_FORMAT' | 'UNKNOWN_FORMAT' | 'NOT_ENOUGH_DATA'
export type WatchlistStatus = 'WATCHLIST_MATCH' | 'NO_MATCH' | 'UNKNOWN' | 'NOT_CHECKED'

export interface PlateCandidate {
  rank: number
  rawRead: string
  normalizedRead: string | null
  confidence: number
  characterConfidence: number[] | null
  formatStatus: PlateFormatStatus
}

export interface PlateRead {
  rawRead: string
  normalizedRead: string | null
  displayRead: string
  confidence: number
  characterConfidence: number[] | null
  formatStatus: PlateFormatStatus
  quality: PlateQuality
  cropReference: string | null
  observedAt: string
  sourceFrameRef: string | null
}

export interface VehicleSighting {
  sightingId: string
  vehicleId: string
  vehicleTrackId: string | null
  cameraId: string
  observedAt: string
  receivedAt: string
  vehicleClass: VehicleClass
  vehicleColor: VehicleColor
  vehicleDirection: VehicleDirection
  plateRead: PlateRead | null
  plateCandidates: PlateCandidate[]
  confidence: number | null
  detectionQuality: string | null
  cameraHealthState: string | null
  locationContext: string | null
  watchlistStatus: WatchlistStatus
  evidenceRef: string | null
  eventRef: string | null
  correlationRef: string | null
  incidentRef: string | null
  thumbnailUrl: string | null
  plateCropUrl: string | null
  sourceProvider: string | null
}

export interface VehicleHistory {
  vehicleId: string
  sightings: VehicleSighting[]
  firstSeen: string | null
  lastSeen: string | null
  totalSightings: number
}

export interface ANPRSummary {
  totalReads: number
  readablePlates: number
  partialReads: number
  unreadablePlates: number
  uniqueTrackedSightings: number
  camerasReporting: number
  lastUpdated: string | null
}

export interface ANPRFilter {
  search: string
  cameraId: string
  vehicleClass: VehicleClass | ''
  quality: PlateQuality | ''
  confidenceMin: number
  confidenceMax: number
  direction: VehicleDirection | ''
  watchlistStatus: WatchlistStatus | ''
  from: string
  to: string
  cursor: string | null
  limit: number
}

export const DEFAULT_ANPR_FILTER: ANPRFilter = {
  search: '',
  cameraId: '',
  vehicleClass: '',
  quality: '',
  confidenceMin: 0,
  confidenceMax: 1,
  direction: '',
  watchlistStatus: '',
  from: '',
  to: '',
  cursor: null,
  limit: 50,
}

export interface VehicleSearchResult {
  sighting: VehicleSighting
  matchType: 'EXACT_NORMALIZED_MATCH' | 'TOP_CANDIDATE_MATCH' | 'PARTIAL_MATCH' | 'RELATED_SIGHTING'
}
