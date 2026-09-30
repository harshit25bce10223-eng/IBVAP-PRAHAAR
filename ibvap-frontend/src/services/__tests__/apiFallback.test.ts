import { afterEach, describe, expect, it } from 'vitest'
import { api } from '../api'
import { zoneService } from '../zoneService'
import { incidentService } from '../incidentService'
import { evaluationService } from '../evaluationService'

const originalAdapter = api.defaults.adapter
afterEach(() => { api.defaults.adapter = originalAdapter })

describe('static-host API fallback', () => {
  it('returns a complete offline observation without fabricating an incident', async () => {
    api.defaults.adapter = async () => { throw new Error('Backend offline') }
    const response = await evaluationService.evaluate({
      track_id: 'DEMO-1', camera_id: 'CAM-07', object_type: 'HUMAN',
      bbox: { x: 0.2, y: 0.3, width: 0.2, height: 0.4 }, confidence: 0.9,
      is_night: false, multi_camera_confirmed: false, reliability: 'LOW',
    })
    expect(response.track.track_id).toBe('DEMO-1')
    expect(response.evaluation.representative_point).toEqual({ x: 0.30000000000000004, y: 0.7 })
    expect(response.evaluation.zones).toEqual([])
    expect(response.incident).toEqual({ created: false, incident_id: null, risk_score: null, severity: null, factors: [] })
    expect(response.exit_event.created).toBe(false)
  })
  it('rejects HTTP 200 HTML for all Virtual Fence list requests', async () => {
    api.defaults.adapter = async config => ({
      data: '<!doctype html><html><body>App shell</body></html>',
      status: 200, statusText: 'OK', headers: { 'content-type': 'text/html' }, config,
    })
    for (const request of [() => zoneService.list('CAM-07'), () => incidentService.list('CAM-07'), () => incidentService.listEvents('CAM-07')]) {
      await expect(request()).rejects.toThrow('Backend unavailable')
    }
    await expect(zoneService.list('CAM-07').catch(() => [])).resolves.toEqual([])
  })

  it('rejects HTML even when the server omits its content type', async () => {
    api.defaults.adapter = async config => ({
      data: '  <!doctype html><html></html>', status: 200, statusText: 'OK', headers: {}, config,
    })
    await expect(api.get('/zones')).rejects.toThrow('Backend unavailable')
  })

  it('preserves valid JSON responses', async () => {
    const zones = [{ zone_id: 'DEMO-ZONE', camera_id: 'CAM-07' }]
    api.defaults.adapter = async config => ({
      data: zones, status: 200, statusText: 'OK', headers: { 'content-type': 'application/json' }, config,
    })
    await expect(zoneService.list('CAM-07')).resolves.toEqual(zones)
  })
})
