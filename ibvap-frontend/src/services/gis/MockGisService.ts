// ─────────────────────────────────────────────────────────────────────────────
// MockGisService — local-dev implementation (DEMO ONLY).
//
// Prototype map state is isolated here so a real GIS backend can replace it
// without rewriting any GIS component. Short latency keeps the same async
// shape as the future API.
// ─────────────────────────────────────────────────────────────────────────────

import type { GisData } from '@/types'
import type { IGisService } from './IGisService'
import { GIS_DEMO } from './mockGisData'

const LATENCY_MS = 200

export class MockGisService implements IGisService {
  async getGisData(_window?: 'LIVE' | '24H' | '7D'): Promise<GisData> {
    await new Promise(resolve => setTimeout(resolve, LATENCY_MS))
    return structuredClone(GIS_DEMO)
  }
}