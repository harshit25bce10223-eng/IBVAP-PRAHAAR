import { describe, expect, it } from 'vitest'
import { chapterForPath, defaultScenario, getChapters, demoClock, scenarioAt } from './scenario'
import { useExperienceStore } from '@/store/experienceState'

describe('guided scenario chronology', () => {
  it('distinguishes a person intrusion from an excluded animal crossing', () => {
    expect(scenarioAt(42, 'person').alert).toBe(true)
    expect(scenarioAt(42, 'animal').alert).toBe(false)
    expect(scenarioAt(120, 'animal').events.some(e => e.kind === 'alert' || e.kind === 'incident')).toBe(false)
    const events = scenarioAt(42, 'animal').events
    expect(events[events.length - 1]?.title).toBe('Animal excluded by this rule')
  })
  it('does not invent plate reads or intrusions in the maintenance case', () => {
    const health = scenarioAt(120, 'health')
    expect(health.sightings).toEqual([])
    expect(health.alert).toBe(false)
    expect(health.events.some(e => /plate|dwell/i.test(e.title))).toBe(false)
    expect(getChapters('health')[1].route).toBe('/health')
    expect(defaultScenario('/health')).toBe('health')
    expect(defaultScenario('/virtual-fence')).toBe('person')
    expect(defaultScenario('/field')).toBe('animal')
  })
  it('reveals plate sightings only after their capture times', () => {
    expect(scenarioAt(7).sightings).toHaveLength(0)
    expect(scenarioAt(8).sightings.map(e => e.camera)).toEqual(['CAM-07'])
    expect(scenarioAt(28).sightings.map(e => e.camera)).toEqual(['CAM-07', 'CAM-08'])
    expect(scenarioAt(62).sightings.map(e => e.camera)).toEqual(['CAM-07', 'CAM-08', 'CAM-12'])
    expect(scenarioAt(28).events.every(e => e.at <= 28)).toBe(true)
  })
  it('requires zone dwell before an alert and retains it for review', () => {
    expect(scenarioAt(38).inside).toBe(false)
    expect(scenarioAt(39).inside).toBe(true)
    expect(scenarioAt(41).alert).toBe(false)
    expect(scenarioAt(42).alert).toBe(true)
    expect(scenarioAt(80).alert).toBe(true)
  })
  it('does not record new sightings during a camera outage', () => {
    expect(scenarioAt(48).outage).toBe(true)
    expect(scenarioAt(59).sightings).toHaveLength(2)
    expect(scenarioAt(60).outage).toBe(false)
    expect(scenarioAt(60).sightings).toHaveLength(2)
  })
  it('scrubbing back clears future events; time and chapter boundaries agree', () => {
    expect(scenarioAt(120).events.length).toBeGreaterThan(10)
    expect(scenarioAt(0).events).toEqual([])
    expect(scenarioAt(120).chapter.id).toBe('evidence')
    expect(demoClock(92)).toBe('14:33:32')
  })
  it('opens the appropriate demo for original workspace routes', () => {
    expect(chapterForPath('/virtual-fence').id).toBe('fence')
    expect(chapterForPath('/camera/CAM-07/vehicles').id).toBe('anpr')
    expect(chapterForPath('/vehicle/VEH-A001').id).toBe('anpr')
    expect(chapterForPath('/track/TRK-1042').id).toBe('tracking')
    expect(chapterForPath('/camera-health').id).toBe('health')
  })
  it('defaults to demo and can return from the unchanged real workspace', () => {
    expect(useExperienceStore.getState().mode).toBe('demo')
    useExperienceStore.getState().setMode('real')
    expect(useExperienceStore.getState().mode).toBe('real')
    useExperienceStore.getState().setMode('demo')
    expect(useExperienceStore.getState().mode).toBe('demo')
  })
})
