import { describe, expect, it } from 'vitest'
import { advanceReplay, DEFAULT_REPLAY_SPEED, rapidNarration } from './rapidReplay'
describe('two minute evaluator replay', () => {
  it('finishes in exactly 120 one-second ticks without voice delays', () => {
    let time = 0
    for (let tick = 0; tick < 119; tick++) time = advanceReplay(time, DEFAULT_REPLAY_SPEED)
    expect(time).toBe(476)
    expect(advanceReplay(time, DEFAULT_REPLAY_SPEED)).toBe(480)
    expect(advanceReplay(480, DEFAULT_REPLAY_SPEED)).toBe(480)
  })
  it('keeps short explanations stable across chapters and covers the transfer', () => {
    expect(rapidNarration(20)).toEqual(rapidNarration(0))
    expect(rapidNarration(205).text).toContain('second car')
    expect(rapidNarration(320).text).toContain('network')
    expect(rapidNarration(480).text).toContain('ready for review')
  })
})
