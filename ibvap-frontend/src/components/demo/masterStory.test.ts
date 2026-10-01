/// <reference types="node" />
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import {
  masterAt,
  masterSteps,
  masterClock,
  replayEvidencePayloads,
  searchMasterEvents,
} from './masterStory'
import { backendRiskReplay } from './backendRiskReplay'
describe('connected incident replay', () => {
  it('explains both vehicle stops and keeps the attack response chronological', () => {
    expect(masterAt(222).events.some(e => e.type === 'threat')).toBe(false)
    expect(masterAt(223).events.some(e => e.id === 'THREAT-223')).toBe(true)
    expect(masterAt(240).journey.firstStopped).toBe(true)
    expect(masterAt(294).journey.secondMoving).toBe(true)
    expect(masterAt(295).journey.secondMoving).toBe(false)
    expect(masterAt(480).journey.second).toEqual({ x: 740, y: 355 })
    expect(masterAt(480).events.find(e => e.id === 'RESPONSE-452')?.detail).toContain(
      'No real dispatch'
    )
    expect(masterAt(200).journey.secondStopped).toBe(false)
  })
  it('keeps both vehicle identities while the person changes cars', () => {
    const leaving = masterAt(180)
    expect(leaving.journey.first.y).toBeGreaterThan(355)
    expect(leaving.journey.secondVisible).toBe(false)
    const approaching = masterAt(200)
    expect(approaching.journey.secondVisible).toBe(true)
    expect(approaching.journey.boarded).toBe(false)
    const boarded = masterAt(205)
    expect(boarded.journey.boarded).toBe(true)
    expect(boarded.position).toEqual(boarded.journey.second)
    const moving = masterAt(240)
    expect(moving.journey.secondMoving).toBe(true)
    expect(moving.journey.first).not.toEqual(moving.journey.second)
    expect(moving.events.find(e => e.id === 'BOARD-X42')?.entity).toBe('X42')
    expect(moving.events.find(e => e.id === 'OBS-V077')?.entity).toBe('V-077')
    expect(moving.events.find(e => e.id === 'MOVE-V042')?.entity).toBe('V-042')
    expect(masterAt(100).events.some(e => e.id === 'BOARD-X42')).toBe(false)
    const payload = JSON.parse(replayEvidencePayloads(masterAt(340).events)[0])
    expect(payload.eventRecords.some((e: { id: string }) => e.id === 'BOARD-X42')).toBe(true)
    expect(searchMasterEvents(moving.events, 'DL08CD5678')[0].entity).toBe('V-077')
  })
  it('keeps the chronology ordered and excludes future observations', () => {
    expect(masterSteps.every((s, i) => i === 0 || s.at >= masterSteps[i - 1].at)).toBe(true)
    for (let time = 0; time <= 480; time += 5) {
      const s = masterAt(time)
      expect(s.events.every(e => e.at <= time)).toBe(true)
      expect(s.events.every((e, i) => i === 0 || e.capture >= s.events[i - 1].capture)).toBe(true)
    }
    expect(masterAt(60).associated).toBe(false)
  })
  it('waits for the dwell rule and excludes the animal from risk', () => {
    expect(masterAt(147).alert).toBe(false)
    expect(masterAt(148).alert).toBe(true)
    expect(masterAt(75).risk).toBe(0)
    expect(masterAt(280).risk).toBe(backendRiskReplay.cases.degraded.result.risk_score)
    expect(masterAt(280).factors.reduce((sum, f) => sum + f.value, 0)).toBe(74)
  })
  it('keeps uplink and camera outages independent', () => {
    expect(masterAt(340).networkOffline).toBe(true)
    expect(masterAt(385).networkOffline).toBe(false)
    expect(masterAt(385).cameraOffline).toBe(true)
    expect(masterAt(190).gap).toBe(false)
    expect(masterAt(180).position).toBeNull()
  })
  it('freezes three reproducible evidence payloads with consistent references', () => {
    const payloads = replayEvidencePayloads(masterAt(340).events)
    expect(payloads).toHaveLength(3)
    for (const payload of payloads) {
      const parsed = JSON.parse(payload)
      expect(parsed.incidentId).toBe('INC-1042')
      expect(parsed.entityId).toBe('X42')
      expect(parsed.eventRecords.every((e: { at: number }) => e.at <= 340)).toBe(true)
    }
    expect(searchMasterEvents(masterAt(480).events, 'MP09AB1234')[0].id).toBe('ANPR-042')
    expect(masterClock(122)).toBe('23:16:02')
  })
  it('detects stale exported scores when canonical backend sources change', () => {
    for (const [path, digest] of Object.entries(backendRiskReplay.sourceHashes)) {
      expect(
        createHash('sha256')
          .update(readFileSync(`../ibvap-backend/${path}`))
          .digest('hex')
      ).toBe(digest)
    }
  })
})
