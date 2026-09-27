// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — isolated development fixtures (DEMO ONLY)
//
// Every value below is a hand-written fixture for local development. It is
// NEVER live telemetry. Components must surface the DEMO source label and
// must never present these values as current backend measurements.
//
// Scenarios:
//   CAM-07 — healthy reference (calm display, no issue list)
//   CAM-12 — degraded: network + image + viewpoint shift (core UX test)
//   CAM-19 — offline: last-known state + compromised coverage
//   CAM-03 — telemetry unavailable: UNKNOWN, nothing invented
// ─────────────────────────────────────────────────────────────────────────────

import type { CameraHealth } from '@/types/cameraHealth'

const now = Date.now()
const iso = (msAgo: number) => new Date(now - msAgo).toISOString()

/** 7-day daily sharpness baseline, oldest → newest (provided points only). */
const SHARPNESS_DECLINE_7D = [0.93, 0.92, 0.9, 0.88, 0.85, 0.8, 0.74, 0.68]
const SHARPNESS_STABLE_7D = [0.91, 0.9, 0.92, 0.91, 0.9, 0.91, 0.92, 0.91]
const LATENCY_24H = [38, 41, 44, 52, 68, 84, 96, 110]
const LOSS_24H = [0.3, 0.4, 0.5, 0.9, 1.6, 2.4, 3.1, 3.8]

const CAM_07: CameraHealth = {
  cameraId: 'CAM-07',
  status: 'ONLINE',
  statusReason: null,
  lastUpdated: iso(3_000),
  source: 'DEMO',
  regionProfile: {
    configured: true,
    region: 'INDO-NEPAL',
    terrain: 'FOOTHILL / PLAINS',
    location: 'Sector outpost feed',
  },
  stream: {
    state: 'CONNECTED',
    fps: 24,
    expectedFps: 25,
    frameDropPercent: 0.8,
    staleSeconds: 2,
    reconnectCount: 0,
  },
  image: {
    status: 'GOOD',
    metrics: [
      { metric: 'sharpness', label: 'Sharpness', value: 0.91, unit: 'ratio', status: 'GOOD', reason: null },
      { metric: 'brightness', label: 'Brightness', value: 0.78, unit: 'ratio', status: 'GOOD', reason: null },
      { metric: 'exposure', label: 'Exposure', value: 'NORMAL', unit: null, status: 'GOOD', reason: null },
      { metric: 'noise', label: 'Noise', value: 'LOW', unit: null, status: 'GOOD', reason: null },
    ],
    backgroundStability: 'Stable against slow baseline',
  },
  network: {
    status: 'STABLE',
    latencyMs: 42,
    latencyVarianceMs: 6,
    packetLossPercent: 0.4,
    heartbeatAgeSec: 3,
  },
  viewpoint: {
    status: 'STABLE',
    shiftScore: 0.04,
    detectedAt: null,
    shiftDetected: false,
    fenceConfidenceNote: null,
  },
  trends: [
    {
      metric: 'sharpness',
      label: 'Sharpness',
      direction: 'STABLE',
      deltaPercent: 0,
      window: '7 DAYS',
      persistence: null,
      series: SHARPNESS_STABLE_7D,
    },
  ],
  issues: [],
  operationalImpact: {
    level: 'NONE',
    coverage: 'NORMAL',
    affectedModules: [],
    message: 'No current impact.',
  },
  maintenance: null,
  lastKnown: null,
}

