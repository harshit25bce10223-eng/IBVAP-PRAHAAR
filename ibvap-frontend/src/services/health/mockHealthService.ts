// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — mock health provider (DEMO ONLY)
//
// Serves the isolated fixtures from `mockHealthData.ts`. A short fixed delay
// keeps async loading states exercisable; it does NOT simulate a backend.
// Unknown camera ids reject so the UI exercises the error/last-known path.
// ─────────────────────────────────────────────────────────────────────────────

import type { CameraHealth } from '@/types/cameraHealth'
import type { IHealthService } from './IHealthService'
import { MOCK_HEALTH } from './mockHealthData'

const PROVIDER_DELAY_MS = 250

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

class MockHealthService implements IHealthService {
  readonly source = 'DEMO' as const

  async get(cameraId: string): Promise<CameraHealth> {
    await delay(PROVIDER_DELAY_MS)
    const record = MOCK_HEALTH[cameraId]
    if (!record) {
      throw new Error(`No health telemetry for camera ${cameraId}.`)
    }
    return record
  }

  async list(cameraIds?: string[]): Promise<CameraHealth[]> {
    await delay(PROVIDER_DELAY_MS)
    const ids = cameraIds ?? Object.keys(MOCK_HEALTH)
    return ids
      .map(id => MOCK_HEALTH[id])
      .filter((h): h is CameraHealth => h !== undefined)
  }
}

export const mockHealthService = new MockHealthService()
