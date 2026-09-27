// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — ANPR Mock Data
// 10 deterministic sightings covering every scenario in the spec.
// NO Math.random(). All IDs and timestamps are fixed strings.
// ─────────────────────────────────────────────────────────────────────────────
import type { VehicleSighting, ANPRSummary, VehicleHistory } from '@/types/anpr'

// ─── Helper ──────────────────────────────────────────────────────────────────
function plateRead(
  raw: string,
  norm: string | null,
  conf: number,
  quality: import('@/types/anpr').PlateQuality,
  fmt: import('@/types/anpr').PlateFormatStatus,
  ts: string
): import('@/types/anpr').PlateRead {
  return {
    rawRead: raw,
    normalizedRead: norm,
    displayRead: norm ?? raw,
    confidence: conf,
    characterConfidence: null,
    formatStatus: fmt,
    quality,
    cropReference: null,
    observedAt: ts,
    sourceFrameRef: null,
  }
}

function candidate(
  rank: number,
  raw: string,
  norm: string | null,
  conf: number,
  fmt: import('@/types/anpr').PlateFormatStatus
): import('@/types/anpr').PlateCandidate {
  return { rank, rawRead: raw, normalizedRead: norm, confidence: conf, characterConfidence: null, formatStatus: fmt }
}

// ─── Sightings ───────────────────────────────────────────────────────────────

