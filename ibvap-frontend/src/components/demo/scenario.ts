export const DEMO_DURATION = 120
export const DEMO_PLATE = 'DEMO 2026'
export const DEMO_VEHICLE = 'DEMO-CAR-01'

export type ScenarioId = 'vehicle' | 'person' | 'animal' | 'health'
export const scenarios = [
  { id: 'vehicle' as const, title: 'Vehicle & plate trail', subject: 'DEMO-CAR-01', summary: 'Plate reading → camera matches → restricted-zone alert', outcome: 'Trace sightings by plate and capture time.' },
  { id: 'person' as const, title: 'Person enters a restricted area', subject: 'DEMO-PERSON-01', summary: 'Person detection → movement tracking → fence breach', outcome: 'Explain an intrusion without claiming a person’s identity.' },
  { id: 'animal' as const, title: 'Animal crosses the perimeter', subject: 'DEMO-ANIMAL-01', summary: 'Animal classification → zone rule → no intrusion alert', outcome: 'See how a configured rule avoids an unnecessary alert.' },
  { id: 'health' as const, title: 'Camera blur & connection loss', subject: 'DEMO-CAMERA-12', summary: 'Image degradation → stale frame → recovery → maintenance', outcome: 'Show when a view cannot be trusted and how it recovers.' },
]

export function defaultScenario(path: string): ScenarioId {
  if (path === '/health' || path === '/camera-health') return 'health'
  if (path === '/field') return 'animal'
  if (path === '/virtual-fence' || path.startsWith('/track/')) return 'person'
  return 'vehicle'
}

export const chapters = [
  { id: 'detection', name: 'Spot the vehicle', module: 'Detection', at: 0, route: '/detections', question: 'What is in the camera view?', explanation: 'A white car enters the checkpoint. A box follows it and the system labels it as a vehicle. Detection describes an object; it does not establish a threat.', action: 'Watch the box follow the car. No alert is raised just because a car appears.' },
  { id: 'anpr', name: 'Read its number plate', module: 'Vehicle intelligence', at: 12, route: '/anpr', question: 'Which vehicle was seen, and when?', explanation: 'The plate is read as DEMO 2026. The observation is stored with its camera and capture time. A plate read is a candidate identifier, not proof of who is driving.', action: 'Compare the plate crop with the recorded text and timestamp.' },
  { id: 'tracking', name: 'Find it on another camera', module: 'Tracking', at: 24, route: '/wall', question: 'Has this vehicle appeared somewhere else?', explanation: 'CAM-08 records the same demo plate after CAM-07. The timeline connects these two sightings. The road between the cameras was not observed continuously.', action: 'Watch the second sighting appear. The dashed connection means a gap in coverage.' },
  { id: 'fence', name: 'Explain a fence alert', module: 'PARAKH · Virtual Fence', at: 36, route: '/virtual-fence', question: 'Why does this movement need attention?', explanation: 'The vehicle enters a marked restricted zone at 14:32:39. After three seconds inside, an alert appears. The rule is zone entry plus dwell time, not the plate itself.', action: 'Watch the amber entry state turn red after the dwell threshold.' },
  { id: 'health', name: 'Notice a camera problem', module: 'Camera health', at: 48, route: '/health', question: 'Can we trust the current view?', explanation: 'CAM-12 temporarily loses its connection. Its last frame freezes and is labelled stale. Missing images must not be treated as fresh detections.', action: 'The timestamp freezes while the scenario clock keeps moving. No sighting is added during the outage.' },
  { id: 'gis', name: 'See where it reappears', module: 'GIS / Digital Twin', at: 60, route: '/gis', question: 'Where did these observations happen?', explanation: 'CAM-12 reconnects. A third plate sighting is placed on the schematic map with its capture time. Links between sightings indicate sequence, not an exact reconstructed route.', action: 'Compare all three camera timestamps on the map and observation list.' },
  { id: 'incident', name: 'Connect the evidence', module: 'SUTRA · Incident intelligence', at: 72, route: '/incident-intel', question: 'What belongs to the same incident?', explanation: 'The restricted-zone event and related vehicle observations are grouped into a reviewable demo incident. An operator can inspect why each observation was included.', action: 'Read the explanation: restricted-zone dwell is the alert reason; the plate helps retrieve sightings.' },
  { id: 'field', name: 'Keep field reports in sync', module: 'SAKSHAM · Field resilience', at: 84, route: '/field', question: 'What happens if the field team is offline?', explanation: 'A simulated field observation is saved locally while the link is down. When connectivity returns, it is marked synced. This demonstration does not contact a real team.', action: 'Watch “Queued offline” become “Synced” at 14:33:32.' },
  { id: 'route', name: 'Compare response routes', module: 'MARGDARSHAN · Route analysis', at: 96, route: '/route-analysis', question: 'How could a team reach the checkpoint?', explanation: 'Two illustrative routes are compared. Route B avoids the camera outage area. These are demonstration routes, not real navigation or operational directions.', action: 'Compare the route choices and the stated reason for preferring B.' },
  { id: 'evidence', name: 'Review the whole story', module: 'PRAMAAN · Evidence', at: 108, route: '/evidence', question: 'Can someone explain and review what happened?', explanation: 'The demo record collects the plate, camera timestamps, fence rule, outage and field report in one timeline. Export it to inspect the same events outside the portal.', action: 'Replay any chapter or download the clearly labelled simulation record. No production evidence is created.' },
] as const

