// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — Track Simulator (Tracking-module stand-in)
//
// The real IBVAP Tracking module will POST TrackObservation payloads to
// /api/v1/evaluation/track_and_evaluate. Until it is wired in, this simulator
// produces realistic observations (walking paths across zone polygons) that
// exercise the identical contract. Swap `simulator.start()` for a live
// tracking pipeline without touching the rest of the UI.
// ─────────────────────────────────────────────────────────────────────────────

import type { NormalizedBBox, ObjectType, Reliability, TrackObservation } from '@/types'

interface SimTrackSpec {
  id: string
  objectType: ObjectType
  start: { x: number; y: number }
  end: { x: number; y: number }
  speed: number          // normalized units per second
  confidence: number
  reliability: Reliability
  isNight: boolean
  multiCamera: boolean
}

function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5)
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * Simulates a fixed pool of tracks that repeatedly traverse between points,
 * producing a frame periodically.
 */
export class TrackSimulator {
  private timer: ReturnType<typeof setInterval> | null = null
  private tracks: SimTrackSpec[] = []
  private progress = new Map<string, number>()
  private phase = 'enter' // enter → traverse → leave

  constructor(
    private readonly cameraId: string,
    private readonly onObservation: (obs: TrackObservation) => void,
    private readonly frameIntervalMs = 300
  ) {}

  setTracks(specs: SimTrackSpec[]) {
    this.tracks = specs
    for (const spec of specs) {
      if (!this.progress.has(spec.id)) {
        this.progress.set(spec.id, 0)
      }
    }
  }

  start() {
    if (this.timer) return
    this.phase = 'enter'
    this.timer = setInterval(() => this.tick(), this.frameIntervalMs)
  }

  stop() {
    if (this.timer) clearInterval(this.timer)
    this.timer = null
  }

  private tick() {
    const dt = this.frameIntervalMs / 1000
    for (const spec of this.tracks) {
      const progress = this.progress.get(spec.id) ?? 0
      const travelTime = Math.hypot(spec.end.x - spec.start.x, spec.end.y - spec.start.y) / spec.speed

      const next = this.advanceProgress(progress, dt, travelTime)
      this.progress.set(spec.id, next)

      const pos = this.positionAt(spec, next)
      const bbox = bboxForObject(pos.x, pos.y, spec.objectType)
      this.onObservation({
        track_id: spec.id,
        camera_id: this.cameraId,
        object_type: spec.objectType,
        bbox,
        confidence: jitterConfidence(spec.confidence),
        is_night: spec.isNight,
        multi_camera_confirmed: spec.multiCamera,
        reliability: spec.reliability,
        timestamp: new Date().toISOString(),
      })
    }
  }

  /**
   * Progress envelope: strictly increasing so objects travel in one direction,
   * then the track is recycled by jumping back to the start. This keeps the
   * simulator continuously producing ENTRY→EXIT→ENTRY cycles that the engine
   * must not double-count, deduplicate correctly, and re-fire after EXIT.
   */
  private advanceProgress(progress: number, dt: number, travelTime: number) {
    const clamped = progress + dt / travelTime
    if (clamped > 1) return 0 // recycle — produces a fresh crossing cycle
    return clamped
  }

  private positionAt(spec: SimTrackSpec, t: number) {
    return {
      x: spec.start.x + (spec.end.x - spec.start.x) * t,
      y: spec.start.y + (spec.end.y - spec.start.y) * t,
    }
  }
}

export function bboxForObject(cx: number, cy: number, type: ObjectType): NormalizedBBox {
  if (type === 'VEHICLE') {
    return { x: cx - 0.035, y: cy - 0.08, width: 0.07, height: 0.08 }
  }
  if (type === 'ANIMAL') {
    return { x: cx - 0.02, y: cy - 0.045, width: 0.04, height: 0.045 }
  }
  // HUMAN
  return { x: cx - 0.018, y: cy - 0.075, width: 0.036, height: 0.075 }
}

function jitterConfidence(base: number) {
  const r = Math.sin(Date.now() * 0.001) * 0.02
  return Math.max(0, Math.min(1, base + r))
}

/** Prebuilt scenario: tracks that clearly cross a camera's restricted zones. */
export function trackSimulator(
  cameraId: string,
  onObservation: (obs: TrackObservation) => void,
  frameIntervalMs = 300
) {
  return new TrackSimulator(cameraId, onObservation, frameIntervalMs)
}

export function buildScenarioTracks(cameraId: string, isNight: boolean): SimTrackSpec[] {
  const rand = mulberry32(cameraId.length * 7919 + 17)
  const conf = () => 0.78 + rand() * 0.2
  return [
    {
      id: `TRK-${cameraId.slice(-2)}01`,
      objectType: 'HUMAN',
      start: { x: 0.1, y: 0.9 },
      end: { x: 0.92, y: 0.12 },
      speed: 0.28,
      confidence: conf(),
      reliability: rand() < 0.25 ? 'LOW' : 'HIGH',
      isNight,
      multiCamera: true,
    },
    {
      id: `TRK-${cameraId.slice(-2)}02`,
      objectType: 'VEHICLE',
      start: { x: 0.9, y: 0.85 },
      end: { x: 0.08, y: 0.15 },
      speed: 0.42,
      confidence: conf(),
      reliability: 'HIGH',
      isNight,
      multiCamera: true,
    },
    {
      id: `TRK-${cameraId.slice(-2)}03`,
      objectType: 'ANIMAL',
      start: { x: 0.15, y: 0.2 },
      end: { x: 0.85, y: 0.8 },
      speed: 0.5,
      confidence: conf(),
      reliability: 'MEDIUM',
      isNight: false,
      multiCamera: false,
    },
  ]
}