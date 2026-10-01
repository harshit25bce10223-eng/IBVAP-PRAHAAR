import { ChallengeDemo } from './ChallengeDemo'
import { MasterDemo } from './MasterDemo'
export function GuidedDemo() {
  return new URLSearchParams(window.location.search).get('mode') === 'challenge' ? (
    <ChallengeDemo />
  ) : (
    <MasterDemo />
  )
}
