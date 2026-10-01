import type { StoryView } from './masterStory'
export const narrationScript: Record<StoryView, string> = {
  hook: 'Welcome to Prahaar. First, understand the map. The highlighted orange line at the top is the international border in this fictional sector. The opposite side is above it. The Indian side, checkpoint, restricted compound and roads are below it. North is up. We will follow one person and two cars across four cameras.',
  overview:
    'This is a remote border sector at night. Camera one faces east along the entry road. Camera two faces west across the handoff area. Camera three faces west from the eastern post. Camera four faces north from the service road. The arrows show these illustrative directions. The orange international border is separate from Zone A. Zone A is the restricted compound, outlined with a people-only virtual fence. The grey road is the vehicle route, and the lower branch is Path B.',
  ingestion:
    'Every camera observation keeps its camera name and capture time. That helps us put the story back in order later. The camera views in this demonstration are a controlled replay.',
  trust:
    'Before trusting a detection, check the camera itself. Here, camera one repeats an old frame. Prahaar marks the feed as suspicious and pauses new detections until fresh frames return.',
  night:
    'The area is dark. Compare the raw view with the brighter view to understand how clearer images can help detection. This is an illustration of processing, not a live enhancement model result.',
  detection:
    'First we see a deer, then a car, and then a person leaving the car. Each object gets its own label. Simply seeing movement does not mean there is an intrusion.',
  animal:
    'The deer enters the area, but our fence rule checks people. The deer stays visible as context and does not create a person intrusion alert. The person is checked separately.',
  tracking:
    'Now camera one follows the person as the same track. We keep the first observation, position, and time together. A new frame should not create a new person every time.',
  behavior:
    'The person waits near the fence for fifty-two seconds. That is useful context, but it does not tell us their intention. The officer can inspect this behavior alongside other clues.',
  fence:
    'The person enters Zone A and stays inside for three seconds. That meets the configured fence rule and creates an event. The event keeps the person track, camera, and original time.',
  anpr: 'Car one keeps its own vehicle ID and plate record. Six test observations support the plate reading. A plate links vehicle observations; it does not identify the driver or the person.',
  departure:
    'Car one now leaves along Path B. Notice that the person is no longer inside it. We keep following the car and the person separately, while keeping the earlier connection.',
  reid: 'Camera two sees a person after the gap between cameras. Appearance, travel time, and nearby camera locations support a possible match to X forty-two. The match still needs review.',
  transfer:
    'The same tracked person walks to car two and gets inside. We add a boarding link to car two. Car one and car two keep separate IDs, so the vehicle change does not mix their records.',
  followcars:
    'Look at both cars now. Car one continues on Path B, while car two moves with X forty-two inside. The person location now comes from the boarding link, not a fresh person detection.',
  why: 'Why does this camera match look likely? We compare appearance, the time between observations, and the distance between cameras. The explanation helps the officer check the match instead of trusting a number alone.',
  rejected:
    'A similar-looking candidate can still be wrong. This test candidate would have to travel four point eight kilometres in twelve seconds. That impossible transition keeps it out of the person record.',
  face: 'A face crop could add context when the image is usable and policy allows it. Here we only show a masked placeholder. No face model or personal identity match ran in this demo.',
  audio:
    'In this fictional terrorist attack exercise, a gunfire report arrives near the security post. It triggers an urgent officer review, not an automatic identity accusation. The first car reaches a closed control gate on Path B. The second car approaches the eastern post barrier with the person linked inside. Both destinations are marked on the map. No live microphone, real attack or operational dispatch is connected.',
  weather:
    'Fog reduces visibility. The system shows the lower observation confidence instead of hiding the problem. An officer can see that the same clue may be less reliable in difficult weather.',
  uncertainty:
    'The observation is not completely certain. We show detection confidence, image quality, and occlusion together. The officer can decide how much weight to give this clue.',
  health:
    'Camera three stops supplying fresh frames. Its last frame is marked stale, and its area becomes a visible coverage gap. The other cameras continue; missing observations are not invented.',
  correlation:
    'Now the clues form one incident. We connect car one, the person track, the fence event, the camera match, and the boarding link to car two. Each clue keeps its own source and time.',
  graph:
    'This view shows why the records are connected. Click a record to inspect its camera and time. The deer stays outside the intrusion story, and uncertain matches stay clearly labelled.',
  risk: 'The risk score comes from the actual backend replay rules. Zone entry, night movement, person class, and detection confidence each contribute visible points. A possible camera match gets no confirmed identity points.',
  risktrail:
    'You can check the reasons behind the score. These are outputs from the backend scorer using its checked-in defaults. Waiting near the fence remains context; we do not invent extra points for it.',
  review:
    'This second candidate has a weak match. The officer can review it or keep it separate. A weak candidate should not silently become part of X forty-two or change the main person record.',
  offline:
    'Now the internet connection goes down. The local replay keeps seven metadata records, and evidence can be prepared on the device. Losing the internet is different from losing a camera.',
  hash: 'The browser makes a real fingerprint for each frozen evidence record using SHA two fifty-six. This can work while the test uplink is offline. A local fingerprint is not a blockchain transaction.',
  sync: 'The test connection returns, and the saved records are delivered in the local simulation. Their original camera times stay unchanged. Camera three still has a coverage gap after the internet returns.',
  evidence:
    'Let us check whether the evidence was changed. Alter one field and the fingerprint no longer matches. Restore the original bytes and the match returns. This integrity calculation really runs in the browser.',
  security:
    'Different users should have different permissions. Try the officer and observer roles to see the local review control. Certificate checks and transport security are deployment controls that this demo does not verify.',
  gis: 'The map keeps the same person, both cars, the incident, and the camera areas. Dashed links show the observation sequence and gaps. They do not pretend the person was measured continuously everywhere.',
  heatmap:
    'This layer shows seven days of controlled historical data. It helps explain where activity repeats and where coverage is weak. The patterns are test data, not real border history.',
  coverage:
    'Activity and camera coverage are different things. Camera three remains unavailable even when nearby activity is visible elsewhere. The officer can see where the surveillance picture is incomplete.',
  route:
    'Compare the direct route with Path B. One route is shorter and near the active alert; the other has lower modeled exposure and a longer approach. The officer chooses, and neither route is guaranteed safe.',
  mobile:
    'The exercise security team acknowledges the attack alert. The first car is held at the Path B control gate and the second at the eastern post barrier. The officer sees the same person link, evidence and camera gap. Protect the post, review both vehicles and preserve evidence. This is a simulated acknowledgement, not a real dispatch, arrest or confirmed terrorist identification.',
  sop: 'A response procedure should help the officer choose the next action. This procedure workflow is a planned feature. We keep that clear instead of presenting it as a connected operational system.',
  integration:
    'Another system needs a clear incident message with the same IDs, risk, and evidence reference. You can inspect a sample message here. An external command system is not connected to this demo.',
  investigation:
    'Search the person, either car, a plate, or the incident. The results lead back to the original observations and evidence. The car change stays connected, so the person story does not stop at the first vehicle.',
  replay:
    'Replay the incident to follow the same sequence again. The person track, both vehicle IDs, boarding link, camera times, and evidence references remain connected and reproducible.',
  relationship:
    'Here is the complete chain. A camera observation becomes a person track, a car-change link, an incident, an explained decision, and verifiable local evidence. Every layer adds useful context.',
  closing:
    'One person, two separate cars, and one connected story. Prahaar keeps the clues, uncertainty, camera gaps, and evidence together. The officer stays in control of the decision.',
}
export function preferredIndianVoice<T extends { name: string; lang: string }>(
  voices: T[]
): T | undefined {
  const indian = voices.filter(v => v.lang.toLowerCase().replace('_', '-') === 'en-in')
  return (
    indian.find(v => /natural|neural|online/i.test(v.name)) ??
    indian.find(v => /heera|neerja/i.test(v.name)) ??
    indian[0] ??
    voices.find(v => v.lang.startsWith('en'))
  )
}
