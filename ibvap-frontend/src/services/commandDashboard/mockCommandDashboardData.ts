// ─────────────────────────────────────────────────────────────────────────────
// Mock Command Center prototype data — DEMO ONLY.
//
// Centralized so the UI never hardcodes operational values. Mirrors the future
// API contract:
//   Prototype Data → same UI contract → Real API → Actual Backend / AI providers
//
// The Golden Incident (INC-024) is the single coherent showcase story:
//   CAM-01 → Person → TRK-014 → Zone Entry → Fence Breach → CAM-02 candidate
//   match → suspicious movement → INC-024 (risk 82, HIGH).
// ─────────────────────────────────────────────────────────────────────────────

import type { CommandDashboardData } from '@/types'

export const COMMAND_DASHBOARD_DEMO: CommandDashboardData = {
  kpis: {
    totalCameras: 12,
    onlineCameras: 10,
    offlineCameras: 2,
    activeIncidents: 3,
    incidentHigh: 1,
    incidentMedium: 2,
    livePersons: 4,
    liveVehicles: 2,
    liveAnimals: 1,
    systemHealthPct: 94,
    healthLabel: 'Coverage Nominal',
    riskSummary: { critical: 0, high: 1, medium: 2, low: 4 },
  },

  goldenIncident: {
    incidentId: 'INC-024',
    entityId: 'TRK-014',
    riskScore: 82,
    band: 'HIGH',
    correlationCount: 6,
    steps: [
      { step: '01', time: '22:41', text: 'Person detected', cameraId: 'CAM-01' },
      { step: '02', time: '22:43', text: 'Restricted-zone entry', cameraId: 'CAM-01' },
      { step: '03', time: '22:44', text: 'Fence breach', cameraId: 'CAM-01' },
      { step: '04', time: '22:46', text: 'Candidate match', cameraId: 'CAM-02' },
      { step: '05', time: '22:47', text: 'Suspicious movement', cameraId: 'CAM-02' },
      { step: '06', time: '22:48', text: 'Incident created', cameraId: 'CAM-02' },
    ],
  },

  incidents: [
    {
      id: 'INC-024',
      riskScore: 82,
      band: 'HIGH',
      cameraId: 'CAM-02',
      title: 'Restricted Zone Breach',
      trackId: 'TRK-014',
      correlatedCameras: 2,
      summary: 'Entity entered restricted zone; cross-camera candidate match confirmed across 2 cameras.',
      isGolden: true,
    },
    {
      id: 'INC-021',
      riskScore: 61,
      band: 'MEDIUM',
      cameraId: 'CAM-05',
      title: 'Unusual Dwell',
      trackId: 'TRK-008',
      correlatedCameras: 1,
      summary: 'Person loitering within proximity band beyond nominal dwell threshold.',
    },
    {
      id: 'INC-019',
      riskScore: 54,
      band: 'MEDIUM',
      cameraId: 'CAM-09',
      title: 'Vehicle Pattern Anomaly',
      trackId: 'TRK-006',
      correlatedCameras: 1,
      summary: 'Unregistered vehicle repeating a non-standard approach pattern near sector road.',
    },
  ],

  cameras: [
    {
      id: 'CAM-01',
      state: 'ONLINE',
      classification: 'Person',
      classConfidence: 96,
      trackId: 'TRK-014',
      note: 'Intrusion candidate',
      stateLabel: 'Online',
    },
    {
      id: 'CAM-02',
      state: 'ONLINE',
      classification: 'Person',
      classConfidence: 91,
      trackId: 'TRK-014',
      note: 'Candidate match',
      stateLabel: 'Online',
    },
    {
      id: 'CAM-07',
      state: 'DEGRADED',
      classification: 'Animal',
      classConfidence: 96,
      note: 'No Intrusion',
      stateLabel: 'Degraded',
    },
  ],

  humanAnimal: {
    title: 'Forest Camera',
    cameraId: 'CAM-12',
    results: [
      { kind: 'ANIMAL', confidence: 96, outcome: 'Non-Threat' },
      { kind: 'HUMAN', confidence: 94, outcome: 'Track Created' },
    ],
    purpose: 'Wildlife movement in forest / hilly border must not raise unnecessary intrusion alerts.',
  },

  systemHealth: [
    { name: 'CAM-01', state: 'ONLINE', monospace: true },
    { name: 'CAM-02', state: 'ONLINE', monospace: true },
    { name: 'CAM-07', state: 'DEGRADED', monospace: true },
    { name: 'BACKEND', state: 'READY', monospace: false },
    { name: 'AI ENGINE', state: 'READY', monospace: false },
    { name: 'LEDGER', state: 'VERIFIED', monospace: false },
    { name: 'NETWORK', state: 'STABLE', monospace: false },
  ],

  activity: [
    { time: '22:48', text: 'INC-024 created · risk 82 HIGH', tone: 'critical' },
    { time: '22:47', text: 'Suspicious movement · CAM-02', tone: 'warning' },
    { time: '22:46', text: 'CAM-02 candidate match · TRK-014', tone: 'warning' },
    { time: '22:44', text: 'Fence breach detected', tone: 'warning' },
    { time: '22:43', text: 'Restricted-zone entry · TRK-014', tone: 'info' },
    { time: '22:41', text: 'Person detected · CAM-01', tone: 'info' },
  ],

  evidence: {
    state: 'Integrity Verified',
    algorithm: 'SHA-256',
    ledger: 'Ledger Connected',
    security: [
      { label: 'TLS', ok: true },
      { label: 'RBAC', ok: true },
      { label: 'AUDIT', ok: true },
      { label: 'LEDGER', ok: true },
    ],
  },
}