// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — §40 scale checks (DEMO provider, real code paths)
//
// Verifies that:
//   • the list surface stays BOUNDED at 10 / 100 / 1,000 / 10,000 mock
//     detections — the UI only ever receives one page (≤ pageSize rows);
//   • filtering + sorting cost stays acceptable at those scales;
//   • concurrent fetches for one query key hit the provider exactly ONCE and
//     nothing refetches after settling (no duplicate requests / refetch loop).
//
// Synthetic rows are PERF INPUTS ONLY — never rendered, never presented as
// demo content. Timings exclude the mock provider's simulated 250 ms latency
// and prove nothing about production capacity (§40 "Do not claim production
// capacity").
// ─────────────────────────────────────────────────────────────────────────────

import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { DetectionQuery, DetectionResult } from '@/types/detection'
import { DEFAULT_DETECTION_QUERY } from '@/types/detection'
import { useDetectionStore } from '@/store/detectionState'
import { DEMO_NOW, MOCK_DETECTIONS } from '../mockDetectionData'
import { mockDetectionService } from '../mockDetectionService'

const BASE_COUNT = MOCK_DETECTIONS.length
const ORIGINAL = MOCK_DETECTIONS.slice()
const DEMO_REF = new Date(DEMO_NOW).getTime()
const WARMUP_RUNS = 3
const MEASURED_RUNS = 15

/** Synthetic perf row — all fields mirrored from a real fixture, refs cleared. */
function syntheticDetection(index: number): DetectionResult {
  const template = MOCK_DETECTIONS[0]
  const at = new Date(DEMO_REF - index * 1000).toISOString()
  return {
    ...template,
    detectionId: `DET-PERF-${String(index).padStart(6, '0')}`,
    cameraId: 'CAM-PERF',
    timestamp: at,
    receivedAt: at,
    updatedAt: at,
    trackId: null,
    eventId: null,
    incidentId: null,
    evidenceId: null,
    correlationId: null,
    anprRef: null,
  }
}

function percentile(sorted: number[], p: number): number {
  const idx = Math.min(sorted.length - 1, Math.ceil(p * sorted.length) - 1)
  return sorted[idx]
}

/** Advances fake timers past the provider latency and awaits the result. */
async function flush<T>(pending: Promise<T>): Promise<T> {
  await vi.advanceTimersByTimeAsync(300)
  return pending
}

/** Runs listDetections `runs` times (after warmup) on fake timers, timing the real pipeline. */
async function measure(query: DetectionQuery): Promise<{ p50: number; p95: number; max: number }> {
  const samples: number[] = []
  for (let i = 0; i < WARMUP_RUNS + MEASURED_RUNS; i++) {
    const t0 = performance.now()
    await flush(mockDetectionService.listDetections(query))
    if (i >= WARMUP_RUNS) samples.push(performance.now() - t0)
  }
  samples.sort((a, b) => a - b)
  return { p50: percentile(samples, 0.5), p95: percentile(samples, 0.95), max: samples[samples.length - 1] }
}

afterAll(() => {
  MOCK_DETECTIONS.length = 0
  MOCK_DETECTIONS.push(...ORIGINAL)
})

// Safety net: any synthetic rows appended by a failed run never leak forward.
afterEach(() => {
  MOCK_DETECTIONS.length = BASE_COUNT
})

// ── §40 · bounded + filtering at 10 / 100 / 1,000 / 10,000 ──────────────────

describe('§40 · bounded pages + filtering at scale', () => {
  const query: DetectionQuery = { ...DEFAULT_DETECTION_QUERY, cameraId: 'CAM-PERF' }

  it('10 / 100 / 1,000 / 10,000 mock detections stay bounded and filter acceptably', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    try {
      for (const n of [10, 100, 1000, 10000]) {
        for (let i = 0; i < n; i++) MOCK_DETECTIONS.push(syntheticDetection(i))

        const page = await flush(mockDetectionService.listDetections(query))
        // Correctness at scale: exact total, page bounded by pageSize.
        expect(page.total).toBe(n)
        expect(page.detections).toHaveLength(Math.min(query.pageSize, n))
        expect(page.detections.length).toBeLessThanOrEqual(query.pageSize)

        const t = await measure(query)
        console.info(
          `[§40] ${n.toLocaleString('en-US')} detections → p50 ${t.p50.toFixed(2)} ms · ` +
            `p95 ${t.p95.toFixed(2)} ms · max ${t.max.toFixed(2)} ms ` +
            `(excl. 250 ms simulated provider delay; smoke bound only, not a capacity claim)`
        )
        // Smoke bound — guards against pathological blowups, not a capacity claim.
        expect(t.p95).toBeLessThan(500)

        MOCK_DETECTIONS.length = BASE_COUNT // restore before the next scale
      }
    } finally {
      vi.useRealTimers()
    }
  }, 30000)
})

// ── §40 · no duplicate requests ─────────────────────────────────────────────

describe('§40 · no duplicate requests (single-flight per query key)', () => {
  const store = useDetectionStore
  const SNAPSHOT = {
    query: store.getState().query,
    page: store.getState().page,
    listState: store.getState().listState,
    listError: store.getState().listError,
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    store.setState({ query: { ...DEFAULT_DETECTION_QUERY }, page: null, listState: 'idle', listError: null })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  afterAll(() => store.setState(SNAPSHOT))

  it('two concurrent fetches for the same query hit the provider once, then stay quiet', async () => {
    const spy = vi.spyOn(mockDetectionService, 'listDetections')

    const p1 = store.getState().fetchList()
    const p2 = store.getState().fetchList()
    expect(p2).toBe(p1) // second call joined the in-flight request
    expect(store.getState().listState).toBe('loading')

    await vi.advanceTimersByTimeAsync(300)
    await Promise.all([p1, p2])

    expect(spy).toHaveBeenCalledTimes(1)
    expect(store.getState().listState).toBe('ready')
    expect(store.getState().page?.total).toBe(BASE_COUNT)

    // Settled state produces no further provider traffic (no refetch loop).
    await vi.advanceTimersByTimeAsync(5000)
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('a filter change issues exactly one new request and resets to page 1', async () => {
    const spy = vi.spyOn(mockDetectionService, 'listDetections')

    const p1 = store.getState().fetchList()
    await vi.advanceTimersByTimeAsync(300)
    await p1

    store.getState().setQuery({ class: 'PERSON' })
    expect(store.getState().query.page).toBe(1)

    const p2 = store.getState().fetchList()
    const p3 = store.getState().fetchList() // duplicate of the changed query → deduped
    expect(p3).toBe(p2)

    await vi.advanceTimersByTimeAsync(300)
    await Promise.all([p2, p3])

    expect(spy).toHaveBeenCalledTimes(2)
    expect(store.getState().listState).toBe('ready')
  })
})
