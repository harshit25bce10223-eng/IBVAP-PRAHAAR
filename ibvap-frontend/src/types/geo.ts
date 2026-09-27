// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Domain Types — Geo
// ─────────────────────────────────────────────────────────────────────────────

export interface GeoPoint {
  lat: number
  lng: number
  altitude?: number
}

export interface GeoBounds {
  northEast: GeoPoint
  southWest: GeoPoint
}

export interface GeoZonePolygon {
  id: string
  name: string
  code: string
  type: 'zone' | 'sector' | 'district' | 'national'
  coordinates: GeoPoint[]  // closed polygon
  parentId?: string
  color?: string            // for map overlay
}
