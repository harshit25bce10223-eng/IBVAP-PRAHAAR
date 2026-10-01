export const CHALLENGE_DURATION = 150
export type MissionId = 'compound' | 'person' | 'animal' | 'health' | 'vehicle'
export type FaultId = 'fog' | 'camera' | 'network'
export type Faults = Record<FaultId, boolean>
export type FaultStarts = Partial<Record<FaultId | 'cameraResume' | 'networkResume', number>>
export const emptyFaults: Faults = { fog: false, camera: false, network: false }
export const missions: { id: MissionId; title: string; subtitle: string; subject: string }[] = [
  {
    id: 'compound',
    title: 'Operation Blackout',
    subtitle: 'Night + fog + mixed targets + camera loss + network outage',
    subject: 'Mixed-target incident',
  },
  {
    id: 'person',
    title: 'Silent Intrusion',
    subtitle: 'Low visibility + person tracking + boundary dwell + uncertainty',
    subject: 'Person P-01',
  },
  {
    id: 'animal',
    title: 'Wildlife Decoy',
    subtitle: 'Animal crossing + person nearby + class-specific fence rules',
    subject: 'Animal A-01 / Person P-01',
  },
  {
    id: 'health',
    title: 'Blind Sector',
    subtitle: 'Blur + occlusion + frozen stream + camera recovery',
    subject: 'Camera maintenance',
  },
  {
    id: 'vehicle',
    title: 'Checkpoint Escape',
    subtitle: 'Ambiguous OCR + candidate match + vehicle-person association',
    subject: 'Vehicle V-01',
  },
]
export const acts = [
  { at: 0, name: 'Observe', description: 'Separate targets from distractions.' },
  { at: 25, name: 'Associate', description: 'Track candidates across usable cameras.' },
  { at: 45, name: 'Explain', description: 'Inspect fence dwell and contributing risk factors.' },
  { at: 65, name: 'Survive', description: 'Keep the coverage gap visible; retain local reports.' },
  { at: 100, name: 'Respond', description: 'Compare route exposure and request officer review.' },
  { at: 125, name: 'Verify', description: 'Inspect the record, then try changing its contents.' },
]
export function missionActs(mission: MissionId) {
  if (mission === 'health')
    return acts.map((act, i) => ({
      ...act,
      ...[
        { name: 'Baseline', description: 'Establish usable camera views and quality baselines.' },
        {
          name: 'Diagnose',
          description: 'CAM1 blur affects image usability; other regions remain visible.',
        },
        {
          name: 'Occlusion',
          description: 'Inspect blocked coverage without inventing an intrusion.',
        },
        {
          name: 'Retain',
          description: 'Freeze the stale view and queue local maintenance reports.',
        },
        {
          name: 'Recover',
          description: 'Confirm fresh frames and compare a maintenance visit route.',
        },
        {
          name: 'Verify',
          description: 'Review the fault chronology and verify its evidence payload.',
        },
      ][i],
    }))
  if (mission === 'animal')
    return acts.map((act, i) => ({
      ...act,
      ...[
        {
          name: 'Classify',
          description: 'Keep animal A-01 and person P-01 as separate object classes.',
        },
        {
          name: 'Separate',
          description: 'Record wildlife without raising a people-only intrusion alert.',
        },
        {
          name: 'Evaluate',
          description:
            'Person P-01 reaches the fence at T+52s; apply its dwell rule independently.',
        },
        {
          name: 'Preserve',
          description: 'Retain the person alert and animal exclusion through the camera outage.',
        },
        {
          name: 'Review',
          description: 'Show why the person requires review and wildlife does not.',
        },
        {
          name: 'Verify',
          description: 'Export both decisions with class labels and captured timestamps.',
        },
      ][i],
    }))
  if (mission === 'vehicle')
    return acts.map((act, i) => ({
      ...act,
      ...[
        {
          name: 'Detect',
          description: 'Track the vehicle and nearby person as separate entities.',
        },
        {
          name: 'Compare',
          description: 'Keep ambiguous plate candidates unresolved; inspect potential handoff.',
        },
        {
          name: 'Explain',
          description: 'Person dwell triggers review; a plate read alone does not.',
        },
        {
          name: 'Survive',
          description: 'Preserve candidate sightings while the exit camera loses coverage.',
        },
        {
          name: 'Respond',
          description: 'Compare route exposure before an officer makes a response choice.',
        },
        {
          name: 'Verify',
          description: 'Seal the snapshot and challenge its integrity by changing one field.',
        },
      ][i],
    }))
  return acts
}
export type ChallengeEvent = {
  at: number
  camera: string
  title: string
  detail: string
  kind: 'observation' | 'rule' | 'alert' | 'health' | 'field' | 'incident' | 'evidence' | 'route'
}
export const featureCatalog = [
  {
    id: 'detection',
    title: 'Object detection',
    module: 'C5',
    route: '/detections',
    note: 'Person, vehicle and animal labels with confidence.',
    stage: 8,
  },
  {
    id: 'tracking',
    title: 'Tracking & handoff',
    module: 'C6',
    route: '/track/TRK-1042',
    note: 'Track lifecycle, candidate continuity and visible gaps.',
    stage: 28,
  },
  {
    id: 'anpr',
    title: 'ANPR candidates',
    module: 'C7',
    route: '/anpr',
    note: 'Ambiguous plate reads remain candidates until reviewed.',
    stage: 20,
  },
  {
    id: 'fence',
    title: 'Virtual fence & dwell',
    module: 'PARAKH',
    route: '/virtual-fence',
    note: 'Entry, dwell and class-specific zone rules.',
    stage: 45,
  },
  {
    id: 'risk',
    title: 'Explainable risk',
    module: 'PARAKH',
    route: '/incident-intel',
    note: 'Visible factors; weak confidence requires human review.',
    stage: 48,
  },
  {
    id: 'animal',
    title: 'Human / animal filtering',
    module: 'SAKSHAM',
    route: '/field',
    note: 'Wildlife is recorded without automatically raising intrusion.',
    stage: 15,
  },
  {
    id: 'health',
    title: 'Camera health',
    module: 'C2',
    route: '/health',
    note: 'Blur, occlusion, freeze and coverage compromise.',
    stage: 60,
  },
  {
    id: 'correlation',
    title: 'Incident correlation',
    module: 'SUTRA',
    route: '/incident-intel',
    note: 'Related observations form one reviewable timeline.',
    stage: 55,
  },
  {
    id: 'gis',
    title: 'GIS & coverage',
    module: 'Digital Twin',
    route: '/gis',
    note: 'Camera regions, zones, entities and blind sectors.',
    stage: 0,
  },
  {
    id: 'offline',
    title: 'Offline store & forward',
    module: 'SAKSHAM',
    route: '/field',
    note: 'Local records queue and drain after reconnect.',
    stage: 68,
  },
  {
    id: 'route',
    title: 'Risk-aware routes',
    module: 'MARGDARSHAN',
    route: '/route-analysis',
    note: 'Compare exposure; no route is guaranteed safe.',
    stage: 100,
  },
  {
    id: 'evidence',
    title: 'Integrity & provenance',
    module: 'PRAMAAN',
    route: '/evidence',
    note: 'Real browser SHA-256 verification of the demo payload.',
    stage: 125,
  },
  {
    id: 'review',
    title: 'Officer review & audit',
    module: 'Human in the loop',
    route: '/events',
    note: 'Acknowledge or reject and record the operator action.',
    stage: 48,
  },
  {
    id: 'context',
    title: 'Night / weather / audio',
    module: 'PPT concept signals',
    route: null,
    note: 'Scripted environmental and sensor context; integrations illustrated.',
    stage: 12,
  },
]