export const demoEvents = [
  { at: 3, camera: 'CAM-07', title: 'Vehicle detected', detail: 'A white car is present. No threat conclusion.', kind: 'observation' },
  { at: 8, camera: 'CAM-07', title: 'First plate sighting', detail: `${DEMO_PLATE} · checkpoint entrance`, kind: 'sighting' },
  { at: 28, camera: 'CAM-08', title: 'Second plate sighting', detail: `${DEMO_PLATE} · perimeter road · candidate match`, kind: 'sighting' },
  { at: 39, camera: 'CAM-08', title: 'Restricted zone entered', detail: 'Dwell timer starts. Threshold: 3 seconds.', kind: 'zone' },
  { at: 42, camera: 'CAM-08', title: 'Fence alert raised', detail: 'Three seconds inside the restricted zone. Operator review required.', kind: 'alert' },
  { at: 48, camera: 'CAM-12', title: 'Camera connection lost', detail: 'Last frame retained. New observations paused.', kind: 'health' },
  { at: 60, camera: 'CAM-12', title: 'Camera reconnected', detail: 'Fresh frames available again.', kind: 'health' },
  { at: 62, camera: 'CAM-12', title: 'Third plate sighting', detail: `${DEMO_PLATE} · exit checkpoint`, kind: 'sighting' },
  { at: 76, camera: 'DEMO-INC-01', title: 'Observations grouped for review', detail: 'Fence event + three sightings + camera-health context.', kind: 'incident' },
  { at: 87, camera: 'FIELD-DEMO', title: 'Field report queued offline', detail: 'Simulated operator note saved locally.', kind: 'field' },
  { at: 92, camera: 'FIELD-DEMO', title: 'Field report synced', detail: 'Simulated connection restored.', kind: 'field' },
  { at: 101, camera: 'ROUTE-DEMO', title: 'Route B suggested', detail: 'Illustrative route avoids the outage area. Human approval required.', kind: 'route' },
  { at: 113, camera: 'DEMO-RECORD-01', title: 'Demo record ready', detail: 'Timeline export available. Not a production evidence record.', kind: 'evidence' },
] as const

export type DemoChapter = { id: string; name: string; module: string; at: number; route: string; question: string; explanation: string; action: string }
export type DemoEvent = { at: number; camera: string; title: string; detail: string; kind: string }

