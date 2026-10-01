import type { StoryStep, StoryView } from './masterStory'
const words: Partial<Record<StoryView, [string, string]>> = {
  hook: [
    'Understand the border before the incident',
    'Orange line: international border. Below: Indian side. North is up.',
  ],
  overview: [
    'Border, fence, roads and camera directions',
    'Camera arrows show facing; Zone A is a separate virtual fence.',
  ],
  ingestion: ['Camera frames arrive', 'Each observation keeps its camera and time.'],
  trust: ['Check a frozen camera', 'Pause detections when the camera repeats old frames.'],
  night: ['See better in the dark', 'Switch between the dark and brighter test view.'],
  detection: [
    'Spot the animal, car and person',
    'An object is seen. It is not automatically a threat.',
  ],
  animal: ['Leave the deer out of the alert', 'This fence rule checks people, not deer.'],
  tracking: ['Keep following the person', 'The same person keeps track TRK-017.'],
  behavior: ['The person waits near the fence', 'Waiting adds context; it does not prove intent.'],
  fence: ['The person enters Zone A', 'After three seconds inside, the fence alert is ready.'],
  anpr: ['Read Car 1’s plate', 'V-042 keeps plate MP09AB1234.'],
  departure: ['Car 1 takes Path B', 'The car moves away. The person is still tracked separately.'],
  reid: [
    'Find the person on Camera 2',
    'Two camera tracks may belong to X42. A reviewer checks the match.',
  ],
  transfer: [
    'The person gets into Car 2',
    'Keep Car 1, X42 and Car 2 connected without mixing their IDs.',
  ],
  followcars: [
    'Follow the person and both cars',
    'Car 1 stays on Path B. Car 2 moves with X42 inside.',
  ],
  why: ['Why does the match look likely?', 'Compare appearance, travel time and camera locations.'],
  rejected: ['Reject an impossible match', 'A car or person cannot jump 4.8 km in 12 seconds.'],
  face: ['Check a possible face crop', 'This is a planned feature; no identity match ran.'],
  audio: [
    'Attack alert near the security post',
    'Fictional exercise: protect the post, review vehicles and preserve evidence.',
  ],
  weather: ['Fog makes the view harder', 'Lower visibility means less reliable observations.'],
  uncertainty: [
    'Show what is uncertain',
    'The officer sees confidence and image quality together.',
  ],
  health: ['Camera 3 stops working', 'Mark the blind area; do not invent missing observations.'],
  correlation: ['Put the clues into one incident', 'Car 1 → X42 → Car 2 → INC-1042.'],
  graph: ['See how the clues connect', 'Click a record to see its source and time.'],
  risk: ['Explain the risk score', 'Every point comes from the backend’s replay rules.'],
  risktrail: [
    'Show the reasons behind the score',
    'The camera match is still a candidate, so it gets no confirmed-match points.',
  ],
  review: ['Keep a weak match separate', 'A 61% match needs a human decision.'],
  offline: ['The internet goes down', 'Keep records and evidence locally.'],
  hash: ['Make an evidence fingerprint', 'Real SHA-256 runs in this browser.'],
  sync: ['Send the saved test records', 'Reconnect without changing the original camera times.'],
  evidence: [
    'Check if evidence was changed',
    'Change one field, then restore it and compare the fingerprints.',
  ],
  security: [
    'Check who can review evidence',
    'Try the Officer and Observer roles in this local test.',
  ],
  gis: ['See the same incident on the map', 'The person and both cars keep the same IDs.'],
  heatmap: ['See past activity', 'This heatmap uses seven days of test data.'],
  coverage: ['Show the camera blind area', 'Camera 3 remains unavailable.'],
  route: ['Compare two routes', 'Path B avoids the direct approach near the alert.'],
  mobile: [
    'Show the field officer’s view',
    'The same incident appears in this simulated phone view.',
  ],
  sop: ['Show the next response step', 'The procedure workflow is a planned feature.'],
  integration: [
    'Show what another system receives',
    'Inspect a sample incident message. No external receiver is connected.',
  ],
  investigation: ['Find the person and both cars', 'Search X42, a car ID, a plate or INC-1042.'],
  replay: ['Watch the story again', 'Replay the same tracks, car change and evidence.'],
  relationship: ['Follow the whole chain', 'Camera → person → car change → incident → evidence.'],
  closing: [
    'One connected story',
    'Two cars stay separate. The person’s links and evidence stay connected.',
  ],
}
export function simpleStory(step: StoryStep): StoryStep {
  const copy = words[step.id]
  return copy ? { ...step, title: copy[0], question: copy[0], output: copy[1] } : step
}