function event(
  at: number,
  camera: string,
  title: string,
  detail: string,
  kind: ChallengeEvent['kind']
): ChallengeEvent {
  return { at, camera, title, detail, kind }
}
export function challengeAt(
  seconds: number,
  mission: MissionId,
  faults: Faults = emptyFaults,
  faultStarts: FaultStarts = {}
) {
  const time = Math.max(0, Math.min(CHALLENGE_DURATION, seconds))
  const healthOnly = mission === 'health'
  const vehicle = mission === 'compound' || mission === 'vehicle'
  const wildlife = mission === 'compound' || mission === 'animal'
  const fog = faults.fog || (mission !== 'vehicle' && time >= 12 && time < 90)
  const recoveryAt = Math.max(90, faultStarts.cameraResume ?? 90)
  const syncAt = Math.max(95, faultStarts.networkResume ?? 95)
  const cameraOffline = faults.camera || (time >= 60 && time < recoveryAt)
  const networkOffline = faults.network || (time >= 65 && time < syncAt)
  // Mixed-class wildlife case deliberately contrasts an excluded animal with a real person alert.
  const entry = healthOnly ? null : mission === 'animal' ? 52 : 45
  const dwell = entry === null ? 0 : Math.min(3, Math.max(0, time - entry))
  const intrusion = entry !== null && time >= entry + 3
  const confidence = fog ? 0.64 : 0.92
  const camera1Blur = healthOnly && time >= 12 && time < 30
  const camera1Occluded = time >= 40 && time < 90
  const factors = healthOnly
    ? []
    : [
        { label: 'Restricted-zone dwell', value: intrusion ? 35 : 0 },
        { label: 'Night movement', value: time >= 12 ? 10 : 0 },
        { label: 'Camera association candidate', value: time >= 28 ? 15 : 0 },
        { label: 'Vehicle-person proximity', value: vehicle && time >= 35 ? 15 : 0 },
        { label: 'Correlated boundary observation', value: intrusion && time >= 55 ? 10 : 0 },
      ]
  const risk = factors.reduce((sum, factor) => sum + factor.value, 0)
  // A high score is not independently corroborated critical evidence.
  const severity = risk >= 65 ? 'High' : risk >= 40 ? 'Medium' : 'Low'
  const all: ChallengeEvent[] = [
    event(
      0,
      'SECTOR-04',
      'Sector baseline established',
      'Three camera coverage regions mapped; route and zone layers available.',
      'observation'
    ),
  ]
  if (!healthOnly) {
    all.push(
      event(
        8,
        'CAM1',
        vehicle ? 'Vehicle and person detected' : 'Person detected',
        'Separate track IDs; class labels do not establish identity.',
        'observation'
      )
    )
    if (wildlife)
      all.push(
        event(
          15,
          'CAM1',
          'Animal crossing excluded',
          'A-01 is retained as an observation; people-only fence rule does not alert on it.',
          'rule'
        )
      )
    if (vehicle)
      all.push(
        event(
          20,
          'CAM1',
          'Ambiguous plate OCR',
          'DEMO 2026 / DEMO 2028 candidates; weak read held for review.',
          'observation'
        )
      )
    all.push(
      event(
        28,
        'CAM2',
        'Cross-camera continuation candidate',
        'Appearance and time window agree; unobserved gap remains explicit.',
        'observation'
      )
    )
    if (mission === 'compound')
      all.push(
        event(
          38,
          'SIMULATED AUDIO',
          'Audio anomaly candidate requires corroboration',
          'Scripted concept signal only; not an independently verified sensor.',
          'observation'
        )
      )
    if (vehicle)
      all.push(
        event(
          35,
          'CAM2',
          'Vehicle-person association',
          'Proximity and timing link observations; no driver identity inferred.',
          'observation'
        )
      )
    all.push(
      event(
        entry!,
        'CAM2',
        'Person enters restricted zone',
        'Dwell timer starts; configured threshold is three seconds.',
        'rule'
      ),
      event(
        entry! + 3,
        'CAM2',
        'Dwell rule requires operator review',
        'Explainable risk alert; simulated sensor context is not independent corroboration.',
        'alert'
      ),
      event(
        Math.max(55, entry! + 3),
        'SUTRA',
        'One incident timeline assembled',
        'Zone entry, dwell, track candidate and camera-quality context grouped.',
        'incident'
      )
    )
    all.push(
      event(
        entry! + 13,
        'CAM2',
        'Person leaves the marked zone',
        'Recorded three-second dwell alert remains available for review after exit.',
        'rule'
      )
    )
  }
  all.push(
    event(
      12,
      'CAM1',
      healthOnly ? 'Optical blur detected' : 'Low-light quality check',
      healthOnly
        ? 'Softened frame details reduce usability; a blur warning is distinct from connection loss.'
        : 'Night and weather are scripted challenge conditions; weak observations remain reviewable.',
      'health'
    ),
    event(
      40,
      'CAM1',
      'Occlusion warning',
      'Partial obstruction reduces usable coverage; another region still reports.',
      'health'
    ),
    event(
      60,
      'CAM3',
      'Stream frozen / coverage compromised',
      'Last usable frame marked stale; no fresh observations accepted in this region.',
      'health'
    ),
    event(
      65,
      'EDGE',
      'Uplink interrupted',
      'Local reports retained; central delivery is pending.',
      'field'
    ),
    event(68, 'EDGE', 'Local observation saved', 'Record 01 queued with capture time.', 'field'),
    event(
      74,
      'EDGE',
      'Second local report saved',
      'Record 02 retained; upload is not mistaken for capture time.',
      'field'
    ),
    event(
      82,
      'EDGE',
      'Third local report saved',
      'Record 03 retained while central link is unavailable.',
      'field'
    )
  )
  const cameraFaultAt = faultStarts.camera ?? 0
  const networkFaultAt = faultStarts.network ?? 0
  if (!faults.camera || cameraFaultAt > recoveryAt) {
    all.push(
      event(
        recoveryAt,
        'CAM3',
        'Fresh stream recovered',
        'Capture clock advances again. Outage interval remains in the timeline.',
        'health'
      )
    )
    if (!healthOnly && (!faults.camera || cameraFaultAt > recoveryAt + 4))
      all.push(
        event(
          recoveryAt + 4,
          'CAM3',
          'Target reacquired after gap',
          'New observation resumes candidate continuity; missing movement was not reconstructed.',
          'observation'
        )
      )
  }
  if (!faults.network || networkFaultAt > syncAt)
    all.push(
      event(
        syncAt,
        'EDGE',
        'Uplink restored',
        'Queued records begin store-and-forward synchronization.',
        'field'
      )
    )
  if (!faults.network || networkFaultAt >= syncAt + 4)
    all.push(
      event(
        syncAt + 4,
        'EDGE',
        'Three records synchronized',
        'Capture timestamps preserved; retransmission duplicates suppressed in this simulation.',
        'field'
      )
    )
  all.push(
    event(
      100,
      'MARGDARSHAN',
      'Response routes compared',
      'Route exposure reflects current visibility and coverage faults. Officer chooses.',
      'route'
    ),
    event(
      125,
      'PRAMAAN',
      'Demo evidence payload available',
      'Local SHA-256 integrity check can be run; no external ledger transaction is claimed.',
      'evidence'
    )
  )
  if (faults.camera)
    all.push(
      event(
        cameraFaultAt,
        'JUDGE CONTROL',
        'Camera failure held active',
        'CAM3 remains unavailable until the injected fault is cleared.',
        'health'
      )
    )
  if (faults.network)
    all.push(
      event(
        networkFaultAt,
        'JUDGE CONTROL',
        'Network failure held active',
        'New uploads pause while the injected uplink is down; earlier syncs remain recorded.',
        'field'
      )
    )
  const events = all.filter(e => e.at <= time).sort((a, b) => a.at - b.at)
  const captured = [68, 74, 82].filter(at => time >= at).length
  const syncTime = faults.network ? Math.min(time, networkFaultAt) : time
  const synced =
    syncTime >= syncAt + 4
      ? captured
      : syncTime >= syncAt
        ? Math.min(captured, Math.floor(syncTime - syncAt))
        : 0
  const routes = [
    {
      id: 'A',
      name: 'Direct perimeter',
      distance: '1.2 km',
      minutes: 4,
      exposure: 25 + (cameraOffline ? 35 : 0) + (fog ? 20 : 0),
      reason: cameraOffline
        ? 'Crosses compromised CAM3 coverage'
        : fog
          ? 'Visibility reduced along perimeter'
          : 'Shorter route; perimeter exposure remains',
    },
    {
      id: 'B',
      name: 'Covered service road',
      distance: '1.8 km',
      minutes: 6,
      exposure: 18 + (fog ? 10 : 0),
      reason: 'Longer approach with usable CAM2 coverage',
    },
  ]
  const steps = missionActs(mission)
  const act = [...steps].reverse().find(a => time >= a.at) ?? steps[0]
  return {
    time,
    mission,
    healthOnly,
    vehicle,
    wildlife,
    fog,
    cameraOffline,
    networkOffline,
    confidence,
    camera1Blur,
    camera1Occluded,
    entry,
    dwell,
    intrusion,
    risk,
    severity,
    factors,
    events,
    captured,
    synced,
    queued: captured - synced,
    routes,
    act,
    lastFrameAt: faults.camera
      ? Math.min(time, cameraFaultAt >= 90 ? cameraFaultAt : Math.min(cameraFaultAt, 60))
      : 60,
    animalExcluded: wildlife && time >= 15,
    lowConfidence: !healthOnly && confidence < 0.75,
    continuity:
      cameraOffline && time >= (entry ?? 45) + 14
        ? 'GAP · NO LIVE OBSERVATION'
        : time >= recoveryAt + 4
          ? 'REACQUIRED · CANDIDATE'
          : time >= 28
            ? 'CAM2 · ASSOCIATION CANDIDATE'
            : time >= 8
              ? 'CAM1 · ACTIVE'
              : 'TENTATIVE',
  }
}
export type ChallengeState = ReturnType<typeof challengeAt>

export async function sha256(text: string) {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('')
}