const CAM_12: CameraHealth = {
  cameraId: 'CAM-12',
  status: 'DEGRADED',
  statusReason: 'Viewpoint shift detected 2 min ago; image sharpness below recent baseline.',
  lastUpdated: iso(4_000),
  source: 'DEMO',
  regionProfile: {
    configured: true,
    region: 'INDO-BHUTAN',
    terrain: 'HILLY / FOREST',
    location: 'Ridge-line feed',
  },
  stream: {
    state: 'CONNECTED',
    fps: 21,
    expectedFps: 25,
    frameDropPercent: 2.1,
    staleSeconds: 4,
    reconnectCount: 4,
  },
  image: {
    status: 'DEGRADED',
    metrics: [
      { metric: 'sharpness', label: 'Sharpness', value: 0.68, unit: 'ratio', status: 'DEGRADED', reason: 'Below recent baseline' },
      { metric: 'brightness', label: 'Brightness', value: 0.52, unit: 'ratio', status: 'DEGRADED', reason: 'Below recent baseline' },
      { metric: 'exposure', label: 'Exposure', value: 'NORMAL', unit: null, status: 'GOOD', reason: null },
      { metric: 'noise', label: 'Noise', value: 'ELEVATED', unit: null, status: 'DEGRADED', reason: 'Rising with low light' },
    ],
    backgroundStability: 'Slow baseline drifting — vegetation growth suspected, unconfirmed',
  },
  network: {
    status: 'DEGRADED',
    latencyMs: 110,
    latencyVarianceMs: 48,
    packetLossPercent: 3.8,
    heartbeatAgeSec: 4,
  },
  viewpoint: {
    status: 'SHIFT_DETECTED',
    shiftScore: 0.87,
    detectedAt: iso(2 * 60_000),
    shiftDetected: true,
    fenceConfidenceNote: 'Virtual Fence reliability reduced until an officer reviews the fence',
  },
  trends: [
    {
      metric: 'sharpness',
      label: 'Sharpness',
      direction: 'DEGRADING',
      deltaPercent: -7.2,
      window: '7 DAYS',
      persistence: '8 days',
      series: SHARPNESS_DECLINE_7D,
    },
    {
      metric: 'latency',
      label: 'Latency',
      direction: 'DEGRADING',
      deltaPercent: 61.8,
      window: '24 HR',
      persistence: '6 hr',
      series: LATENCY_24H,
    },
    {
      metric: 'packet-loss',
      label: 'Packet loss',
      direction: 'DEGRADING',
      deltaPercent: 58.3,
      window: '24 HR',
      persistence: '6 hr',
      series: LOSS_24H,
    },
  ],
  issues: [
    {
      issueId: 'ISS-CAM12-VP-01',
      title: 'Possible viewpoint shift',
      impact: 'HIGH',
      firstSeen: iso(2 * 60_000),
      lastSeen: iso(30_000),
      count: 4,
      durationLabel: '2 min',
      impactNote: 'Fence reliability reduced',
      affectedModules: ['Virtual Fence'],
    },
    {
      issueId: 'ISS-CAM12-SH-01',
      title: 'Image sharpness degradation',
      impact: 'MEDIUM',
      firstSeen: iso(8 * 24 * 3600_000),
      lastSeen: iso(3600_000),
      count: 96,
      durationLabel: '8 days',
      impactNote: 'Lower image quality for downstream analytics',
      affectedModules: ['Detection', 'Tracking'],
    },
    {
      issueId: 'ISS-CAM12-NW-01',
      title: 'Network degraded',
      impact: 'MEDIUM',
      firstSeen: iso(6 * 3600_000),
      lastSeen: iso(60_000),
      count: 18,
      durationLabel: '6 hr',
      impactNote: 'Live visibility may be delayed',
      affectedModules: ['Live visibility'],
    },
  ],
  operationalImpact: {
    level: 'DEGRADED',
    coverage: 'DEGRADED',
    affectedModules: ['Virtual Fence', 'Detection', 'Tracking'],
    message: 'Virtual Fence reliability reduced. Live visibility may be delayed.',
  },
  maintenance: {
    recommended: true,
    reason: 'Sustained sharpness degradation over 8 days',
    durationLabel: '8 days',
    impactNote: 'Lower image quality for downstream analytics',
  },
  lastKnown: null,
}

