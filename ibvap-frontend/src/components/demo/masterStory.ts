import { backendRiskReplay } from './backendRiskReplay'

export const MASTER_DURATION = 480
export const ENTITY_ID = 'X42'
export const INCIDENT_ID = 'INC-1042'
export const EVIDENCE_ID = 'EVD-5521'
export type StoryView =
  | 'hook'
  | 'overview'
  | 'ingestion'
  | 'trust'
  | 'night'
  | 'detection'
  | 'animal'
  | 'tracking'
  | 'behavior'
  | 'fence'
  | 'anpr'
  | 'reid'
  | 'departure'
  | 'transfer'
  | 'followcars'
  | 'why'
  | 'face'
  | 'audio'
  | 'weather'
  | 'uncertainty'
  | 'health'
  | 'correlation'
  | 'risk'
  | 'review'
  | 'offline'
  | 'hash'
  | 'sync'
  | 'evidence'
  | 'security'
  | 'gis'
  | 'heatmap'
  | 'route'
  | 'mobile'
  | 'integration'
  | 'investigation'
  | 'rejected'
  | 'graph'
  | 'risktrail'
  | 'coverage'
  | 'sop'
  | 'replay'
  | 'relationship'
  | 'closing'
export type DeliveryStatus = 'LIVE' | 'REPLAY TEST' | 'INTEGRATION READY' | 'PLANNED EXTENSION'
export type StoryStep = {
  id: StoryView
  at: number
  title: string
  module: string
  question: string
  narration: string
  output: string
  status: DeliveryStatus
}
const step = (
  id: StoryView,
  at: number,
  title: string,
  module: string,
  question: string,
  narration: string,
  output: string,
  status: DeliveryStatus = 'REPLAY TEST'
): StoryStep => ({ id, at, title, module, question, narration, output, status })
export const masterSteps: StoryStep[] = [
  step(
    'hook',
    0,
    'One camera. One complete story.',
    'PRAHAAR',
    'What does an intelligence layer add to CCTV?',
    'One incident will take us from a camera observation to an explainable decision and verifiable evidence. The same identifiers connect every layer.',
    'A connected incident, from first observation to investigation.'
  ),
  step(
    'overview',
    20,
    'A remote border post at 23:14',
    'Command view',
    'What is happening in this sector?',
    'The officer starts with cameras, entities, zones and surveillance health in one workspace. Forest terrain, low light and intermittent connectivity form the challenge.',
    'One shared sector with four camera regions.'
  ),
  step(
    'ingestion',
    30,
    'Existing camera → timestamped frames',
    'Ingestion',
    'How did the camera observation enter the system?',
    'This synthetic replay models camera IDs, capture timestamps and a frame queue. The repository has no recorded RTSP footage for this story, so this view is explicitly a replay test.',
    'CAM-01 → capture time → replay frame queue.'
  ),
  step(
    'trust',
    42,
    'Check the feed before trusting it',
    'Feed trust',
    'Is this incoming frame trustworthy?',
    'A controlled repeated-frame interval is flagged suspicious. Target observations pause until the replay feed recovers; the trust warning remains part of the context.',
    'Possible freeze → suspicious feed → restored input.'
  ),
  step(
    'night',
    52,
    'Darkness is part of the pipeline',
    'Night processing',
    'What changes when visibility falls?',
    'Compare the raw and enhanced schematic. This illustrates preprocessing before detection; it does not claim a live Zero-DCE or thermal inference result.',
    'Raw view → illustrative enhancement → detection.'
  ),
  step(
    'detection',
    60,
    'Deer. Vehicle. Person.',
    'C5 · Detection',
    'What did the camera see?',
    'The deer appears first, followed by a vehicle and then a person exiting it. Class labels describe observations; presence alone does not trigger an intrusion.',
    'A-008 / V-042 / person observation.'
  ),
  step(
    'animal',
    75,
    'Movement is not automatically a threat',
    'Human / animal',
    'Why is wildlife not treated as an intrusion?',
    'The people-only fence rule excludes the deer and retains its observation. A nearby person receives an independent track candidate. Exclusion is a configured rule, not a universal claim about animals.',
    'Animal context retained; person evaluated independently.'
  ),
  step(
    'tracking',
    100,
    'The observation gets memory',
    'C6 · Tracking',
    'How do repeated detections become one track?',
    'CAM-01 maintains TRK-017 with first seen, duration and position. Tracking describes continuity within a camera and provides input to association and event processing.',
    'PERSON → TRK-017 → position + duration.'
  ),
  step(
    'behavior',
    130,
    'The boundary has not been crossed yet',
    'Behavior context',
    'What signal appears before a fence event?',
    'TRK-017 has spent 52 seconds near the boundary and moved repeatedly along it. This controlled long-dwell signal provides context without asserting intent.',
    '52s boundary dwell · behavioral signal only.'
  ),
  step(
    'fence',
    145,
    'A spatial rule creates an event',
    'PARAKH · Fence',
    'When does the configured zone rule trigger?',
    'The same track enters the polygon and remains for three seconds. EVT-2291 records the crossing and dwell condition, with the track and capture time attached.',
    'TRK-017 → restricted polygon → EVT-2291.'
  ),
  step(
    'anpr',
    160,
    'The vehicle becomes investigation context',
    'C7 · ANPR',
    'Which vehicle observation belongs to this story?',
    'Six scripted plate observations vote for MP09AB1234 at 91% test confidence. Plate context links to V-042; it does not identify the person or prove who was driving.',
    'V-042 → 6 observations → MP09AB1234.'
  ),
  step(
    'departure',
    170,
    'Car 1 takes Path B',
    'Vehicle tracking',
    'Where did the first car go?',
    'V-042 leaves the checkpoint along Path B. The person keeps TRK-017 independently. A vehicle departure does not end the person track.',
    'Car 1 → Path B; person → CAM-02.'
  ),
  step(
    'reid',
    190,
    'Two local tracks. One candidate entity.',
    'Cross-camera association',
    'What connects the next camera observation?',
    'CAM-02 calls its local track TRK-044. Appearance, time and spatial plausibility support a candidate association to CAM-01 / TRK-017 under X42. The 85% replay score is not guaranteed identity.',
    'TRK-017 → candidate X42 ← TRK-044.'
  ),
  step(
    'transfer',
    205,
    'The person gets into Car 2',
    'Person + vehicle links',
    'Can we follow the person after a car change?',
    'In this controlled replay, X42 walks to V-077 and gets inside. A boarding observation links the person to the second car without making the two vehicle identities the same. Car 1 remains on Path B; the person’s location is now carried by Car 2 and labelled inferred.',
    'V-042 → person X42 → V-077; both cars stay separate.'
  ),
  step(
    'why',
    209,
    'Show why the association is plausible',
    'Association explanation',
    'What is behind that 85% score?',
    'Inspect appearance similarity, the 56-second transition window, adjacent camera locations and object type. The score is backed by visible replay inputs and explicit uncertainty.',
    'Appearance HIGH · temporal PASS · spatial PASS.'
  ),
  step(
    'rejected',
    211,
    'A plausible-looking candidate can still fail',
    'Re-ID rejection fixture',
    'Why was the other candidate kept out?',
    'CAM-05 / TRK-081 is a controlled impossible-transition fixture: 4.8 km in 12 seconds, or 400 m/s. It is excluded from this replay association. This fixture rejection is not presented as a live model result.',
    'Rejected fixture candidate · does not join X42.'
  ),
  step(
    'followcars',
    213,
    'Follow both cars after boarding',
    'Connected vehicle trace',
    'Where are the person and both cars now?',
    'Car 1 keeps V-042 on Path B. Car 2 keeps V-077 as it moves away, with X42 linked by the boarding observation. Both cars and the person remain searchable under the same incident.',
    'Car 1 on Path B; X42 linked to moving Car 2.'
  ),
  step(
    'face',
    215,
    'A crop without a name',
    'Face quality concept',
    'Was a usable face observation available?',
    'A masked illustrative crop shows the planned face-localization and quality workflow. No face model ran here, and no watchlist match or personal identity is claimed.',
    'Face localization design · policy-controlled crop.',
    'PLANNED EXTENSION'
  ),
  step(
    'audio',
    223,
    'Another source of possible context',
    'Audio concept',
    'What nonvisual signal could contribute?',
    'A configured impulse is introduced as a controlled test event. No microphone or validated audio classifier is connected; the replay signal cannot count as independent live corroboration.',
    'Configured audio anomaly · controlled input.'
  ),
  step(
    'weather',
    230,
    'Interpret observations in their environment',
    'Weather context',
    'Why should confidence change in fog?',
    'The controlled fog input reduces test observation confidence. Environmental context accompanies the observation rather than silently changing the officer’s conclusion.',
    'FOG / LOW VISIBILITY → confidence context.'
  ),
  step(
    'uncertainty',
    240,
    'Show how much to trust the observation',
    'Uncertainty',
    'How reliable is the available evidence?',
    'This replay observation combines 72% detection confidence, reduced image quality and high occlusion into a medium trust state. An officer sees the limitation instead of an invented certainty.',
    '72% detection · image quality LOW · trust MEDIUM.'
  ),
  step(
    'health',
    250,
    'The surveillance system watches itself',
    'C2 · Camera health',
    'Where is coverage compromised?',
    'CAM-03 degrades to a scripted 4.1 FPS and then loses its stream. Its last frame is stale. Other views continue, while the unobserved region remains visibly marked.',
    'CAM-03 → degraded / stale → coverage compromised.'
  ),
  step(
    'correlation',
    260,
    'Scattered signals become one incident',
    'SUTRA · C4',
    'Why do these observations belong together?',
    'Vehicle context, the person track, behavioral dwell, zone event and candidate handoff share time, location and entity links. Audio remains labeled test context. One inspectable timeline becomes INC-1042.',
    'Related observations → one contextual INC-1042.'
  ),
  step(
    'graph',
    272,
    'Every link has a reason',
    'SUTRA · Relationships',
    'What does each graph edge mean?',
    'Inspect proximity, track continuity, zone entry and candidate association. The graph links actual replay records. Animal observations remain outside the intrusion graph; face and audio carry their concept/test labels.',
    'Observation relationships → INC-1042.'
  ),
  step(
    'risk',
    280,
    'The risk score shows its reasons',
    'PARAKH · Risk',
    'Why did this incident receive this score?',
    'The canonical backend scorer produces 74/100 under the degraded fixture: zone crossing, night, human class and 72% confidence. Candidate cross-camera association is not confirmed identity and earns no confirmation points. Behavior stays visible context, not an invented extra weight.',
    '74 / 100 backend replay risk · visible factors · human review.'
  ),
  step(
    'risktrail',
    292,
    'The configured backend factors remain visible',
    'Risk decision trail',
    'Can the score be traced to the scorer?',
    'These are exported outputs of the canonical backend calculate_risk function using checked-in defaults. Candidate Re-ID is not passed as confirmed multi-camera identity. The UI does not invent a 90-point score to match a slide.',
    'Actual backend replay factors · source provenance.'
  ),
  step(
    'review',
    300,
    'An ambiguous candidate stays separate',
    'Officer review',
    'What happens when the match is only 61%?',
    'A second candidate is intentionally ambiguous. Review or keep it separate. Keeping it separate does not contaminate X42 or remove the primary candidate association.',
    '61% secondary candidate → human decision.'
  ),
  step(
    'offline',
    320,
    'The network goes away. Context remains.',
    'SAKSHAM',
    'What survives the network outage?',
    'Seven controlled metadata events and three evidence payloads enter the local replay buffer. Essential metadata is prioritized. The camera outage and uplink outage are distinct conditions.',
    '7 metadata events / 3 evidence payloads queued.'
  ),
  step(
    'hash',
    340,
    'Fingerprint evidence while offline',
    'PRAMAAN · SHA-256',
    'Can integrity processing continue locally?',
    'The browser computes actual SHA-256 hashes for three frozen replay payloads. They remain pending delivery while the simulated uplink is down. Local hashing does not imply a blockchain transaction.',
    'Actual local hashes → pending replay delivery.',
    'LIVE'
  ),
  step(
    'sync',
    365,
    'Reconnect with capture times preserved',
    'SAKSHAM · Sync',
    'What happens to the queued records?',
    'The controlled link returns. The replay buffer drains and retains original capture timestamps. Synced counts describe local simulation records, not external ledger anchors.',
    '7/7 replay events delivered · 3/3 replay payloads delivered.'
  ),
  step(
    'evidence',
    385,
    'Verify bytes. Expose the ledger boundary.',
    'PRAMAAN · Integrity',
    'Does the record still match its fingerprint?',
    'Recompute the frozen payload digest, alter one field and compare again. SHA-256 runs for real locally. The permissioned Fabric anchor remains a planned extension; no transaction ID is invented.',
    'Original MATCH → altered MISMATCH → restored MATCH.',
    'LIVE'
  ),
  step(
    'security',
    397,
    'Security surrounds the story',
    'Access & audit',
    'Who is allowed to review the evidence?',
    'Inspect a replay role check and local audit trail. X.509 authentication and TLS are deployment controls; this screen does not certify the demo transport or pretend a device certificate was verified.',
    'Role decision + review audit; deployment checks labeled.'
  ),
  step(
    'gis',
    410,
    'The same incident becomes spatial',
    'Digital Twin',
    'Where did these linked observations occur?',
    'The sector view shows X42, the zone, INC-1042 and camera coverage. Dashed connections indicate candidate sequence and an observation gap, not a continuously measured route.',
    'Same X42 + INC-1042 on one sector map.'
  ),
  step(
    'heatmap',
    425,
    'An incident becomes part of a pattern',
    'Historical analysis',
    'Where is recurring activity concentrated?',
    'A seven-day fixture illustrates repeated activity near Zone A and weak coverage near CAM-03. The heatmap is a controlled historical test dataset, not real border history.',
    '7-day replay fixtures → activity + coverage layer.'
  ),
  step(
    'coverage',
    433,
    'See the blind sector on the map',
    'Coverage context',
    'Where are the surveillance limitations?',
    'CAM-03 stays visibly compromised while CAM-01, CAM-02 and CAM-04 retain their replay status. The map shows the surveillance gap alongside incident activity.',
    'Activity and coverage are separate layers.'
  ),
  step(
    'route',
    440,
    'Intelligence supports a route decision',
    'MARGDARSHAN',
    'Which approach has lower modeled exposure?',
    'Compare illustrative routes using current alerts, historical activity, terrain and coverage. Route B has lower modeled exposure and a longer approach. Neither route is guaranteed safe.',
    'Route A / Route B → officer chooses.'
  ),
  step(
    'mobile',
    452,
    'Give the field officer useful context',
    'SSB alert concept',
    'What does the field officer receive?',
    'The in-browser mobile preview uses the same INC-1042, entity, zone and reasons. Acknowledgement is a local demo action. No notification is sent to a real device.',
    'INC-1042 → contextual field preview → local acknowledgement.'
  ),
  step(
    'sop',
    457,
    'Operational procedures belong to the deployment',
    'SOP concept',
    'Is an approved procedure connected?',
    'No deployment-approved SOP is connected in this prototype. The field preview preserves the context and officer actions without inventing tactical instructions.',
    'Approved SOP integration not connected.',
    'PLANNED EXTENSION'
  ),
  step(
    'integration',
    461,
    'Connect through structured interfaces',
    'C2 concept',
    'Can an existing command system consume the incident?',
    'Inspect the local structured event envelope. REST endpoints exist in the repository, but no C2 receiver is connected here. MQTT, ONVIF and live WebSocket delivery are not asserted.',
    'Structured demo JSON; external receiver not connected.'
  ),
  step(
    'investigation',
    470,
    'Follow the entity back to its evidence',
    'Investigation',
    'How can the connected proof be retrieved?',
    'Search the deterministic local incident records by X42, INC-1042, a track ID or plate. The result preserves camera, event, incident and evidence links. This is a fixture query, not a general natural-language AI search.',
    'X42 → observations → INC-1042 → EVD-5521.'
  ),
  step(
    'replay',
    475,
    'Replay the connected incident',
    'Investigation replay',
    'Can we follow the saved sequence again?',
    'Use Replay Incident to retrace the same entity, tracks, zone event, candidate association and evidence references. Capture timestamps remain attached to each local fixture record.',
    'Same identifiers · same observations · reproducible replay.'
  ),
  step(
    'relationship',
    477,
    'A chain with useful outputs',
    'System relationships',
    'How did each layer feed the next?',
    'The relationship view follows input, trust, detection, tracking, association, correlation, decision support and evidence, with outputs to GIS, field preview and investigation. It uses this incident’s actual replay identifiers.',
    'Observation → context → incident → verifiable local record.'
  ),
  step(
    'closing',
    478,
    'One contextual incident. One verifiable record.',
    'PRAHAAR',
    'What did the intelligence layer add?',
    'One camera observation became a track, an association candidate, a spatial event, an explainable incident and locally verifiable evidence. Coverage gaps and uncertainty stayed visible; the officer stayed in control.',
    'One entity · multiple cameras · one connected story.'
  ),
]
export type MasterEvent = {
  id: string
  at: number
  capture: number
  camera: string
  title: string
  type: string
  entity: string
  incident: string
  detail: string
  status: DeliveryStatus
}
const observation = (
  id: string,
  at: number,
  capture: number,
  camera: string,
  title: string,
  type: string,
  detail: string,
  entity = ENTITY_ID
): MasterEvent => ({
  id,
  at,
  capture,
  camera,
  title,
  type,
  detail,
  entity,
  incident: INCIDENT_ID,
  status: 'REPLAY TEST',
})
export const masterEvents: MasterEvent[] = [
  observation(
    'HEALTH-001',
    42,
    2,
    'CAM-01',
    'Repeated-frame input flagged',
    'feed',
    'Suspicious test input; fresh observations temporarily paused.',
    ''
  ),
  observation(
    'HEALTH-002',
    52,
    3,
    'CAM-01',
    'Feed trust restored',
    'feed',
    'Fresh replay frames resume.',
    ''
  ),
  observation(
    'OBS-A008',
    63,
    4,
    'CAM-01',
    'Deer detected',
    'animal',
    'People-only fence rule excludes this animal.',
    'A-008'
  ),
  observation(
    'OBS-V042',
    70,
    8,
    'CAM-01',
    'Vehicle V-042 detected',
    'vehicle',
    'Vehicle appears at entry checkpoint.',
    'V-042'
  ),
  observation(
    'OBS-P017',
    80,
    12,
    'CAM-01',
    'Person exits near vehicle',
    'person',
    'Proximity creates candidate context, not driver identity.'
  ),
  observation(
    'TRK-017',
    100,
    19,
    'CAM-01',
    'TRK-017 becomes active',
    'track',
    'Persistent camera-local track attached to the person.'
  ),
  observation(
    'BEH-071',
    130,
    71,
    'CAM-01',
    '52-second boundary dwell',
    'behavior',
    'Long dwell and boundary hovering; intent remains unknown.'
  ),
  observation(
    'EVT-2291',
    145,
    122,
    'CAM-01',
    'Restricted-zone entry',
    'zone',
    'Tracked point enters Zone A; three-second dwell begins.'
  ),
  observation(
    'EVT-2292',
    148,
    125,
    'CAM-01',
    'Three-second zone dwell confirmed',
    'zone',
    'Zone rule is met; operator review required.'
  ),
  observation(
    'ANPR-042',
    160,
    140,
    'CAM-01',
    'MP09AB1234 plate context',
    'plate',
    'Six scripted reads vote for the plate; no driver identity.',
    'V-042'
  ),
  observation(
    'REID-042',
    190,
    178,
    'CAM-02',
    'TRK-044 candidate association',
    'association',
    '85% replay confidence; appearance, time and spatial tests support X42.'
  ),
  observation(
    'FACE-042',
    215,
    190,
    'CAM-02',
    'Face-quality workflow illustrated',
    'concept',
    'Masked placeholder only; no face model was run.'
  ),
  observation(
    'AUD-184',
    223,
    184,
    'AUDIO TEST',
    'Configured impulse test event',
    'audio',
    'Controlled replay context; no live microphone or gunshot verdict.'
  ),
  observation(
    'WEATHER-042',
    230,
    200,
    'WEATHER TEST',
    'Visibility reduced',
    'weather',
    'Controlled fog input affects observation confidence.'
  ),
  observation(
    'QUALITY-042',
    240,
    206,
    'CAM-02',
    'Observation trust: medium',
    'uncertainty',
    '72% confidence, low quality and high occlusion.'
  ),
  observation(
    'HEALTH-003',
    250,
    210,
    'CAM-03',
    'Coverage compromised',
    'health',
    '4.1 FPS fixture; last frame stale after stream loss.',
    ''
  ),
  observation(
    INCIDENT_ID,
    260,
    220,
    'SUTRA',
    'Signals correlated into INC-1042',
    'incident',
    'Time, entity and spatial links remain inspectable.'
  ),
  observation(
    'RISK-1042',
    280,
    228,
    'PARAKH',
    'Backend replay risk: 74 / 100',
    'risk',
    'Canonical backend defaults; candidate association is not counted as confirmed identity.'
  ),
  observation(
    'AMB-061',
    300,
    230,
    'CAM-02',
    'Secondary candidate is ambiguous',
    'review',
    '61% score; stays separate unless reviewed.',
    'CANDIDATE-061'
  ),
  observation(
    'NET-242',
    320,
    242,
    'EDGE',
    'Uplink lost',
    'network',
    'Seven metadata fixtures and three evidence fixtures retained locally.',
    ''
  ),
  observation(
    'EVD-LOCAL',
    340,
    250,
    'EDGE',
    'Evidence payloads ready for hashing',
    'evidence',
    'Actual SHA-256 can run locally while replay delivery is offline.'
  ),
  observation(
    'NET-278',
    365,
    278,
    'EDGE',
    'Replay uplink restored',
    'network',
    'Buffered fixtures begin simulated delivery; capture time preserved.',
    ''
  ),
]
masterEvents.push(
  observation(
    'MOVE-V042',
    170,
    151,
    'CAM-04',
    'Car 1 takes Path B',
    'vehicle-move',
    'V-042 continues on Path B. X42 is outside this vehicle.',
    'V-042'
  ),
  observation(
    'OBS-V077',
    192,
    180,
    'CAM-02',
    'Car 2 arrives',
    'vehicle',
    'V-077 / DL08CD5678 approaches the person. Vehicle identities stay separate.',
    'V-077'
  ),
  observation(
    'BOARD-X42',
    205,
    193,
    'CAM-02',
    'X42 boards Car 2',
    'boarding',
    'Controlled boarding observation links X42 to V-077. No personal identity is claimed.'
  ),
  observation(
    'MOVE-V077',
    212,
    200,
    'CAM-02',
    'Car 2 moves with the person',
    'vehicle-move',
    'V-077 moves; X42 location is inferred from the boarding link, not a fresh person detection.',
    'V-077'
  )
)
export function masterClock(seconds: number) {
  const total = 23 * 3600 + 14 * 60 + Math.floor(seconds)
  return [Math.floor(total / 3600) % 24, Math.floor(total / 60) % 60, total % 60]
    .map(n => String(n).padStart(2, '0'))
    .join(':')
}
// Separate camera observations from the person's inferred location inside a car.
export function vehicleJourney(time: number) {
  const progress = Math.max(0, Math.min(1, (time - 170) / 70))
  const first =
    time < 170
      ? { x: Math.min(192, 100 + (time - 70) * 9.2), y: 355 }
      : progress < 0.25
        ? { x: 192, y: 355 + progress * 224 }
        : { x: 192 + ((progress - 0.25) / 0.75) * 510, y: 411 }
  const secondVisible = time >= 192
  const second =
    time < 205
      ? { x: 660, y: Math.max(255, 355 - (time - 192) * 12.5) }
      : {
          x: 660 + Math.min(75, Math.max(0, time - 212) * 2),
          y: 255 + Math.min(100, Math.max(0, time - 212) * 3),
        }
  return {
    first,
    second,
    secondVisible,
    boarded: time >= 205,
    secondMoving: time >= 212,
    firstMoving: time >= 170 && time < 240,
  }
}
export function masterAt(
  seconds: number,
  forced: { network: boolean; camera: boolean; fog: boolean } = {
    network: false,
    camera: false,
    fog: false,
  }
) {
  const time = Math.max(0, Math.min(MASTER_DURATION, seconds))
  const current = [...masterSteps].reverse().find(s => s.at <= time) ?? masterSteps[0]
  const events = masterEvents.filter(e => e.at <= time).sort((a, b) => a.capture - b.capture)
  const freeze = time >= 42 && time < 52
  const cameraOffline = forced.camera || time >= 250
  const fog = forced.fog || (time >= 230 && time < 365)
  const networkOffline = forced.network || (time >= 320 && time < 365)
  const capture = events.reduce((latest, e) => Math.max(latest, e.capture), 0)
  const journey = vehicleJourney(time)
  const position =
    time < 80
      ? { x: 120, y: 355 }
      : time < 100
        ? { x: 192 + (time - 80) * 3, y: 335 }
        : time < 130
          ? { x: 252 + (time - 100) * 4, y: 310 }
          : time < 145
            ? { x: 380 + Math.sin((time - 130) * 0.8) * 14, y: 296 }
            : time < 175
              ? { x: 430 + (time - 145) * 5, y: 282 - Math.min(72, (time - 145) * 5) }
              : time < 190
                ? null
                : time < 205
                  ? { x: 612 + (time - 190) * 3.2, y: 218 + (time - 190) * 2.46 }
                  : journey.second
  const riskCase = backendRiskReplay.cases[time >= 230 || forced.fog ? 'degraded' : 'clear']
  const factors =
    time >= 148
      ? riskCase.result.factors.map(f => ({
          label: f.label,
          value: f.points,
          evidence: f.evidence,
          code: f.code,
        }))
      : []
  const risk = time >= 148 ? riskCase.result.risk_score : 0
  const confidence = fog || time >= 240 ? 0.72 : 0.94
  return {
    time,
    current,
    events,
    capture,
    freeze,
    cameraOffline,
    networkOffline,
    fog,
    position,
    journey,
    factors,
    risk,
    riskSource: backendRiskReplay.provenance,
    confidence,
    animal: time >= 63,
    vehicle: time >= 70,
    person: time >= 80,
    tracking: time >= 100,
    behavior: time >= 130,
    crossed: time >= 145,
    dwell: Math.min(3, Math.max(0, time - 145)),
    alert: time >= 148,
    plate: time >= 160,
    associated: time >= 190,
    gap: time >= 175 && time < 190,
    incident: time >= 260,
    uncertainCandidate: time >= 300,
  }
}
export type MasterState = ReturnType<typeof masterAt>
export function searchMasterEvents(events: MasterEvent[], query: string, after = 0) {
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  return events.filter(
    e =>
      e.capture >= after &&
      terms.every(term =>
        `${e.entity} ${e.incident} ${e.id} ${e.camera} ${e.title} ${e.type} ${e.detail}`
          .toLowerCase()
          .includes(term)
      )
  )
}
export function replayEvidencePayloads(events: MasterEvent[]) {
  return [0, 1, 2].map(index =>
    JSON.stringify(
      {
        simulation: true,
        replay: 'PRAHAAR master incident',
        evidenceId: index === 0 ? EVIDENCE_ID : `EVD-${5521 + index}`,
        incidentId: INCIDENT_ID,
        entityId: ENTITY_ID,
        captureTimezone: 'Asia/Kolkata',
        mediaSource: 'SYNTHETIC SCHEMATIC; NO RECORDED MEDIA ATTACHED',
        eventRecords: events.filter(
          e =>
            e.at <= 340 &&
            (index === 0 ||
              (index === 1
                ? ['zone', 'behavior'].includes(e.type)
                : ['association', 'uncertainty'].includes(e.type)))
        ),
      },
      null,
      2
    )
  )
}
