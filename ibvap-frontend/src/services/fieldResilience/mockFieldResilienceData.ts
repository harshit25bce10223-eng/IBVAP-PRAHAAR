// ─────────────────────────────────────────────────────────────────────────────
// Mock Field Intelligence & Resilience prototype data — DEMO ONLY.
//
// Uses the canonical CAM-12 (forest/hilly ground) and CAM-07 (degraded east
// edge) references from across the prototype so the field view stays coherent
// with the rest of प्रहार. Resilience numbers describe prototype behaviour,
// not measured field performance.
//
//   Prototype Data → same UI → Real API → Actual field system
// ─────────────────────────────────────────────────────────────────────────────

import type { FieldIntelligenceData } from '@/types'

export const FIELD_INTELLIGENCE_DEMO: FieldIntelligenceData = {
  subjects: [
    {
      kind: 'ANIMAL',
      label: 'Animal',
      confidence: 96,
      outcome: 'Non-Threat',
      outcomeTone: 'safe',
      note: 'No intrusion alert raised.',
    },
    {
      kind: 'HUMAN',
      label: 'Human',
      confidence: 94,
      outcome: 'Track Created',
      outcomeTone: 'warning',
      note: 'Potential intrusion — monitoring continues.',
    },
  ],

  reason: {
    title: 'Forest / Hilly Border Environment',
    problem: 'Wildlife movement can trigger false intrusion alerts near the border.',
    approachSteps: ['Detect', 'Classify', 'Track relevant entities', 'Reduce unnecessary alerts'],
    disclaimer: 'Prototype behaviour — not a measured false-positive reduction.',
  },

  resilienceSteps: [
    { label: 'CONNECTED', detail: 'Full video uplink', stateId: 'CONNECTED' },
    { label: 'NETWORK LOST', detail: 'Local buffer engaged', stateId: 'NETWORK-LOST' },
    { label: 'LOCAL BUFFER', detail: '7 events stored at edge', stateId: 'BUFFERING' },
    { label: 'NETWORK RESTORED', detail: 'Link recovery detected', stateId: 'SYNCING' },
    { label: 'AUTO SYNC', detail: 'Queue replay at reduced load', stateId: 'SYNCING' },
    { label: '7/7 SYNCHRONIZED', detail: 'Buffer drained to ledger', stateId: 'SYNC-COMPLETE', last: true },
  ],

  visualStates: [
    { id: 'CONNECTED', label: 'CONNECTED' },
    { id: 'NETWORK-LOST', label: 'NETWORK LOST' },
    { id: 'BUFFERING', label: 'BUFFERING' },
    { id: 'SYNCING', label: 'SYNCING' },
    { id: 'SYNC-COMPLETE', label: 'SYNC COMPLETE' },
  ],

  degradedCamera: {
    id: 'CAM-07',
    state: 'DEGRADED',
    coverage: 'COMPROMISED',
    localProcessing: 'READY',
    bufferedEvents: '07',
  },

  bandwidth: [
    { label: 'FULL VIDEO', detail: 'Nominal uplink' },
    { label: 'NETWORK DEGRADES', detail: 'Link quality drops' },
    { label: 'REDUCED FPS / BITRATE', detail: 'Adaptive streaming' },
    { label: 'METADATA + THUMBNAIL PRIORITY', detail: 'Key-content first' },
  ],

  station: {
    name: 'REMOTE BOP',
    network: 'Intermittent',
    localInference: 'Available',
    evidenceBuffering: 'Active',
    autoSync: 'Ready',
  },
}