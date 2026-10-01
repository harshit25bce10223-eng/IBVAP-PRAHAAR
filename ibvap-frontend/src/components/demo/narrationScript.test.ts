import { describe, expect, it } from 'vitest'
import { masterSteps } from './masterStory'
import { narrationScript, preferredIndianVoice } from './narrationScript'
describe('Indian demo narration', () => {
  it('explains every story chapter with a complete script', () => {
    for (const step of masterSteps) {
      expect(narrationScript[step.id].split(' ').length).toBeGreaterThan(20)
    }
    expect(narrationScript.followcars).toContain('not a fresh person detection')
    expect(narrationScript.evidence).toContain('really runs in the browser')
  })
  it('prefers a natural Indian voice ahead of a natural American voice', () => {
    const voices = [
      { name: 'US Natural', lang: 'en-US' },
      { name: 'Microsoft Heera', lang: 'en-IN' },
      { name: 'Neerja Online Natural', lang: 'en-IN' },
    ]
    expect(preferredIndianVoice(voices)?.name).toBe('Neerja Online Natural')
    expect(preferredIndianVoice(voices.slice(0, 2))?.name).toBe('Microsoft Heera')
  })
  it('handles delayed voices and missing Indian voices', () => {
    expect(preferredIndianVoice([])).toBeUndefined()
    expect(preferredIndianVoice([{ name: 'English', lang: 'en-US' }])?.name).toBe('English')
  })
})