export function getChapters(scenario: ScenarioId): DemoChapter[] {
  if (scenario === 'vehicle') return [...chapters]
  const subject = scenario === 'person' ? 'person' : scenario === 'animal' ? 'animal' : 'camera'
  const result: DemoChapter[] = chapters.map(c => ({ ...c }))
  result[0] = { ...result[0], name: scenario === 'health' ? 'Check the camera view' : `Detect a ${subject}`, question: scenario === 'health' ? 'Is this camera giving a usable view?' : `What entered the camera view?`, explanation: scenario === 'health' ? 'Start with a clear camera image. Image quality and connectivity are monitored separately from object detection.' : `A ${subject} enters the view. The bounding box is a scripted detection; it does not identify an individual or establish a threat.`, action: scenario === 'health' ? 'Watch the baseline view before the image degrades.' : `Follow the labelled ${subject} across the scene.` }
  result[1] = { ...result[1], name: scenario === 'health' ? 'Detect image blur' : `Classify the ${subject}`, module: scenario === 'health' ? 'Image quality' : 'Object classification', question: scenario === 'health' ? 'Is the picture too blurry to rely on?' : 'Is this a person, vehicle or animal?', explanation: scenario === 'health' ? 'The image becomes blurred at 14:32:12. A quality warning appears before the connection is lost. The quality state matters even if frames are still arriving.' : `This case is classified as ${subject.toUpperCase()}. Number-plate reading does not apply here. Classification determines which configured zone rules should run.`, action: scenario === 'health' ? 'Compare the blurred image with the normal view after 14:32:24.' : 'Read the object-class label. The vehicle case separately demonstrates number-plate reading.' }
  result[2] = { ...result[2], explanation: scenario === 'health' ? 'CAM-08 provides an alternative view while camera quality is monitored. A different camera view does not repair or replace the missing original evidence.' : `A second camera records the ${subject}. These scripted sightings illustrate a possible track handover; continuity between cameras is not a confirmed identity.`, action: 'Compare camera IDs and capture times. Gaps in coverage are explicitly shown.' }
  result[3] = { ...result[3], name: scenario === 'animal' ? 'Suppress an irrelevant alert' : scenario === 'health' ? 'Check rule availability' : 'Explain the person alert', question: scenario === 'animal' ? 'Should every animal crossing raise an intrusion alert?' : scenario === 'health' ? 'Can zone rules use a degraded camera?' : 'Why was this person flagged?', explanation: scenario === 'animal' ? 'The animal enters the zone, but this example rule monitors people and vehicles. Animal movement is recorded without raising an intrusion incident. Different zones can have different rules.' : scenario === 'health' ? 'Zone rules depend on usable images. A camera fault is not itself an intrusion. An operator should review coverage before relying on automatic zone events.' : 'The person enters a restricted zone and stays inside for three seconds. That rule triggers review; appearance or identity does not.', action: scenario === 'animal' ? 'At 14:32:42, see “Animal excluded by this rule” instead of a red alert.' : scenario === 'health' ? 'The intrusion counter stays clear in this maintenance scenario.' : 'Watch the zone change from amber to red after three seconds.' }
  result[5] = { ...result[5], explanation: scenario === 'health' ? 'The map shows which camera lost coverage and when fresh images returned. It helps an operator distinguish a coverage gap from an observed event.' : `After CAM-12 reconnects, a third ${subject} observation appears. The map shows observation order, not a verified route between camera positions.` }
  result[6] = { ...result[6], name: scenario === 'person' ? 'Group the intrusion signals' : 'Review context without over-alerting', explanation: scenario === 'animal' ? 'The object classification and configured rule explain why no intrusion incident is created. The observations remain available for review.' : scenario === 'health' ? 'Blur, connection loss and recovery are grouped into a maintenance review. No vehicle identity, plate or intrusion is inferred from these camera faults.' : 'The person’s zone-entry event is grouped with related camera observations and the coverage gap. A human can review the reason for each link.', action: scenario === 'person' ? 'Review zone entry + dwell + related observations.' : 'Notice that an observation or fault can be recorded without creating an intrusion incident.' }
  result[7] = { ...result[7], explanation: `A simulated ${scenario === 'health' ? 'maintenance' : subject + ' observation'} note is queued while the field connection is down, then synced when it returns. No real team is contacted.` }
  result[8] = { ...result[8], explanation: scenario === 'animal' ? 'No response team is requested for this excluded animal event. Route analysis remains available for a separate operational need; a detection does not automatically dispatch anyone.' : `Two illustrative routes are compared for ${scenario === 'health' ? 'a maintenance visit' : 'operator response'}. Route B avoids the coverage gap. This is a suggestion, not an automatic dispatch.` }
  result[9] = { ...result[9], explanation: `The export records ${scenario === 'health' ? 'image quality, connection loss, recovery and maintenance context' : subject + ' observations, timestamps, zone-rule outcome and camera context'}. It is clearly labelled simulation, not production evidence.` }
  result[0].route = scenario === 'health' ? '/health' : '/detections'
  if (scenario === 'animal') {
    result[0].name = 'Detect an animal'
    result[0].explanation = 'An animal enters the view. The bounding box marks a scripted detection; the configured zone rule decides whether it needs an intrusion alert.'
  }
  result[2].question = scenario === 'health' ? 'Which camera still provides coverage?' : `Has this ${subject} appeared on another camera?`
  result[1].route = scenario === 'health' ? '/health' : '/field'
  return result
}

