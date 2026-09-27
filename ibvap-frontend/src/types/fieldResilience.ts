// ─────────────────────────────────────────────────────────────────────────────
// प्रहार — Field Intelligence & Resilience types
//
// Contract for the field capability screen (SIH screenshot 6): human/animal
// differentiation in wildlife-heavy border terrain + offline-first resilience
// when connectivity degrades. Answers: "will this system actually work in
// difficult border environments?"
//
//   Prototype Data → same UI → Real API → Actual field system
// ─────────────────────────────────────────────────────────────────────────────

// ─── Human vs animal subjects ────────────────────────────────────────────────
export type SubjectKind = 'ANIMAL' | 'HUMAN'

export interface SubjectClassification {
  kind: SubjectKind
  label: string
  confidence: number
  outcome: string
  outcomeTone: 'safe' | 'warning'
  note: string
}

// ─── Why the difference matters (wildlife-heavy environment) ────────────────
export interface FieldReasonContext {
  title: string
  problem: string
  approachSteps: string[]
  disclaimer: string
}

// ─── Offline-first resilience ────────────────────────────────────────────────
export type ResilienceStateId = 'CONNECTED' | 'NETWORK-LOST' | 'BUFFERING' | 'SYNCING' | 'SYNC-COMPLETE'

export interface ResilienceStep {
  label: string
  detail: string
  stateId: ResilienceStateId
  last?: boolean
}

export interface FieldVisualState {
  id: ResilienceStateId
  label: string
}

// ─── Degraded camera health ──────────────────────────────────────────────────
export interface DegradedCamera {
  id: string
  state: string
  coverage: string
  localProcessing: string
  bufferedEvents: string
}

// ─── Bandwidth adaptation ladder ─────────────────────────────────────────────
export interface BandwidthStep {
  label: string
  detail: string
}

// ─── Remote outpost station ──────────────────────────────────────────────────
export interface RemoteStation {
  name: string
  network: string
  localInference: string
  evidenceBuffering: string
  autoSync: string
}

// ─── Full dataset ────────────────────────────────────────────────────────────
export interface FieldIntelligenceData {
  subjects: SubjectClassification[]
  reason: FieldReasonContext
  resilienceSteps: ResilienceStep[]
  visualStates: FieldVisualState[]
  degradedCamera: DegradedCamera
  bandwidth: BandwidthStep[]
  station: RemoteStation
}