const CAM_19: CameraHealth = {
  cameraId: 'CAM-19',
  status: 'OFFLINE',
  statusReason: 'No telemetry for 11 minutes. Showing last known state.',
  lastUpdated: iso(11 * 60_000),
  source: 'DEMO',
  regionProfile: {
    configured: true,
    region: 'INDO-NEPAL',
    terrain: 'RURAL / AGRICULTURAL FRINGE',
    location: 'Field-edge feed',
  },
  stream: {
    state: 'DISCONNECTED',
    fps: null,
    expectedFps: 25,
    frameDropPercent: null,
    staleSeconds: 660,
    reconnectCount: 7,
  },
  image: {
    status: 'UNKNOWN',
    metrics: [],
    backgroundStability: null,
  },
  network: {
    status: 'OFFLINE',
    latencyMs: null,
    latencyVarianceMs: null,
    packetLossPercent: null,
    heartbeatAgeSec: 660,
  },
  viewpoint: {
    status: 'UNKNOWN',
    shiftScore: null,
    detectedAt: null,
    shiftDetected: false,
    fenceConfidenceNote: null,
  },
  trends: [],
  issues: [
    {
      issueId: 'ISS-CAM19-ST-01',
      title: 'Stream disconnected',
      impact: 'HIGH',
      firstSeen: iso(11 * 60_000),
      lastSeen: iso(11 * 60_000),
      count: 1,
      durationLabel: '11 min',
      impactNote: 'Coverage compromised',
      affectedModules: ['Virtual Fence', 'Detection', 'Live visibility'],
    },
  ],
  operationalImpact: {
    level: 'COMPROMISED',
    coverage: 'COMPROMISED',
    affectedModules: ['Virtual Fence', 'Detection', 'Live visibility'],
    message: 'Coverage compromised. Last seen 11 min ago.',
  },
  maintenance: {
    recommended: true,
    reason: 'Stream unreachable for 11 minutes',
    durationLabel: '11 min',
    impactNote: 'Coverage compromised until the feed is restored',
  },
  lastKnown: {
    status: 'ONLINE',
    at: iso(11 * 60_000),
  },
}

const CAM_03: CameraHealth = {
  cameraId: 'CAM-03',
  status: 'UNKNOWN',
  statusReason: 'Health telemetry unavailable for this camera.',
  lastUpdated: null,
  source: 'UNAVAILABLE',
  regionProfile: {
    configured: true,
    region: 'INDO-NEPAL',
    terrain: 'RURAL / AGRICULTURAL FRINGE',
    location: 'Checkpoint feed',
  },
  stream: {
    state: 'UNKNOWN',
    fps: null,
    expectedFps: 30,
    frameDropPercent: null,
    staleSeconds: null,
    reconnectCount: null,
  },
  image: {
    status: 'UNKNOWN',
    metrics: [],
    backgroundStability: null,
  },
  network: {
    status: 'UNKNOWN',
    latencyMs: null,
    latencyVarianceMs: null,
    packetLossPercent: null,
    heartbeatAgeSec: null,
  },
  viewpoint: {
    status: 'UNKNOWN',
    shiftScore: null,
    detectedAt: null,
    shiftDetected: false,
    fenceConfidenceNote: null,
  },
  trends: [],
  issues: [],
  operationalImpact: {
    level: 'UNKNOWN',
    coverage: 'UNKNOWN',
    affectedModules: [],
    message: 'Health telemetry unavailable. State cannot be established.',
  },
  maintenance: null,
  lastKnown: null,
}

const CAM_05: CameraHealth = {
  cameraId: 'CAM-05',
  status: 'FROZEN',
  statusReason: 'Frame similarity remained above 0.99 for 120s persistence window.',
  lastUpdated: iso(5_000),
  source: 'DEMO',
  regionProfile: {
    configured: true,
    region: 'INDO-NEPAL',
    terrain: 'RIVERINE',
    location: 'Riverbed crossing outpost',
  },
  stream: {
    state: 'FROZEN',
    fps: 0,
    expectedFps: 25,
    frameDropPercent: 100,
    staleSeconds: 120,
    reconnectCount: 2,
  },
  image: {
    status: 'GOOD',
    metrics: [
      { metric: 'sharpness', label: 'Sharpness', value: 0.88, unit: 'ratio', status: 'GOOD', reason: null },
      { metric: 'brightness', label: 'Brightness', value: 0.72, unit: 'ratio', status: 'GOOD', reason: null },
      { metric: 'exposure', label: 'Exposure', value: 'NORMAL', unit: null, status: 'GOOD', reason: null },
    ],
    backgroundStability: 'Static duplicate frames detected',
  },
  network: {
    status: 'STABLE',
    latencyMs: 38,
    latencyVarianceMs: 4,
    packetLossPercent: 0.0,
    heartbeatAgeSec: 3,
  },
  viewpoint: {
    status: 'STABLE',
    shiftScore: 0.0,
    detectedAt: null,
    shiftDetected: false,
    fenceConfidenceNote: null,
  },
  trends: [
    {
      metric: 'fps',
      label: 'FPS',
      direction: 'DEGRADING',
      deltaPercent: -100,
      window: '15 MIN',
      persistence: '2 min',
      series: [25, 25, 25, 12, 0, 0, 0, 0],
    },
  ],
  issues: [
    {
      issueId: 'ISS-CAM05-FZ-01',
      title: 'Frame frozen',
      impact: 'HIGH',
      firstSeen: iso(120_000),
      lastSeen: iso(5_000),
      count: 24,
      durationLabel: '2 min',
      impactNote: 'Surveillance stream is unresponsive',
      affectedModules: ['Live visibility', 'Virtual Fence', 'Detection', 'Tracking'],
    },
  ],
  operationalImpact: {
    level: 'COMPROMISED',
    coverage: 'COMPROMISED',
    affectedModules: ['Live visibility', 'Virtual Fence', 'Detection'],
    message: 'Live video frozen. Temporal observations halted.',
  },
  maintenance: {
    recommended: true,
    reason: 'RTSP encoder frozen — restart or encoder check needed',
    durationLabel: '2 min',
    impactNote: 'No live movement detectable',
  },
  lastKnown: {
    status: 'ONLINE',
    at: iso(120_000),
  },
}

