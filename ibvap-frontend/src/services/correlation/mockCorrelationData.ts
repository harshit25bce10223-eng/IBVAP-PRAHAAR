// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — mock correlation fixtures (DEMO ONLY)
//
// Isolated, hand-written fixtures that exercise every correlation surface.
// All values are authoritative demo outputs — this module never computes
// correlation, risk, severity or identity. Only demo/test infrastructure
// should import this file; components consume the service interface.
//
// Demo timestamps use a fixed fictional date (2026-09-07) so behaviour is
// deterministic; they are clearly mock, never presented as live events.
// ─────────────────────────────────────────────────────────────────────────────

import type {
  CameraReliabilityContext,
  CorrelationEventMember,
  CorrelationExplanation,
  CorrelationGroup,
  CorrelationModality,
  CorrelationSource,
  EventLogQuery,
} from '@/types/eventCorrelation'
import type { Severity } from '@/types/risk'

const D = '2026-09-07'

interface MemberInput {
  id: string
  kind: CorrelationEventMember['kind']
  source: CorrelationSource
  modality: CorrelationModality
  cameraId: string
  at: string
  severity: Severity
  zoneId?: string | null
  sectorId?: string | null
  regionProfile?: string | null
  trackId?: string | null
  reliability?: CorrelationEventMember['reliability']
  confidence?: number | null
  evidenceIds?: string[]
  healthContext?: CameraReliabilityContext | null
}

function member(ii: MemberInput): CorrelationEventMember {
  return {
    eventId: ii.id,
    kind: ii.kind,
    source: ii.source,
    modality: ii.modality,
    cameraId: ii.cameraId,
    zoneId: ii.zoneId ?? null,
    sectorId: ii.sectorId ?? 'SECTOR-B',
    regionProfile: ii.regionProfile ?? 'INDO-NEPAL / FOOTHILL',
    trackId: ii.trackId ?? null,
    timestamp: ii.at,
    severity: ii.severity,
    reliability: ii.reliability ?? null,
    confidence: ii.confidence ?? null,
    evidenceIds: ii.evidenceIds ?? [],
    healthContext: ii.healthContext ?? null,
  }
}

function expl(facet: CorrelationExplanation['facet'], label: string, detail: string): CorrelationExplanation {
  return { facet, label, detail }
}

const CAM07HILL: CameraReliabilityContext = {
  cameraId: 'CAM-07',
  reliability: 'HIGH',
  note: null,
}

const CAM12DEGRADED: CameraReliabilityContext = {
  cameraId: 'CAM-12',
  reliability: 'LOW',
  note: 'Camera image quality degraded; associated video observations carry reduced reliability.',
}

// ── Scenario 1 — SIMPLE CORRELATION (single camera) ─────────────────────────
const EV_10421 = member({
  id: 'EV-10421', kind: 'DETECTION', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-07', at: `${D}T02:14:11Z`, severity: 'HIGH', trackId: 'TRK-1042',
  reliability: 'HIGH', confidence: 0.91, evidenceIds: ['EVD-10481'],
})
const EV_10422 = member({
  id: 'EV-10422', kind: 'ZONE_ENTRY', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-07', at: `${D}T02:14:17Z`, severity: 'HIGH', zoneId: 'ZONE-B',
  trackId: 'TRK-1042', reliability: 'HIGH', evidenceIds: ['EVD-10482'],
})
const EV_10423 = member({
  id: 'EV-10423', kind: 'TRACK', source: 'TRACKING', modality: 'VIDEO',
  cameraId: 'CAM-07', at: `${D}T02:14:29Z`, severity: 'MEDIUM', trackId: 'TRK-1042',
  reliability: 'HIGH', confidence: 0.87,
})

// ── Scenario 2 — CROSS-CAMERA CORRELATION (possible same entity) ────────────
const EV_10431 = member({
  id: 'EV-10431', kind: 'DETECTION', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-07', at: `${D}T02:16:01Z`, severity: 'MEDIUM', trackId: 'TRK-1043',
  reliability: 'HIGH', confidence: 0.84, evidenceIds: ['EVD-10483'],
})
const EV_10432 = member({
  id: 'EV-10432', kind: 'REID_CANDIDATE', source: 'RE_ID', modality: 'VIDEO',
  cameraId: 'CAM-08', at: `${D}T02:16:12Z`, severity: 'MEDIUM', trackId: 'TRK-1043',
  reliability: 'MEDIUM', confidence: 0.72,
})
const EV_10433 = member({
  id: 'EV-10433', kind: 'ZONE_ENTRY', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-08', at: `${D}T02:16:21Z`, severity: 'MEDIUM', zoneId: 'ZONE-C',
  trackId: 'TRK-1043', reliability: 'MEDIUM', evidenceIds: ['EVD-10484'],
})

