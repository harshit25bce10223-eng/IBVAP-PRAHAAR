// ─────────────────────────────────────────────────────────────────────────────
// Mock GIS / Digital Twin prototype data — DEMO ONLY.
//
// Centralized so the GIS page never hardcodes cartographic values. Consistent
// with the rest of the prototype (CAM-01/CAM-02/CAM-07/CAM-12, TRK-014,
// INC-024 risk 82 HIGH). Map geometry lives in a 1200 × 520 viewBox that
// matches the dominant full-width map area at 1920 × 1080.
//
//   Prototype Data → same UI → Real GIS/API → Actual operational system
// ─────────────────────────────────────────────────────────────────────────────

import type { GisData } from '@/types'

export const GIS_DEMO: GisData = {
  sectorRef: 'SECTOR-7',
  coords: '27.72°N 88.15°E',

  terrain: {
    // Subtle hilly-height bands that give cartographic depth without fake 3D.
    hillPaths: [
      'M40,330 L95,275 L150,330 Z',
      'M120,400 L185,330 L250,400 Z',
      'M290,310 L355,265 L420,310 Z',
      'M620,240 L690,185 L760,240 Z',
      'M880,260 L945,205 L1010,260 Z',
      'M1060,420 L1120,365 L1180,420 Z',
    ],
    // Forest canopy patches (operational context: wildlife-heavy ground).
    forestPaths: [
      'M150,55 q60,50 20,110 q-70,40 -130,0 q-40,-60 0,-100 z',
      'M520,330 q80,-30 120,40 q10,80 -70,100 q-90,10 -110,-55 z',
      'M860,380 q65,-25 100,30 q5,70 -70,82 q-80,12 -90,-50 z',
      'M980,120 q55,-20 90,25 q5,60 -65,70 q-70,10 -80,-40 z',
    ],
    // Sector roads / patrol trails.
    roadPaths: [
      'M110,515 L340,320 L520,310 L760,360 L960,440',
      'M380,515 L500,420 L650,370 L880,280 L1120,240',
      'M620,515 L700,440 L820,400',
    ],
  },

  borderRef: {
    label: 'INDIA — NEPAL',
    path: 'M0,205 Q120,188 240,195 Q360,202 480,186 Q600,170 720,185 Q840,200 960,180 Q1080,162 1200,176',
  },

  cameras: [
    { id: 'CAM-01', state: 'ONLINE',  x: 200, y: 270, sectorId: 'S7-N' },
    { id: 'CAM-02', state: 'ONLINE',  x: 430, y: 210, sectorId: 'S7-C' },
    { id: 'CAM-03', state: 'ONLINE',  x: 700, y: 300, sectorId: 'S7-S' },
    { id: 'CAM-07', state: 'DEGRADED', x: 900, y: 390, sectorId: 'S7-E' },
    { id: 'CAM-12', state: 'ONLINE',  x: 165, y: 120, sectorId: 'S7-F' },
  ],

  tracks: [
    {
      id: 'TRK-014',
      label: 'Entity Track',
      classification: 'Person',
      confidence: 91,
      direction: 'NW → SE',
      points: [
        { x: 200, y: 270, at: '22:41' },
        { x: 300, y: 250, at: '22:43' },
        { x: 385, y: 225, at: '22:44' },
        { x: 430, y: 210, at: '22:46' },
        { x: 492, y: 140, at: '22:48' },
      ],
      cameraTransitions: [
        { from: 'CAM-01', to: 'CAM-01', at: '22:41', note: 'Person detected' },
        { from: 'CAM-01', to: 'CAM-02', at: '22:46', note: 'Cross-camera candidate match' },
      ],
    },
  ],

  incidents: [
    {
      id: 'INC-024',
      riskScore: 82,
      band: 'HIGH',
      cameraId: 'CAM-02',
      trackId: 'TRK-014',
      title: 'Restricted Zone Breach',
      reason: 'Restricted Zone Breach',
      correlationCount: 2,
      x: 492,
      y: 140,
      isGolden: true,
    },
    {
      id: 'INC-021',
      riskScore: 61,
      band: 'MEDIUM',
      cameraId: 'CAM-05',
      trackId: 'TRK-008',
      title: 'Unusual Dwell',
      reason: 'Proximity dwell beyond nominal threshold',
      correlationCount: 1,
      x: 770,
      y: 305,
    },
  ],

  zones: [
    {
      id: 'ZONE-RZ',
      label: 'RESTRICTED ZONE',
      kind: 'RESTRICTED',
      path: 'M320,155 L475,130 L505,240 L355,270 Z',
      info: 'High-priority buffer — entry requires cleared track authorisation.',
    },
    {
      id: 'ZONE-VF',
      label: 'VIRTUAL FENCE',
      kind: 'FENCE',
      path: 'M0,250 Q120,233 240,240 Q360,247 480,231 Q600,215 720,230 Q840,245 960,225 Q1080,207 1200,221',
      info: 'Perimeter sensing line — breach here raises a zone alert.',
    },
    {
      id: 'ZONE-FS',
      label: 'FOREST ZONE',
      kind: 'FOREST',
      path: 'M150,55 q60,50 20,110 q-70,40 -130,0 q-40,-60 0,-100 z',
      info: 'Wildlife-heavy ground — human/animal differentiation is enabled here.',
    },
  ],

  riskHeat: [
    {
      id: 'HOT-1',
      label: 'RESTRICTED ZONE',
      level: 'HIGH',
      x: 415,
      y: 205,
      radius: 105,
      note: 'Breach corridor — repeated zone entries (7D).',
    },
    {
      id: 'HOT-2',
      label: 'SECTOR ROAD',
      level: 'MEDIUM',
      x: 770,
      y: 305,
      radius: 85,
      note: 'Unusual dwell near patrol trail — repeat location.',
    },
    {
      id: 'HOT-3',
      label: 'FOREST ZONE',
      level: 'LOW',
      x: 220,
      y: 115,
      radius: 95,
      note: 'Wildlife movement — continues human/animal differentiation.',
    },
  ],

  historicalActivity: [
    { id: 'HIST-1', kind: 'BREACH',   label: 'Zone entry patterns', x: 415,  y: 175, count: 12, window: '7D' },
    { id: 'HIST-2', kind: 'BREACH',   label: 'Zone entry patterns', x: 412,  y: 172, count: 5,  window: '24H' },
    { id: 'HIST-3', kind: 'CROSSING', label: 'Night crossing',      x: 765,  y: 295, count: 6,  window: '7D' },
    { id: 'HIST-4', kind: 'ANIMAL',   label: 'Wildlife corridor',   x: 218,  y: 95,  count: 14, window: '7D' },
    { id: 'HIST-5', kind: 'ANIMAL',   label: 'Wildlife corridor',   x: 600,  y: 400, count: 8,  window: '7D' },
  ],

  forestZone: {
    cameraId: 'CAM-12',
    zoneLabel: 'FOREST ZONE',
    animal: { confidence: 96, outcome: 'Non-Threat' },
    human:  { confidence: 94, outcome: 'Track Created' },
    note: 'Wildlife movement in forest / hilly border must not raise unnecessary intrusion alerts.',
  },
}