// S1: Clear car plate HR26AK4521, high confidence (0.92), GOOD quality
export const S1: VehicleSighting = {
  sightingId: 'SGT-0001',
  vehicleId: 'VEH-A001',
  vehicleTrackId: 'TRK-1042',
  cameraId: 'CAM-07',
  observedAt: '2026-09-19T17:11:00Z',
  receivedAt: '2026-09-19T17:11:02Z',
  vehicleClass: 'PERSONAL_CAR',
  vehicleColor: 'WHITE',
  vehicleDirection: 'NORTH',
  plateRead: plateRead('HR26AK4521', 'HR26AK4521', 0.92, 'GOOD', 'VALID_FORMAT', '2026-09-19T17:11:00Z'),
  plateCandidates: [
    candidate(1, 'HR26AK4521', 'HR26AK4521', 0.92, 'VALID_FORMAT'),
    candidate(2, 'HR26AK452I', 'HR26AK452I', 0.61, 'POSSIBLE_FORMAT'),
  ],
  confidence: 0.92,
  detectionQuality: 'HIGH',
  cameraHealthState: 'HEALTHY',
  locationContext: 'Sector 7 North Gate',
  watchlistStatus: 'NO_MATCH',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// S2: Low-confidence OCR MP09CD7731, 0.48 confidence, FAIR quality, SUV
export const S2: VehicleSighting = {
  sightingId: 'SGT-0002',
  vehicleId: 'VEH-A002',
  vehicleTrackId: 'TRK-1043',
  cameraId: 'CAM-08',
  observedAt: '2026-09-19T17:14:30Z',
  receivedAt: '2026-09-19T17:14:32Z',
  vehicleClass: 'SUV',
  vehicleColor: 'GREY',
  vehicleDirection: 'SOUTH',
  plateRead: plateRead('MP09CD7731', 'MP09CD7731', 0.48, 'FAIR', 'POSSIBLE_FORMAT', '2026-09-19T17:14:30Z'),
  plateCandidates: [
    candidate(1, 'MP09CD7731', 'MP09CD7731', 0.48, 'POSSIBLE_FORMAT'),
    candidate(2, 'MP09C07731', null, 0.31, 'INVALID_FORMAT'),
  ],
  confidence: 0.48,
  detectionQuality: 'LOW',
  cameraHealthState: 'HEALTHY',
  locationContext: 'Sector 8 Checkpoint',
  watchlistStatus: 'NOT_CHECKED',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// S3: Two candidates RJ14AB1052 (0.91) and RJ14AB1062 (0.66), FAIR quality
export const S3: VehicleSighting = {
  sightingId: 'SGT-0003',
  vehicleId: 'VEH-A003',
  vehicleTrackId: 'TRK-1044',
  cameraId: 'CAM-09',
  observedAt: '2026-09-19T17:19:00Z',
  receivedAt: '2026-09-19T17:19:01Z',
  vehicleClass: 'PERSONAL_CAR',
  vehicleColor: 'SILVER',
  vehicleDirection: 'EAST',
  plateRead: plateRead('RJ14AB1O52', 'RJ14AB1052', 0.91, 'FAIR', 'POSSIBLE_FORMAT', '2026-09-19T17:19:00Z'),
  plateCandidates: [
    candidate(1, 'RJ14AB1O52', 'RJ14AB1052', 0.91, 'POSSIBLE_FORMAT'),
    candidate(2, 'RJ14AB1062', 'RJ14AB1062', 0.66, 'POSSIBLE_FORMAT'),
    candidate(3, 'RJ14AB105Z', null, 0.43, 'INVALID_FORMAT'),
  ],
  confidence: 0.91,
  detectionQuality: 'MEDIUM',
  cameraHealthState: 'HEALTHY',
  locationContext: 'East Perimeter Road',
  watchlistStatus: 'NO_MATCH',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// S4: UNREADABLE plate, null plateRead, motorcycle, night scene
export const S4: VehicleSighting = {
  sightingId: 'SGT-0004',
  vehicleId: 'VEH-A004',
  vehicleTrackId: 'TRK-1045',
  cameraId: 'CAM-07',
  observedAt: '2026-09-19T22:41:08Z',
  receivedAt: '2026-09-19T22:41:10Z',
  vehicleClass: 'MOTORCYCLE',
  vehicleColor: 'BLACK',
  vehicleDirection: 'NORTH',
  plateRead: null,
  plateCandidates: [],
  confidence: 0.12,
  detectionQuality: 'VERY_LOW',
  cameraHealthState: 'HEALTHY',
  locationContext: 'Sector 7 North Gate',
  watchlistStatus: 'NOT_CHECKED',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// S5: Truck, MOTION_BLUR quality, confidence 0.61
export const S5: VehicleSighting = {
  sightingId: 'SGT-0005',
  vehicleId: 'VEH-A005',
  vehicleTrackId: 'TRK-1046',
  cameraId: 'CAM-11',
  observedAt: '2026-09-19T17:31:00Z',
  receivedAt: '2026-09-19T17:31:02Z',
  vehicleClass: 'TRUCK',
  vehicleColor: 'RED',
  vehicleDirection: 'INBOUND',
  plateRead: plateRead('DL1LT7821', 'DL1LT7821', 0.61, 'MOTION_BLUR', 'VALID_FORMAT', '2026-09-19T17:31:00Z'),
  plateCandidates: [
    candidate(1, 'DL1LT7821', 'DL1LT7821', 0.61, 'VALID_FORMAT'),
    candidate(2, 'DL1LT782I', null, 0.39, 'INVALID_FORMAT'),
  ],
  confidence: 0.61,
  detectionQuality: 'LOW',
  cameraHealthState: 'HEALTHY',
  locationContext: 'Main Inbound Lane',
  watchlistStatus: 'NO_MATCH',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// S6: Night scene, degraded camera health, SUV, LOW_LIGHT quality
export const S6: VehicleSighting = {
  sightingId: 'SGT-0006',
  vehicleId: 'VEH-A006',
  vehicleTrackId: 'TRK-1047',
  cameraId: 'CAM-12',
  observedAt: '2026-09-19T23:05:00Z',
  receivedAt: '2026-09-19T23:05:04Z',
  vehicleClass: 'SUV',
  vehicleColor: 'BLACK',
  vehicleDirection: 'OUTBOUND',
  plateRead: plateRead('UP32GH0034', 'UP32GH0034', 0.53, 'LOW_LIGHT', 'VALID_FORMAT', '2026-09-19T23:05:00Z'),
  plateCandidates: [
    candidate(1, 'UP32GH0034', 'UP32GH0034', 0.53, 'VALID_FORMAT'),
  ],
  confidence: 0.53,
  detectionQuality: 'LOW',
  cameraHealthState: 'DEGRADED',
  locationContext: 'South Perimeter Night Zone',
  watchlistStatus: 'NOT_CHECKED',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// S7: DEGRADED camera, partial plate DL8C__123, PARTIAL quality
export const S7: VehicleSighting = {
  sightingId: 'SGT-0007',
  vehicleId: 'VEH-A007',
  vehicleTrackId: 'TRK-1048',
  cameraId: 'CAM-13',
  observedAt: '2026-09-19T17:55:00Z',
  receivedAt: '2026-09-19T17:55:03Z',
  vehicleClass: 'VAN',
  vehicleColor: 'BLUE',
  vehicleDirection: 'WEST',
  plateRead: plateRead('DL8C__123', null, 0.34, 'PARTIAL', 'NOT_ENOUGH_DATA', '2026-09-19T17:55:00Z'),
  plateCandidates: [
    candidate(1, 'DL8C__123', null, 0.34, 'NOT_ENOUGH_DATA'),
  ],
  confidence: 0.34,
  detectionQuality: 'POOR',
  cameraHealthState: 'DEGRADED',
  locationContext: 'West Flank CAM-13 Partial View',
  watchlistStatus: 'NOT_CHECKED',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// S8a,b,c: Multi-camera history (same vehicleId VEH-A001 / HR26AK4521 on 3 cameras)
export const S8a: VehicleSighting = {
  sightingId: 'SGT-0008A',
  vehicleId: 'VEH-A001',
  vehicleTrackId: 'TRK-1042',
  cameraId: 'CAM-07',
  observedAt: '2026-09-19T17:11:00Z',
  receivedAt: '2026-09-19T17:11:02Z',
  vehicleClass: 'PERSONAL_CAR',
  vehicleColor: 'WHITE',
  vehicleDirection: 'NORTH',
  plateRead: plateRead('HR26AK4521', 'HR26AK4521', 0.92, 'GOOD', 'VALID_FORMAT', '2026-09-19T17:11:00Z'),
  plateCandidates: [candidate(1, 'HR26AK4521', 'HR26AK4521', 0.92, 'VALID_FORMAT')],
  confidence: 0.92,
  detectionQuality: 'HIGH',
  cameraHealthState: 'HEALTHY',
  locationContext: 'Sector 7 North Gate',
  watchlistStatus: 'NO_MATCH',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

export const S8b: VehicleSighting = {
  sightingId: 'SGT-0008B',
  vehicleId: 'VEH-A001',
  vehicleTrackId: 'TRK-1061',
  cameraId: 'CAM-08',
  observedAt: '2026-09-19T17:23:00Z',
  receivedAt: '2026-09-19T17:23:02Z',
  vehicleClass: 'PERSONAL_CAR',
  vehicleColor: 'WHITE',
  vehicleDirection: 'NORTH',
  plateRead: plateRead('HR26AK4521', 'HR26AK4521', 0.89, 'GOOD', 'VALID_FORMAT', '2026-09-19T17:23:00Z'),
  plateCandidates: [candidate(1, 'HR26AK4521', 'HR26AK4521', 0.89, 'VALID_FORMAT')],
  confidence: 0.89,
  detectionQuality: 'HIGH',
  cameraHealthState: 'HEALTHY',
  locationContext: 'Sector 8 Checkpoint',
  watchlistStatus: 'NO_MATCH',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

export const S8c: VehicleSighting = {
  sightingId: 'SGT-0008C',
  vehicleId: 'VEH-A001',
  vehicleTrackId: 'TRK-1079',
  cameraId: 'CAM-11',
  observedAt: '2026-09-19T17:34:00Z',
  receivedAt: '2026-09-19T17:34:02Z',
  vehicleClass: 'PERSONAL_CAR',
  vehicleColor: 'WHITE',
  vehicleDirection: 'NORTH',
  plateRead: plateRead('HR26AK4521', 'HR26AK4521', 0.91, 'GOOD', 'VALID_FORMAT', '2026-09-19T17:34:00Z'),
  plateCandidates: [candidate(1, 'HR26AK4521', 'HR26AK4521', 0.91, 'VALID_FORMAT')],
  confidence: 0.91,
  detectionQuality: 'HIGH',
  cameraHealthState: 'HEALTHY',
  locationContext: 'North Corridor CAM-11',
  watchlistStatus: 'NO_MATCH',
  evidenceRef: null,
  eventRef: null,
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// S9: Incident-linked sighting, incidentRef: 'INC-024'
export const S9: VehicleSighting = {
  sightingId: 'SGT-0009',
  vehicleId: 'VEH-A009',
  vehicleTrackId: 'TRK-1050',
  cameraId: 'CAM-07',
  observedAt: '2026-09-19T16:55:00Z',
  receivedAt: '2026-09-19T16:55:01Z',
  vehicleClass: 'SUV',
  vehicleColor: 'BLACK',
  vehicleDirection: 'INBOUND',
  plateRead: plateRead('GJ01BV2209', 'GJ01BV2209', 0.87, 'GOOD', 'VALID_FORMAT', '2026-09-19T16:55:00Z'),
  plateCandidates: [
    candidate(1, 'GJ01BV2209', 'GJ01BV2209', 0.87, 'VALID_FORMAT'),
  ],
  confidence: 0.87,
  detectionQuality: 'HIGH',
  cameraHealthState: 'HEALTHY',
  locationContext: 'Sector 7 North Gate',
  watchlistStatus: 'WATCHLIST_MATCH',
  evidenceRef: null,
  eventRef: 'EVT-0188',
  correlationRef: 'COR-0019',
  incidentRef: 'INC-024',
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// S10: Evidence-linked sighting, evidenceRef: 'EVD-0091'
export const S10: VehicleSighting = {
  sightingId: 'SGT-0010',
  vehicleId: 'VEH-A010',
  vehicleTrackId: 'TRK-1051',
  cameraId: 'CAM-09',
  observedAt: '2026-09-19T15:30:00Z',
  receivedAt: '2026-09-19T15:30:01Z',
  vehicleClass: 'BUS',
  vehicleColor: 'YELLOW',
  vehicleDirection: 'OUTBOUND',
  plateRead: plateRead('MH43AA8801', 'MH43AA8801', 0.78, 'GOOD', 'VALID_FORMAT', '2026-09-19T15:30:00Z'),
  plateCandidates: [
    candidate(1, 'MH43AA8801', 'MH43AA8801', 0.78, 'VALID_FORMAT'),
    candidate(2, 'MH43AA8B01', null, 0.52, 'INVALID_FORMAT'),
  ],
  confidence: 0.78,
  detectionQuality: 'HIGH',
  cameraHealthState: 'HEALTHY',
  locationContext: 'East Perimeter Road',
  watchlistStatus: 'NO_MATCH',
  evidenceRef: 'EVD-0091',
  eventRef: 'EVT-0144',
  correlationRef: null,
  incidentRef: null,
  thumbnailUrl: null,
  plateCropUrl: null,
  sourceProvider: 'ANPR-ENGINE-v2',
}

// ─── Exports ──────────────────────────────────────────────────────────────────

export const ALL_MOCK_SIGHTINGS: VehicleSighting[] = [
  S1, S2, S3, S4, S5, S6, S7, S8a, S8b, S8c, S9, S10,
]

export const MOCK_SUMMARY: ANPRSummary = {
  totalReads: 12,
  readablePlates: 9,
  partialReads: 1,
  unreadablePlates: 1,
  uniqueTrackedSightings: 10,
  camerasReporting: 6,
  lastUpdated: '2026-09-19T23:05:04Z',
}

export const MOCK_VEHICLE_HISTORY_VEH_A001: VehicleHistory = {
  vehicleId: 'VEH-A001',
  sightings: [S8a, S8b, S8c],
  firstSeen: '2026-09-19T17:11:00Z',
  lastSeen: '2026-09-19T17:34:00Z',
  totalSightings: 3,
}