// ── Scenario 3 — MULTI-MODAL CORRELATION (VIDEO + ANPR + AUDIO) ─────────────
const EV_10441 = member({
  id: 'EV-10441', kind: 'DETECTION', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-12', at: `${D}T02:20:05Z`, severity: 'MEDIUM', trackId: 'TRK-1044',
  reliability: 'MEDIUM', confidence: 0.78, evidenceIds: ['EVD-10485'],
})
const EV_10442 = member({
  id: 'EV-10442', kind: 'ANPR_READ', source: 'ANPR', modality: 'ANPR',
  cameraId: 'CAM-12', at: `${D}T02:20:18Z`, severity: 'MEDIUM', trackId: 'TRK-1044',
  reliability: 'LOW', confidence: 0.66, evidenceIds: ['EVD-10486'],
})
const EV_10443 = member({
  id: 'EV-10443', kind: 'AUDIO_ANOMALY', source: 'AUDIO', modality: 'AUDIO',
  cameraId: 'CAM-12', at: `${D}T02:20:31Z`, severity: 'MEDIUM', trackId: 'TRK-1044',
  reliability: 'LOW', evidenceIds: ['EVD-10487'],
})
const EV_10444 = member({
  id: 'EV-10444', kind: 'ZONE_ENTRY', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-12', at: `${D}T02:20:44Z`, severity: 'MEDIUM', zoneId: 'ZONE-F',
  trackId: 'TRK-1044', reliability: 'MEDIUM',
})

// ── Scenario 4 — STANDALONE (no forced correlation) ──────────────────────────
const EV_10451 = member({
  id: 'EV-10451', kind: 'ANPR_READ', source: 'ANPR', modality: 'ANPR',
  cameraId: 'CAM-12', at: `${D}T02:17:43Z`, severity: 'LOW',
  reliability: 'MEDIUM', confidence: 0.81, evidenceIds: ['EVD-10488'],
})

// ── Scenario 5 — UNCERTAIN (temporal strong, spatial weak) ───────────────────
const EV_10461 = member({
  id: 'EV-10461', kind: 'DETECTION', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-03', at: `${D}T02:23:02Z`, severity: 'MEDIUM', trackId: 'TRK-1045',
  reliability: 'MEDIUM', confidence: 0.6,
})
const EV_10462 = member({
  id: 'EV-10462', kind: 'AUDIO_ANOMALY', source: 'AUDIO', modality: 'AUDIO',
  cameraId: 'CAM-08', at: `${D}T02:23:09Z`, severity: 'MEDIUM', trackId: null,
  reliability: 'LOW',
})
const EV_10463 = member({
  id: 'EV-10463', kind: 'ANPR_READ', source: 'ANPR', modality: 'ANPR',
  cameraId: 'CAM-12', at: `${D}T02:23:16Z`, severity: 'MEDIUM', trackId: null,
  reliability: 'LOW', confidence: 0.55,
})

// ── Scenario 6 — CORRELATION REVISED / DISSOLVED ────────────────────────────
const EV_10471 = member({
  id: 'EV-10471', kind: 'ZONE_ENTRY', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-07', at: `${D}T02:19:04Z`, severity: 'MEDIUM', zoneId: 'ZONE-B',
  trackId: 'TRK-1046', reliability: 'MEDIUM',
})
const EV_10472 = member({
  id: 'EV-10472', kind: 'ANPR_READ', source: 'ANPR', modality: 'ANPR',
  cameraId: 'CAM-08', at: `${D}T02:19:11Z`, severity: 'LOW', trackId: null,
  reliability: 'LOW', confidence: 0.5,
})

