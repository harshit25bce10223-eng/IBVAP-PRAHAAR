import { describe, expect, it } from 'vitest'
import { challengeAt, emptyFaults, missions, sha256 } from './challengeEngine'

describe('compound challenge outcomes', () => {
  it('separates animal exclusion from a person dwell alert', () => {
    const animal = challengeAt(51, 'animal')
    expect(animal.animalExcluded).toBe(true)
    expect(animal.intrusion).toBe(false)
    expect(challengeAt(54.9, 'animal').intrusion).toBe(false)
    expect(challengeAt(55, 'animal').intrusion).toBe(true)
    expect(challengeAt(47.9, 'compound').intrusion).toBe(false)
    expect(challengeAt(48, 'compound').intrusion).toBe(true)
  })
  it('never creates target observations or intrusion in a maintenance mission', () => {
    const state = challengeAt(150, 'health')
    expect(state.risk).toBe(0)
    expect(state.intrusion).toBe(false)
    expect(state.events.some(e => e.kind === 'alert' || e.kind === 'incident')).toBe(false)
    expect(state.events.some(e => /plate|person detected|reacquired/i.test(e.title))).toBe(false)
  })
  it('records a coverage gap without fresh target observations', () => {
    const gap = challengeAt(80, 'compound')
    expect(gap.cameraOffline).toBe(true)
    expect(gap.continuity).toContain('GAP')
    expect(gap.events.filter(e => e.camera === 'CAM3' && e.kind === 'observation')).toEqual([])
    expect(challengeAt(94, 'compound').events.some(e => e.title.includes('reacquired'))).toBe(true)
    const held = challengeAt(150, 'compound', { ...emptyFaults, camera: true })
    expect(held.cameraOffline).toBe(true)
    expect(held.events.some(e => /reacquired|Fresh stream recovered/.test(e.title))).toBe(false)
  })
  it('preserves capture order and drains queues only after reconnect', () => {
    expect(challengeAt(68, 'person').queued).toBe(1)
    expect(challengeAt(82, 'person').queued).toBe(3)
    expect(challengeAt(94.9, 'person').synced).toBe(0)
    expect(challengeAt(96, 'person').queued).toBe(2)
    expect(challengeAt(99, 'person').synced).toBe(3)
    const held = challengeAt(150, 'person', { ...emptyFaults, network: true })
    expect(held.queued).toBe(3)
    expect(held.synced).toBe(0)
    expect(held.events.some(e => /records synchronized|Uplink restored/.test(e.title))).toBe(false)
  })
  it('updates route exposure and confidence when a judge injects faults', () => {
    const clear = challengeAt(110, 'vehicle')
    const failed = challengeAt(110, 'vehicle', { fog: true, camera: true, network: false })
    expect(failed.confidence).toBeLessThan(clear.confidence)
    expect(failed.routes[0].exposure).toBeGreaterThan(clear.routes[0].exposure)
    expect(failed.routes[1].exposure).toBeLessThan(failed.routes[0].exposure)
    expect(failed.risk).toBe(failed.factors.reduce((sum, f) => sum + f.value, 0))
    expect(failed.severity).not.toBe('Critical')
  })
  it('retains earlier syncs and uses actual late recovery times', () => {
    const lateCut = challengeAt(
      125,
      'compound',
      { ...emptyFaults, network: true, camera: true },
      { network: 120, camera: 120 }
    )
    expect(lateCut.synced).toBe(3)
    expect(lateCut.queued).toBe(0)
    expect(lateCut.events.some(e => e.title.includes('reacquired'))).toBe(true)
    const release = { network: 70, networkResume: 125, camera: 70, cameraResume: 120 }
    expect(challengeAt(125, 'compound', emptyFaults, release).queued).toBe(3)
    expect(challengeAt(127, 'compound', emptyFaults, release).synced).toBe(2)
    const recovered = challengeAt(129, 'compound', emptyFaults, release)
    expect(recovered.queued).toBe(0)
    expect(recovered.events.find(e => e.title === 'Fresh stream recovered')?.at).toBe(120)
    expect(recovered.events.find(e => e.title === 'Three records synchronized')?.at).toBe(129)
  })
  it('replaying or scrubbing removes future outcomes across every mission', () => {
    for (const mission of missions) {
      const reset = challengeAt(0, mission.id)
      expect(reset.events.every(e => e.at === 0)).toBe(true)
      expect(reset.intrusion).toBe(false)
      expect(reset.queued).toBe(0)
      const middle = challengeAt(36, mission.id)
      expect(middle.events.every(e => e.at <= 36)).toBe(true)
      expect(challengeAt(999, mission.id).time).toBe(150)
      expect(challengeAt(-1, mission.id).time).toBe(0)
    }
  })
  it('computes SHA-256 for actual bytes and rejects altered evidence', async () => {
    expect(await sha256('abc')).toBe(
      'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    )
    const original = JSON.stringify({ simulation: true, captureSeconds: 125 })
    const changed = JSON.stringify({ simulation: false, captureSeconds: 125 })
    expect(await sha256(original)).not.toBe(await sha256(changed))
    expect(await sha256(original)).toBe(await sha256(original))
  })
})