export function getEvents(scenario: ScenarioId): DemoEvent[] {
  if (scenario === 'vehicle') return [...demoEvents]
  const subject = scenario === 'person' ? 'Person' : 'Animal'
  if (scenario === 'health') return [
    { at: 3, camera: 'CAM-07', title: 'Baseline image available', detail: 'Clear image; camera connection healthy.', kind: 'health' },
    { at: 12, camera: 'CAM-07', title: 'Image blur detected', detail: 'Frames still arriving, but scene details are unreliable.', kind: 'health' },
    { at: 24, camera: 'CAM-08', title: 'Alternative camera available', detail: 'Use a different view; do not invent missing observations.', kind: 'health' },
    ...demoEvents.filter(e => e.kind === 'health'),
    { at: 62, camera: 'CAM-12', title: 'Fresh image confirmed', detail: 'New camera timestamps advance after recovery.', kind: 'health' },
    { at: 76, camera: 'DEMO-MAINT-01', title: 'Maintenance review created', detail: 'Blur + outage + recovery. Not an intrusion incident.', kind: 'maintenance' },
    ...demoEvents.filter(e => e.kind === 'field' || e.kind === 'route' || e.kind === 'evidence'),
  ]
  return demoEvents.map(event => {
    if (event.kind === 'sighting') return { ...event, title: `${subject} sighting on ${event.camera}`, detail: `Scripted ${subject.toLowerCase()} observation · potential continuity, not identity verification.` }
    if (event.at === 3) return { ...event, title: `${subject} detected`, detail: `${subject.toUpperCase()} class label. No identity claim.` }
    if (scenario === 'animal' && event.at === 42) return { ...event, title: 'Animal excluded by this rule', detail: 'This zone monitors people and vehicles. Observation retained; no intrusion alert.', kind: 'rule' }
    if (event.at === 76) return { ...event, camera: scenario === 'animal' ? 'DEMO-REVIEW-01' : event.camera, title: scenario === 'animal' ? 'Observation reviewed; no incident' : 'Person intrusion signals grouped', detail: scenario === 'animal' ? 'Class + configured rule explain the decision.' : 'Person sightings + restricted-zone dwell + camera-health context.', kind: scenario === 'animal' ? 'review' : 'incident' }
    if (scenario === 'animal' && event.at === 101) return { ...event, title: 'No response route requested', detail: 'Animal excluded by this rule. No dispatch implied.', kind: 'route' }
    return { ...event }
  })
}

export function chapterForPath(path: string) {
  if (path.startsWith('/camera/') && path.endsWith('/vehicles')) return chapters[1]
  if (path.startsWith('/camera/')) return chapters[3]
  if (path.startsWith('/track/')) return chapters[2]
  if (path.startsWith('/vehicle/')) return chapters[1]
  if (path.startsWith('/incident/')) return chapters[6]
  if (path === '/events') return chapters[6]
  if (path === '/camera-health') return chapters[4]
  return chapters.find(chapter => chapter.route === path) ?? chapters[0]
}

export function demoClock(seconds: number) {
  const total = 14 * 3600 + 32 * 60 + Math.floor(seconds)
  return [Math.floor(total / 3600), Math.floor(total / 60) % 60, total % 60].map(n => String(n).padStart(2, '0')).join(':')
}

export function scenarioAt(seconds: number, scenario: ScenarioId = 'vehicle') {
  const time = Math.max(0, Math.min(DEMO_DURATION, seconds))
  const scenarioChapters = getChapters(scenario)
  const chapter = [...scenarioChapters].reverse().find(c => time >= c.at) ?? scenarioChapters[0]
  const events = getEvents(scenario).filter(e => e.at <= time)
  return {
    time, chapter, events,
    sightings: events.filter(e => e.kind === 'sighting'),
    camera: time < 24 ? 'CAM-07' : time < 48 ? 'CAM-08' : 'CAM-12',
    outage: time >= 48 && time < 60,
    alert: (scenario === 'vehicle' || scenario === 'person') && time >= 42,
    inside: scenario !== 'health' && time >= 39 && time < 48,
  }
}