// ── Scenario 7 — LOW-SEVERITY CORRELATED (correlation ≠ severity, §69) ──────
const EV_10481 = member({
  id: 'EV-10481', kind: 'ZONE_EXIT', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-12', at: `${D}T03:02:44Z`, severity: 'LOW', trackId: 'TRK-1047',
  reliability: 'HIGH', confidence: 0.88,
})
const EV_10482 = member({
  id: 'EV-10482', kind: 'TRACK', source: 'TRACKING', modality: 'VIDEO',
  cameraId: 'CAM-12', at: `${D}T03:02:51Z`, severity: 'LOW', trackId: 'TRK-1047',
  reliability: 'HIGH', confidence: 0.85,
})

// ── Scenario 8 — CAMERA CHAIN + HEALTH CONTEXT (CAM-12 degraded) ────────────
const EV_10491 = member({
  id: 'EV-10491', kind: 'DETECTION', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-12', at: `${D}T02:31:10Z`, severity: 'MEDIUM', trackId: 'TRK-1048',
  reliability: 'LOW', confidence: 0.62, healthContext: CAM12DEGRADED,
  evidenceIds: ['EVD-10489'],
})
const EV_10492 = member({
  id: 'EV-10492', kind: 'ZONE_ENTRY', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-12', at: `${D}T02:31:18Z`, severity: 'MEDIUM', zoneId: 'ZONE-F',
  trackId: 'TRK-1048', reliability: 'LOW', healthContext: CAM12DEGRADED,
  evidenceIds: ['EVD-10490'],
})
const EV_10493 = member({
  id: 'EV-10493', kind: 'REID_CANDIDATE', source: 'RE_ID', modality: 'VIDEO',
  cameraId: 'CAM-07', at: `${D}T02:31:26Z`, severity: 'MEDIUM', trackId: 'TRK-1048',
  reliability: 'MEDIUM', confidence: 0.7,
})
const EV_10494 = member({
  id: 'EV-10494', kind: 'ZONE_ENTRY', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-07', at: `${D}T02:31:33Z`, severity: 'MEDIUM', zoneId: 'ZONE-B',
  trackId: 'TRK-1048', reliability: 'HIGH',
})

// ── Scenario 9 — LARGE GROUP (20 signals, summary + expand, §134) ───────────
const LARGE_MEMBERS: CorrelationEventMember[] = Array.from({ length: 20 }, (_, i) =>
  member({
    id: `EV-1100${String(i + 1).padStart(2, '0')}`,
    kind: i % 4 === 0 ? 'DETECTION' : i % 4 === 1 ? 'ZONE_ENTRY' : i % 4 === 2 ? 'ANPR_READ' : 'AUDIO_ANOMALY',
    source: i % 4 === 2 ? 'ANPR' : i % 4 === 3 ? 'AUDIO' : 'VIRTUAL_FENCE',
    modality: i % 4 === 2 ? 'ANPR' : i % 4 === 3 ? 'AUDIO' : 'VIDEO',
    cameraId: i % 2 === 0 ? 'CAM-19' : 'CAM-03',
    at: `${D}T02:${String(40 + Math.floor(i / 4)).padStart(2, '0')}:${String(10 + (i % 4) * 3).padStart(2, '0')}Z`,
    severity: 'MEDIUM',
    trackId: 'TRK-1050',
    reliability: 'MEDIUM',
  })
)

// ── Scenario 10 — RELATED, GROUPING IN PROGRESS (never forced) ───────────────
const EV_10511 = member({
  id: 'EV-110021', kind: 'DETECTION', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-07', at: `${D}T03:09:18Z`, severity: 'LOW', trackId: 'TRK-1051',
  reliability: 'HIGH', confidence: 0.8,
})
const EV_10512 = member({
  id: 'EV-110022', kind: 'ZONE_ENTRY', source: 'VIRTUAL_FENCE', modality: 'VIDEO',
  cameraId: 'CAM-07', at: `${D}T03:09:35Z`, severity: 'LOW', zoneId: 'ZONE-B',
  trackId: 'TRK-1051', reliability: 'HIGH',
})

