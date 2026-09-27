// ─────────────────────────────────────────────────────────────────────────────
// GisService — Interface Contract
//
// The ONLY thing the GIS / Digital Twin UI depends on for its operational map.
// Swap implementations (MockGisService → RealGisService) without touching any
// GIS component.
//
// Future API equivalents:
//   GET /gis/context          (sector, terrain, border reference)
//   GET /gis/cameras
//   GET /gis/tracks
//   GET /gis/incidents
//   GET /gis/zones
//   GET /gis/risk-heat        (?window=live|24h|7d)
//   GET /gis/historical       (?window=live|24h|7d)
// ─────────────────────────────────────────────────────────────────────────────

import type { GisData } from '@/types'

export interface IGisService {
  /** Full operational map dataset for the current sector. */
  getGisData(window?: 'LIVE' | '24H' | '7D'): Promise<GisData>
}