const CAM_08: CameraHealth = {
  cameraId: 'CAM-08',
  status: 'STALE',
  statusReason: 'No fresh video frames received for 45 seconds (configured threshold: 30s).',
  lastUpdated: iso(45_000),
  source: 'DEMO',
  regionProfile: {
    configured: true,
    region: 'INDO-BHUTAN',
    terrain: 'HILLY / FOREST',
    location: 'Ridge patrol feed',
  },
  stream: {
    state: 'STALE',
    fps: 8,
    expectedFps: 25,
    frameDropPercent: 68.0,
    staleSeconds: 45,
    reconnectCount: 5,
  },
  image: {
    status: 'DEGRADED',
    metrics: [
      { metric: 'sharpness', label: 'Sharpness', value: 0.65, unit: 'ratio', status: 'DEGRADED', reason: 'High packet loss corruption' },
      { metric: 'brightness', label: 'Brightness', value: 0.60, unit: 'ratio', status: 'GOOD', reason: null },
    ],
    backgroundStability: 'Intermittent frames received',
  },
  network: {
    status: 'DEGRADED',
    latencyMs: 240,
    latencyVarianceMs: 95,
    packetLossPercent: 12.4,
    heartbeatAgeSec: 45,
  },
  viewpoint: {
    status: 'STABLE',
    shiftScore: 0.02,
    detectedAt: null,
    shiftDetected: false,
    fenceConfidenceNote: null,
  },
  trends: [
    {
      metric: 'packet-loss',
      label: 'Packet loss',
      direction: 'DEGRADING',
      deltaPercent: 120.0,
      window: '15 MIN',
      persistence: '45s',
      series: [1.2, 2.0, 4.5, 8.2, 12.4],
    },
  ],
  issues: [
    {
      issueId: 'ISS-CAM08-ST-01',
      title: 'Stream stale / packet loss',
      impact: 'HIGH',
      firstSeen: iso(45_000),
      lastSeen: iso(45_000),
      count: 9,
      durationLabel: '45s',
      impactNote: 'Tracking continuity degraded',
      affectedModules: ['Tracking', 'Live visibility'],
    },
  ],
  operationalImpact: {
    level: 'DEGRADED',
    coverage: 'DEGRADED',
    affectedModules: ['Tracking', 'Live visibility'],
    message: 'Frame delivery delayed. Tracking continuity degraded.',
  },
  maintenance: {
    recommended: false,
    reason: 'Transient network congestion',
    durationLabel: '45s',
    impactNote: 'Link recovery in progress',
  },
  lastKnown: {
    status: 'ONLINE',
    at: iso(60_000),
  },
}

