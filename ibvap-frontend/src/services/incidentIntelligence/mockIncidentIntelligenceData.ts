// ─────────────────────────────────────────────────────────────────────────────
// Mock Incident Intelligence prototype data — DEMO ONLY.
//
// Composes the coherent INC-024 story (same timeline as the Command Center) with
// explainable risk factors and an evidence record. Risk factor math sums to the
// canonical 82 score; 82 sits in the HIGH band (65–84), never CRITICAL.
//
//   Prototype Data → same UI → Real API → Actual investigation system
// ─────────────────────────────────────────────────────────────────────────────

import type { IncidentIntelligenceData } from '@/types'

export const INCIDENT_INTELLIGENCE_DEMO: IncidentIntelligenceData = {
  incidentId: 'INC-024',
  riskScore: 82,
  band: 'HIGH',
  correlationCount: 6,

  timelineTitle: 'Correlated Event Timeline',

  timeline: [
    { step: '01', time: '22:41', text: 'Person detected', cameraId: 'CAM-01' },
    { step: '02', time: '22:43', text: 'Restricted-zone entry', cameraId: 'CAM-01' },
    { step: '03', time: '22:44', text: 'Virtual fence breach', cameraId: 'CAM-01' },
    { step: '04', time: '22:46', text: 'Cross-camera candidate match', cameraId: 'CAM-02' },
    { step: '05', time: '22:47', text: 'Suspicious movement', cameraId: 'CAM-02' },
    { step: '06', time: '22:48', text: 'Incident created', cameraId: 'CAM-02' },
  ],

  riskFactors: [
    { label: 'Restricted Zone', points: 25, tone: 'critical' },
    { label: 'Fence Breach', points: 25, tone: 'critical' },
    { label: 'Cross-Camera Match', points: 15, tone: 'warning' },
    { label: 'Night Movement', points: 10, tone: 'warning' },
    { label: 'Confidence', points: 7, tone: 'info' },
  ],

  bandBrackets: [
    { label: 'LOW', range: '0–39' },
    { label: 'MEDIUM', range: '40–64' },
    { label: 'HIGH', range: '65–84' },
    { label: 'CRITICAL', range: '85–100' },
  ],

  decisionNote: 'Decision-support, not decision replacement.',

  reId: {
    trackId: 'TRK-014',
    cameraChain: 'CAM-01 → CAM-02',
    relationLabel: 'Possible Same Entity',
    confidencePct: 91,
  },

  evidence: {
    evidenceId: 'EVD-024',
    cameraId: 'CAM-01',
    timestamp: '22:49:12',
    media: 'Snapshot + Event Metadata',
    sha256: 'A83F…91D',
    ledgerTx: 'TX-8A72',
    integrity: '✓ VERIFIED',
    custody: '✓ INTACT',
  },

  pipeline: [
    { label: 'Incident', detail: 'INC-024 raised', verified: true },
    { label: 'Evidence', detail: 'EVD-024 captured', verified: true },
    { label: 'SHA-256', detail: 'Digest A83F…91D', verified: true },
    { label: 'Signed Record', detail: 'Operator-device key', verified: true },
    { label: 'Hyperledger Ledger', detail: 'Immutably recorded', verified: true },
    { label: 'Transaction Verified', detail: 'TX-8A72 confirmed', verified: true },
  ],

  security: [
    { label: 'TLS', ok: true },
    { label: 'RBAC', ok: true },
    { label: 'Audit', ok: true },
    { label: 'Ledger', ok: true },
  ],

  review: {
    title: 'Low-Confidence Events → Human Review',
    note: 'Officer decision remains authoritative. प्रहार supports decision-making.',
  },
}