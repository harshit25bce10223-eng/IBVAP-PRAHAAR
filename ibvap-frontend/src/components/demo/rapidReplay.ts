export const DEFAULT_REPLAY_SPEED = 4
export const RAPID_DURATION = 480
export function advanceReplay(time: number, speed: number) {
  return Math.min(RAPID_DURATION, time + speed)
}
const explanations = [
  {
    at: 0,
    text: 'Welcome to Prahaar. This two minute replay follows one incident across four cameras. Watch the same map as the system links people, vehicles, alerts and evidence. These are simulated observations for the demo.',
  },
  {
    at: 60,
    text: 'A person leaves the first car. The system separates the person from an animal, keeps a track, and checks suspicious movement near the fence. The plate and camera observations stay linked to the same incident.',
  },
  {
    at: 170,
    text: 'The first car takes Path B. The person continues separately, then enters a second car. Both cars remain traceable. After boarding, the person location is inferred from the second car, rather than claimed as a fresh camera detection.',
  },
  {
    at: 230,
    text: 'Now fog reduces visibility and a camera fails. Prahaar shows the uncertainty and missing coverage. It keeps earlier observations and combines available signals into a risk score for officer review.',
  },
  {
    at: 320,
    text: 'The network is down. Incident records stay saved locally. Evidence gets a digital fingerprint so changes can be checked. When connectivity returns, queued records are delivered without losing their original capture order.',
  },
  {
    at: 385,
    text: 'The officer can verify evidence, inspect permissions, and review the incident on the map. Route and coverage tools explain where to respond. Camera failure remains visible throughout.',
  },
  {
    at: 452,
    text: 'The final handover brings the person, both cars, alerts and evidence into one connected story. This is a simulated replay with local integrity checks. The complete incident is ready for review.',
  },
]
export function rapidNarration(time: number) {
  const available = explanations.filter(segment => segment.at <= time)
  return available[available.length - 1] ?? explanations[0]
}