const CAM_09: CameraHealth = {
  cameraId: 'CAM-09',
  status: 'MAINTENANCE',
  statusReason: 'Scheduled optical inspection & housing maintenance active.',
  lastUpdated: iso(2_000),
  source: 'DEMO',
  regionProfile: {
    configured: true,
    region: 'INDO-NEPAL',
    terrain: 'FOOTHILL / PLAINS',
    location: 'Sector HQ Gate feed',
  },
  stream: {
    state: 'CONNECTED',
    fps: 30,
    expectedFps: 30,
    frameDropPercent: 0.0,
    staleSeconds: 2,
    reconnectCount: 0,
  },
  image: {
    status: 'GOOD',
    metrics: [
      { metric: 'sharpness', label: 'Sharpness', value: 0.94, unit: 'ratio', status: 'GOOD', reason: null },
      { metric: 'brightness', label: 'Brightness', value: 0.82, unit: 'ratio', status: 'GOOD', reason: null },
    ],
    backgroundStability: 'Calibration target verified',
  },
  network: {
    status: 'STABLE',
    latencyMs: 22,
    latencyVarianceMs: 3,
    packetLossPercent: 0.0,
    heartbeatAgeSec: 1,
  },
  viewpoint: {
    status: 'STABLE',
    shiftScore: 0.01,
    detectedAt: null,
    shiftDetected: false,
    fenceConfidenceNote: null,
  },
  trends: [],
  issues: [
    {
      issueId: 'ISS-CAM09-MN-01',
      title: 'Scheduled maintenance active',
      impact: 'LOW',
      firstSeen: iso(45 * 60_000),
      lastSeen: iso(2_000),
      count: 1,
      durationLabel: '45 min',
      impactNote: 'Planned optical calibration',
      affectedModules: [],
    },
  ],
  operationalImpact: {
    level: 'NONE',
    coverage: 'NORMAL',
    affectedModules: [],
    message: 'Field technician performing routine maintenance. Camera operating nominally.',
  },
  maintenance: {
    recommended: false,
    reason: 'Routine optical calibration in progress',
    durationLabel: '45 min',
    impactNote: 'Expected completion within 30 min',
  },
  lastKnown: null,
}

const CAM_14: CameraHealth = {
  cameraId: 'CAM-14',
  status: 'ONLINE',
  statusReason: 'Camera hardware & stream healthy. Boundary coverage compromised due to severe atmospheric fog.',
  lastUpdated: iso(2_000),
  source: 'DEMO',
  regionProfile: {
    configured: true,
    region: 'INDO-BHUTAN',
    terrain: 'HILLY / FOREST',
    location: 'Dense ridge outpost feed',
  },
  stream: {
    state: 'CONNECTED',
    fps: 25,
    expectedFps: 25,
    frameDropPercent: 0.2,
    staleSeconds: 2,
    reconnectCount: 0,
  },
  image: {
    status: 'DEGRADED',
    metrics: [
      { metric: 'sharpness', label: 'Sharpness', value: 0.38, unit: 'ratio', status: 'DEGRADED', reason: 'Heavy fog attenuation' },
      { metric: 'brightness', label: 'Brightness', value: 0.42, unit: 'ratio', status: 'GOOD', reason: null },
      { metric: 'contrast', label: 'Contrast', value: 0.31, unit: 'ratio', status: 'DEGRADED', reason: 'Low visual dynamic range' },
    ],
    backgroundStability: 'Severe fog occlusion detected',
  },
  network: {
    status: 'STABLE',
    latencyMs: 35,
    latencyVarianceMs: 5,
    packetLossPercent: 0.1,
    heartbeatAgeSec: 2,
  },
  viewpoint: {
    status: 'STABLE',
    shiftScore: 0.03,
    detectedAt: null,
    shiftDetected: false,
    fenceConfidenceNote: null,
  },
  trends: [
    {
      metric: 'sharpness',
      label: 'Sharpness',
      direction: 'DEGRADING',
      deltaPercent: -45.0,
      window: '1 HR',
      persistence: '45 min',
      series: [0.82, 0.76, 0.65, 0.52, 0.42, 0.38],
    },
  ],
  issues: [
    {
      issueId: 'ISS-CAM14-FG-01',
      title: 'Atmospheric fog occlusion',
      impact: 'HIGH',
      firstSeen: iso(45 * 60_000),
      lastSeen: iso(2_000),
      count: 45,
      durationLabel: '45 min',
      impactNote: 'Border fence detection range compromised',
      affectedModules: ['Virtual Fence', 'Detection'],
    },
  ],
  operationalImpact: {
    level: 'DEGRADED',
    coverage: 'COMPROMISED',
    affectedModules: ['Virtual Fence', 'Detection'],
    message: 'Camera ONLINE but sector coverage COMPROMISED due to low visibility.',
  },
  maintenance: null,
  lastKnown: null,
}

export const MOCK_HEALTH: Record<string, CameraHealth> = {
  'CAM-07': CAM_07,
  'CAM-12': CAM_12,
  'CAM-19': CAM_19,
  'CAM-03': CAM_03,
  'CAM-05': CAM_05,
  'CAM-08': CAM_08,
  'CAM-09': CAM_09,
  'CAM-14': CAM_14,
}
