// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Domain Types — Surveillance Entities
// ─────────────────────────────────────────────────────────────────────────────

import type { GeoPoint } from './geo'

export type CameraStatus = 'online' | 'offline' | 'degraded' | 'maintenance' | 'alert'

export interface StreamConfig {
  rtspUrl?: string       // filled by backend — never exposed to browser directly
  hlsUrl?: string        // proxy URL safe for browser
  resolution: string     // e.g. "1920x1080"
  fps: number
  bitrateMbps: number
}

export interface Camera {
  id: string
  label: string
  serialNumber: string
  status: CameraStatus
  zoneId: string
  location: GeoPoint
  stream?: StreamConfig
  lastHeartbeat: string  // ISO-8601
  aiEnabled: boolean
  firmwareVersion: string
}

// ─── Incidents ────────────────────────────────────────────────────────────────

export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low'
export type IncidentStatus   = 'open' | 'acknowledged' | 'investigating' | 'resolved' | 'false_positive'

export interface Incident {
  id: string
  cameraId: string
  severity: IncidentSeverity
  status: IncidentStatus
  title: string
  description: string
  detectedAt: string   // ISO-8601
  resolvedAt?: string
  assignedTo?: string  // userId
  zoneId: string
  evidenceIds: string[]
  blockchainTxHash?: string
  tags: string[]
}

// ─── AI Detections ────────────────────────────────────────────────────────────

export type DetectionCategory =
  | 'intrusion'
  | 'loitering'
  | 'crowd_surge'
  | 'abandoned_object'
  | 'vehicle_violation'
  | 'face_match'
  | 'weapon_detected'
  | 'perimeter_breach'

export interface BoundingBox {
  x: number; y: number
  width: number; height: number
}

export interface Detection {
  id: string
  incidentId?: string
  cameraId: string
  category: DetectionCategory
  confidence: number       // 0.0 – 1.0
  boundingBox?: BoundingBox
  detectedAt: string
  frameUrl?: string        // signed URL to frame image
  modelVersion: string
}

// ─── Evidence ─────────────────────────────────────────────────────────────────
// NOTE (Component 3): the legacy Evidence/EvidenceChain placeholders lived
// here but were never referenced anywhere. They are removed in favor of the
// canonical backend-aligned model in `types/evidence.ts` (EvidenceRecord,
// IntegrityState, AnchorState, …), which is the single evidence type source.

// ─── Audit ────────────────────────────────────────────────────────────────────

export type AuditAction =
  | 'login' | 'logout' | 'login_failed' | 'session_expired'
  | 'view_camera' | 'view_incident' | 'acknowledge_incident'
  | 'export_evidence' | 'delete_evidence'
  | 'create_user' | 'update_user' | 'delete_user'
  | 'modify_zone' | 'modify_config'

export interface AuditEvent {
  id: string
  userId: string
  action: AuditAction
  resourceType?: string
  resourceId?: string
  ipAddress: string
  userAgent?: string
  timestamp: string
  metadata?: Record<string, unknown>
  blockchainTxHash?: string
}
