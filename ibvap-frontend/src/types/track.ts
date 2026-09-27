// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — Track domain types + simulated observation contract
// ─────────────────────────────────────────────────────────────────────────────

/** Normalized (image-space, [0,1]) bounding box: top-left origin. */
export interface NormalizedBBox {
  x: number
  y: number
  width: number
  height: number
}

export type ObjectType = 'HUMAN' | 'VEHICLE' | 'ANIMAL'

export type Reliability = 'HIGH' | 'MEDIUM' | 'LOW'

/** One observation of a track, POSTed to the backend for evaluation. */
export interface TrackObservation {
  track_id: string
  camera_id: string
  object_type: ObjectType
  bbox: NormalizedBBox
  confidence: number
  is_night: boolean
  multi_camera_confirmed: boolean
  reliability: Reliability
  timestamp?: string
}

/** A live track being visualized / simulated on the camera feed. */
export interface TrackVisual {
  track_id: string
  object_type: ObjectType
  bbox: NormalizedBBox
  confidence: number
  /** representative ground-contact point (bottom-center) used by the engine */
  representativePoint: ZonePointLike
  path: ZonePointLike[]
  lastSeen: number
  insideZones: string[]
}

export interface ZonePointLike {
  x: number
  y: number
}