export const MOCK_GROUPS: CorrelationGroup[] = [
  {
    correlationId: 'COR-1042',
    incidentId: 'INC-1042',
    incidentState: 'NEW',
    status: 'CORRELATED',
    state: 'STABLE',
    startedAt: `${D}T02:14:11Z`,
    endedAt: `${D}T02:14:43Z`,
    eventCount: 3,
    cameraCount: 1,
    memberEventsLoaded: null,
    memberEvents: [EV_10421, EV_10422, EV_10423],
    primaryEventId: 'EV-10422',
    relationships: [
      { fromEventId: 'EV-10421', toEventId: 'EV-10422', type: 'TEMPORAL', strength: null, explanation: '6-second separation within configured window' },
      { fromEventId: 'EV-10421', toEventId: 'EV-10423', type: 'SEQUENCE', strength: null, explanation: 'Track continuation after detection' },
      { fromEventId: 'EV-10422', toEventId: 'EV-10423', type: 'ENTITY', strength: null, explanation: 'Possible same track candidate' },
    ],
    explanation: [
      expl('TEMPORAL', '32 sec', 'Within configured 60-second correlation window'),
      expl('SPATIAL', 'same sector', 'All signals in SECTOR-B'),
      expl('ZONE', 'same zone', 'Zone entry into ZONE-B'),
      expl('ENTITY', 'possible continuation', 'Track continuity across signals'),
    ],
    confidence: { value: 87, note: 'Based on temporal, spatial and entity relationship signals.' },
    temporalWindowSec: 60,
    risk: { score: 82, severity: 'HIGH' },
    uncertainty: { reliability: 'HIGH', note: null },
    trackCandidate: { trackId: 'TRK-1042', confidence: 0.87, label: 'possible same entity' },
    cameraChain: ['CAM-07'],
    modalities: ['VIDEO'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-NEPAL / FOOTHILL',
    sources: ['VIRTUAL_FENCE', 'TRACKING'],
    healthContext: [CAM07HILL],
    evidenceCount: 3,
    connectivity: 'LIVE',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T02:14:45Z`,
      updatedAt: `${D}T02:14:45Z`,
      transitions: [
        { status: 'RELATED', at: `${D}T02:14:32Z`, note: null },
        { status: 'CORRELATED', at: `${D}T02:14:45Z`, note: 'Grouping sustained with converging signals.' },
      ],
    },
    updatedAt: `${D}T02:14:45Z`,
  },
  {
    correlationId: 'COR-1043',
    incidentId: 'INC-1043',
    incidentState: 'NEW',
    status: 'CORRELATED',
    state: 'ACTIVE',
    startedAt: `${D}T02:16:01Z`,
    endedAt: `${D}T02:16:21Z`,
    eventCount: 3,
    cameraCount: 2,
    memberEventsLoaded: null,
    memberEvents: [EV_10431, EV_10432, EV_10433],
    primaryEventId: 'EV-10431',
    relationships: [
      { fromEventId: 'EV-10431', toEventId: 'EV-10432', type: 'CAMERA', strength: null, explanation: 'Cross-camera observation CAM-07 → CAM-08' },
      { fromEventId: 'EV-10432', toEventId: 'EV-10433', type: 'ENTITY', strength: null, explanation: 'Possible same entity candidate' },
      { fromEventId: 'EV-10431', toEventId: 'EV-10433', type: 'SPATIAL', strength: null, explanation: 'Nearby cameras, same sector' },
    ],
    explanation: [
      expl('TEMPORAL', '20 sec', 'Within configured correlation window'),
      expl('SPATIAL', 'nearby cameras', 'CAM-07 and CAM-08 geographically linked'),
      expl('ENTITY', 'possible continuation', 'Re-ID candidate across cameras'),
      expl('CAMERA', 'cross-camera', 'Observation continued on adjacent camera'),
    ],
    confidence: { value: 78, note: 'Based on temporal and cross-camera entity relationship signals.' },
    temporalWindowSec: 60,
    risk: { score: 64, severity: 'MEDIUM' },
    uncertainty: { reliability: 'MEDIUM', note: 'Cross-camera entity continuity is a candidate relation; identity is not confirmed.' },
    trackCandidate: { trackId: 'TRK-1043', confidence: 0.72, label: 'possible same entity' },
    cameraChain: ['CAM-07', 'CAM-08'],
    modalities: ['VIDEO'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-NEPAL / FOOTHILL',
    sources: ['VIRTUAL_FENCE', 'RE_ID'],
    healthContext: [CAM07HILL],
    evidenceCount: 2,
    connectivity: 'LIVE',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T02:16:25Z`,
      updatedAt: `${D}T02:16:25Z`,
      transitions: [
        { status: 'RELATED', at: `${D}T02:16:20Z`, note: null },
        { status: 'CORRELATED', at: `${D}T02:16:25Z`, note: null },
      ],
    },
    updatedAt: `${D}T02:16:25Z`,
  },
  {
    correlationId: 'COR-1044',
    incidentId: 'INC-1044',
    incidentState: 'REVIEWED',
    status: 'CORRELATED',
    state: 'STABLE',
    startedAt: `${D}T02:20:05Z`,
    endedAt: `${D}T02:20:44Z`,
    eventCount: 4,
    cameraCount: 1,
    memberEventsLoaded: null,
    memberEvents: [EV_10441, EV_10442, EV_10443, EV_10444],
    primaryEventId: 'EV-10444',
    relationships: [
      { fromEventId: 'EV-10441', toEventId: 'EV-10442', type: 'SUPPORTING', strength: null, explanation: 'ANPR read supports video detection' },
      { fromEventId: 'EV-10441', toEventId: 'EV-10443', type: 'SUPPORTING', strength: null, explanation: 'Audio anomaly supports detection contextually' },
      { fromEventId: 'EV-10442', toEventId: 'EV-10444', type: 'SEQUENCE', strength: null, explanation: 'Zone entry after ANPR observation' },
    ],
    explanation: [
      expl('TEMPORAL', '39 sec', 'Within configured correlation window'),
      expl('SPATIAL', 'same camera', 'All signals from CAM-12'),
      expl('CAMERA', 'same zone', 'Zone-F'),
      expl('CONTEXTUAL', 'multimodal', 'VIDEO + ANPR + AUDIO help establish context'),
    ],
    confidence: { value: 81, note: 'Multimodal enrichment supports grouping.' },
    temporalWindowSec: 60,
    risk: { score: 55, severity: 'MEDIUM' },
    uncertainty: { reliability: 'MEDIUM', note: 'ANPR and audio reliability are low; plate is a candidate, not verified.' },
    trackCandidate: { trackId: 'TRK-1044', confidence: 0.78, label: 'possible same entity' },
    cameraChain: ['CAM-12'],
    modalities: ['VIDEO', 'ANPR', 'AUDIO'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-BHUTAN / HILLY-FOREST',
    sources: ['VIRTUAL_FENCE', 'ANPR', 'AUDIO'],
    healthContext: [CAM12DEGRADED],
    evidenceCount: 3,
    connectivity: 'DELAYED',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T02:20:48Z`,
      updatedAt: `${D}T02:20:48Z`,
      transitions: [
        { status: 'RELATED', at: `${D}T02:20:38Z`, note: null },
        { status: 'CORRELATED', at: `${D}T02:20:48Z`, note: null },
      ],
    },
    updatedAt: `${D}T02:20:48Z`,
  },
  {
    correlationId: 'COR-1045',
    incidentId: null,
    incidentState: null,
    status: 'STANDALONE',
    state: 'OPEN',
    startedAt: `${D}T02:17:43Z`,
    endedAt: null,
    eventCount: 1,
    cameraCount: 1,
    memberEventsLoaded: null,
    memberEvents: [EV_10451],
    primaryEventId: 'EV-10451',
    relationships: [],
    explanation: [
      expl('CONTEXTUAL', 'no support', 'No sufficient relationship evidence to group this signal'),
    ],
    confidence: null,
    temporalWindowSec: null,
    risk: { score: 18, severity: 'LOW' },
    uncertainty: { reliability: 'MEDIUM', note: null },
    trackCandidate: null,
    cameraChain: null,
    modalities: ['ANPR'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-BHUTAN / HILLY-FOREST',
    sources: ['ANPR'],
    healthContext: [CAM12DEGRADED],
    evidenceCount: 1,
    connectivity: 'LIVE',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T02:17:45Z`,
      updatedAt: `${D}T02:17:45Z`,
      transitions: [{ status: 'STANDALONE', at: `${D}T02:17:45Z`, note: null }],
    },
    updatedAt: `${D}T02:17:45Z`,
  },
  {
    correlationId: 'COR-1046',
    incidentId: null,
    incidentState: null,
    status: 'UNCERTAIN',
    state: 'OPEN',
    startedAt: `${D}T02:23:02Z`,
    endedAt: `${D}T02:23:16Z`,
    eventCount: 3,
    cameraCount: 3,
    memberEventsLoaded: null,
    memberEvents: [EV_10461, EV_10462, EV_10463],
    primaryEventId: 'EV-10461',
    relationships: [
      { fromEventId: 'EV-10461', toEventId: 'EV-10462', type: 'TEMPORAL', strength: null, explanation: 'Close in time (7s)' },
      { fromEventId: 'EV-10461', toEventId: 'EV-10463', type: 'TEMPORAL', strength: null, explanation: 'Close in time (14s)' },
    ],
    explanation: [
      expl('TEMPORAL', 'strong', 'Temporal proximity is strong'),
      expl('SPATIAL', 'weak', 'Spatial support insufficient across cameras'),
      expl('ENTITY', 'insufficient', 'No reliable entity continuity'),
    ],
    confidence: null,
    temporalWindowSec: 60,
    risk: { score: 40, severity: 'MEDIUM' },
    uncertainty: { reliability: 'LOW', note: 'Temporal proximity is strong; spatial and entity continuity are weak.' },
    trackCandidate: null,
    cameraChain: null,
    modalities: ['VIDEO', 'AUDIO', 'ANPR'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-NEPAL / RURAL FRINGE',
    sources: ['VIRTUAL_FENCE', 'AUDIO', 'ANPR'],
    healthContext: [],
    evidenceCount: 0,
    connectivity: 'LIVE',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T02:23:18Z`,
      updatedAt: `${D}T02:23:18Z`,
      transitions: [
        { status: 'RELATED', at: `${D}T02:23:12Z`, note: null },
        { status: 'UNCERTAIN', at: `${D}T02:23:18Z`, note: 'Spatial support not sustained.' },
      ],
    },
    updatedAt: `${D}T02:23:18Z`,
  },
  {
    correlationId: 'COR-1047',
    incidentId: null,
    incidentState: null,
    status: 'DISSOLVED',
    state: 'DISSOLVED',
    startedAt: `${D}T02:19:04Z`,
    endedAt: `${D}T02:19:11Z`,
    eventCount: 2,
    cameraCount: 2,
    memberEventsLoaded: null,
    memberEvents: [EV_10471, EV_10472],
    primaryEventId: 'EV-10471',
    relationships: [
      { fromEventId: 'EV-10471', toEventId: 'EV-10472', type: 'TEMPORAL', strength: null, explanation: 'Initially close in time (7s)' },
    ],
    explanation: [
      expl('TEMPORAL', '7 sec', 'Initially within window'),
      expl('CONTEXTUAL', 'not sustained', 'Additional observations did not sustain the relationship'),
    ],
    confidence: null,
    temporalWindowSec: 60,
    risk: { score: null, severity: null },
    uncertainty: { reliability: 'LOW', note: 'Previous correlation was not sustained.' },
    trackCandidate: null,
    cameraChain: null,
    modalities: ['VIDEO', 'ANPR'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-NEPAL / FOOTHILL',
    sources: ['VIRTUAL_FENCE', 'ANPR'],
    healthContext: [],
    evidenceCount: 0,
    connectivity: 'LIVE',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T02:19:13Z`,
      updatedAt: `${D}T02:22:40Z`,
      transitions: [
        { status: 'RELATED', at: `${D}T02:19:13Z`, note: null },
        { status: 'DISSOLVED', at: `${D}T02:22:40Z`, note: 'Additional observations did not sustain the relationship.' },
      ],
    },
    updatedAt: `${D}T02:22:40Z`,
  },
  {
    correlationId: 'COR-1048',
    incidentId: null,
    incidentState: null,
    status: 'CORRELATED',
    state: 'STABLE',
    startedAt: `${D}T03:02:44Z`,
    endedAt: `${D}T03:02:51Z`,
    eventCount: 2,
    cameraCount: 1,
    memberEventsLoaded: null,
    memberEvents: [EV_10481, EV_10482],
    primaryEventId: 'EV-10481',
    relationships: [
      { fromEventId: 'EV-10481', toEventId: 'EV-10482', type: 'ENTITY', strength: null, explanation: 'Possible same track candidate' },
    ],
    explanation: [
      expl('TEMPORAL', '7 sec', 'Within configured window'),
      expl('ENTITY', 'possible continuation', 'Track continuity'),
    ],
    // Correlation is not severity: this correlated group is LOW risk (§69).
    confidence: { value: 85, note: 'Track continuity supports grouping.' },
    temporalWindowSec: 60,
    risk: { score: 12, severity: 'LOW' },
    uncertainty: { reliability: 'HIGH', note: null },
    trackCandidate: { trackId: 'TRK-1047', confidence: 0.85, label: 'possible same entity' },
    cameraChain: ['CAM-12'],
    modalities: ['VIDEO'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-BHUTAN / HILLY-FOREST',
    sources: ['VIRTUAL_FENCE', 'TRACKING'],
    healthContext: [CAM12DEGRADED],
    evidenceCount: 0,
    connectivity: 'LIVE',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T03:02:53Z`,
      updatedAt: `${D}T03:04:00Z`,
      transitions: [
        { status: 'CORRELATED', at: `${D}T03:02:53Z`, note: null },
        { status: 'DISSOLVED', at: `${D}T03:04:00Z`, note: 'Additional observations did not sustain the relationship.' },
      ],
    },
    updatedAt: `${D}T03:04:00Z`,
  },
  {
    correlationId: 'COR-1049',
    incidentId: 'INC-1049',
    incidentState: 'NEW',
    status: 'CORRELATED',
    state: 'ACTIVE',
    startedAt: `${D}T02:31:10Z`,
    endedAt: `${D}T02:31:33Z`,
    eventCount: 4,
    cameraCount: 2,
    memberEventsLoaded: null,
    memberEvents: [EV_10491, EV_10492, EV_10493, EV_10494],
    primaryEventId: 'EV-10492',
    relationships: [
      { fromEventId: 'EV-10491', toEventId: 'EV-10493', type: 'CAMERA', strength: null, explanation: 'Cross-camera observation CAM-12 → CAM-07' },
      { fromEventId: 'EV-10491', toEventId: 'EV-10492', type: 'SEQUENCE', strength: null, explanation: 'Zone entry after detection' },
      { fromEventId: 'EV-10493', toEventId: 'EV-10494', type: 'ENTITY', strength: null, explanation: 'Possible same track candidate' },
    ],
    explanation: [
      expl('TEMPORAL', '23 sec', 'Within configured window'),
      expl('SPATIAL', 'nearby cameras', 'CAM-12 and CAM-07 linked'),
      expl('ENTITY', 'possible continuation', 'Re-ID candidate'),
      expl('CONTEXTUAL', 'health context', 'Reading camera has degraded reliability'),
    ],
    confidence: { value: 71, note: 'Temporal and cross-camera signals support grouping; image quality is reduced.' },
    temporalWindowSec: 60,
    risk: { score: 58, severity: 'MEDIUM' },
    uncertainty: { reliability: 'MEDIUM', note: 'One supporting camera has degraded image quality. Camera reliability may reduce confidence in associated observations.' },
    trackCandidate: { trackId: 'TRK-1048', confidence: 0.7, label: 'possible same entity' },
    cameraChain: ['CAM-12', 'CAM-07'],
    modalities: ['VIDEO'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-NEPAL / FOOTHILL',
    sources: ['VIRTUAL_FENCE', 'RE_ID'],
    healthContext: [CAM12DEGRADED],
    evidenceCount: 2,
    connectivity: 'DELAYED',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T02:31:37Z`,
      updatedAt: `${D}T02:31:37Z`,
      transitions: [
        { status: 'RELATED', at: `${D}T02:31:30Z`, note: null },
        { status: 'CORRELATED', at: `${D}T02:31:37Z`, note: null },
      ],
    },
    updatedAt: `${D}T02:31:37Z`,
  },
  {
    // Scenario 9 — LARGE GROUP (20 signals). eventCount is authoritative; the
    // list returns it lazily, and loading every member is an explicit action.
    correlationId: 'COR-1050',
    incidentId: 'INC-1050',
    incidentState: 'NEW',
    status: 'CORRELATED',
    state: 'ACTIVE',
    startedAt: `${D}T02:40:10Z`,
    endedAt: `${D}T02:42:59Z`,
    eventCount: 20,
    cameraCount: 2,
    memberEventsLoaded: 12,
    memberEvents: LARGE_MEMBERS.slice(0, 12),
    primaryEventId: 'EV-110001',
    relationships: [
      { fromEventId: 'EV-110001', toEventId: 'EV-110002', type: 'SUPPORTING', strength: null, explanation: 'Repeated signals share track and zone context' },
    ],
    explanation: [
      expl('TEMPORAL', '2m 49s', 'High-density sequence within extended window'),
      expl('SPATIAL', 'same sector', 'SECTOR-B'),
      expl('ENTITY', 'possible continuation', 'Track continuity across 20 signals'),
    ],
    confidence: { value: 90, note: 'High-density temporal and entity relationship signals.' },
    temporalWindowSec: 180,
    risk: { score: 76, severity: 'HIGH' },
    uncertainty: { reliability: 'MEDIUM', note: 'Dense sequence; individual reading reliability varies.' },
    trackCandidate: { trackId: 'TRK-1050', confidence: 0.82, label: 'possible same entity' },
    cameraChain: ['CAM-19', 'CAM-03'],
    modalities: ['VIDEO', 'ANPR', 'AUDIO'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-NEPAL / RURAL FRINGE',
    sources: ['VIRTUAL_FENCE', 'ANPR', 'AUDIO'],
    healthContext: [],
    evidenceCount: 6,
    connectivity: 'LAST_SYNCED',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T02:43:05Z`,
      updatedAt: `${D}T02:43:05Z`,
      transitions: [
        { status: 'RELATED', at: `${D}T02:41:00Z`, note: null },
        { status: 'CORRELATED', at: `${D}T02:43:05Z`, note: 'Grouping continues to grow as signals arrive.' },
      ],
    },
    updatedAt: `${D}T02:43:05Z`,
  },
  // Scenario 10 — RELATED (grouping in progress, not yet correlated). A real
  // signal that is clearly linked but has not been raised: no incident, no
  // confidence — correlation is never forced and never fabricated (§71).
  {
    correlationId: 'COR-1051',
    incidentId: null,
    incidentState: null,
    status: 'RELATED',
    state: 'ACTIVE',
    startedAt: `${D}T03:09:18Z`,
    endedAt: null,
    eventCount: 2,
    cameraCount: 1,
    memberEventsLoaded: null,
    memberEvents: [EV_10511, EV_10512],
    primaryEventId: 'EV-110021',
    relationships: [
      { fromEventId: 'EV-110021', toEventId: 'EV-110022', type: 'SEQUENCE', strength: null, explanation: 'Signals share track and zone context; grouping in progress.' },
    ],
    explanation: [
      expl('TEMPORAL', '17 sec', 'Within configured window'),
      expl('SPATIAL', 'same zone', 'ZONE-B'),
    ],
    confidence: null,
    temporalWindowSec: 60,
    risk: { score: 22, severity: 'LOW' },
    uncertainty: { reliability: 'HIGH', note: null },
    trackCandidate: null,
    cameraChain: ['CAM-07'],
    modalities: ['VIDEO'],
    sectorId: 'SECTOR-B',
    regionProfile: 'INDO-NEPAL / FOOTHILL',
    sources: ['VIRTUAL_FENCE', 'TRACKING'],
    healthContext: [],
    evidenceCount: 0,
    connectivity: 'LIVE',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: `${D}T03:09:35Z`,
      updatedAt: `${D}T03:09:35Z`,
      transitions: [
        { status: 'RELATED', at: `${D}T03:09:35Z`, note: 'Two signals share track and zone context; grouping in progress.' },
      ],
    },
    updatedAt: `${D}T03:09:35Z`,
  },
]

export const MOCK_GROUP_BY_ID: Record<string, CorrelationGroup> = Object.fromEntries(
  MOCK_GROUPS.map(g => [g.correlationId, g])
)

export const MOCK_MEMBER_BY_ID: Record<string, CorrelationEventMember> = Object.fromEntries(
  MOCK_GROUPS.flatMap(g => g.memberEvents.map(m => [m.eventId, m]))
)

export const DEFAULT_LIST_SORT: EventLogQuery = {
  search: '',
  correlation: 'ALL',
  severity: 'ALL',
  cameraId: 'ALL',
  sectorId: 'ALL',
  source: 'ALL',
  connectivity: 'ALL',
  timeRange: 'all',
  sort: 'time',
  order: 'desc',
  page: 1,
  pageSize: 8,
}
