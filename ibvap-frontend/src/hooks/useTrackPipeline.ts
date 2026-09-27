// ─────────────────────────────────────────────────────────────────────────────
// useTrackPipeline — wires the TrackSimulator → evaluationService → stores
//
// Demo-mode driver for Component 1: synthetic observations exercise the REAL
// backend contract (POST /evaluation/track_and_evaluate). The backend remains
// authoritative for geometry, risk and incidents; this hook only transports
// observations and mirrors responses into the visualization stores.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useCallback, useState } from 'react'
import { useCameraStore, useRiskStore } from '@/store'
import { evaluationService } from '@/services/evaluationService'
import { trackSimulator, buildScenarioTracks } from '@/services/trackSimulator'
import type { TrackObservation } from '@/types'

export function useTrackPipeline(cameraId: string) {
  const simRef = useRef<ReturnType<typeof trackSimulator> | null>(null)
  const [running, setRunning] = useState(false)
  // inFlight tracks outstanding evaluations without flashing global UI state.
  const inFlightRef = useRef(0)

  const onObservation = useCallback(
    async (obs: TrackObservation) => {
      const { upsertTrack } = useCameraStore.getState()
      const { pushEvaluation, prependIncident, setError } = useRiskStore.getState()
      const prev = useCameraStore.getState().tracks.find(t => t.track_id === obs.track_id)

      upsertTrack({
        track_id: obs.track_id,
        object_type: obs.object_type,
        bbox: obs.bbox,
        confidence: obs.confidence,
        representativePoint: { x: obs.bbox.x + obs.bbox.width / 2, y: obs.bbox.y + obs.bbox.height },
        path: prev?.path ?? [],
        lastSeen: Date.now(),
        insideZones: prev?.insideZones ?? [],
      })

      // Evaluate against backend. No global loading flicker per frame;
      // errors surface on the risk store without breaking the stream.
      inFlightRef.current += 1
      try {
        const resp = await evaluationService.evaluate(obs)
        pushEvaluation(resp)

        const inside = resp.evaluation.zones
          .filter(z => z.is_inside)
          .map(z => z.zone_name)

        upsertTrack({
          track_id: obs.track_id,
          object_type: obs.object_type,
          bbox: obs.bbox,
          confidence: obs.confidence,
          representativePoint: { x: obs.bbox.x + obs.bbox.width / 2, y: obs.bbox.y + obs.bbox.height },
          path: useCameraStore.getState().tracks.find(t => t.track_id === obs.track_id)?.path ?? [],
          lastSeen: Date.now(),
          insideZones: inside,
        })

        if (resp.incident.created) {
          prependIncident({
            incident_id: resp.incident.incident_id!,
            risk_score: resp.incident.risk_score ?? 0,
            severity: resp.incident.severity ?? 'LOW',
            factors: resp.incident.factors,
            event_id: resp.event.event_id!,
            camera_id: cameraId,
            track_id: obs.track_id,
            zone_id: resp.evaluation.zones.find(z => z.event?.created)?.zone_id ?? '',
            created_at: new Date().toISOString(),
          })
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Evaluation failed')
      } finally {
        inFlightRef.current -= 1
      }
    },
    [cameraId]
  )

  const start = useCallback(() => {
    if (simRef.current) return
    const { isNight } = useCameraStore.getState()
    // Build scenario tracks that cross the camera's zones
    const scenario = buildScenarioTracks(cameraId, isNight)

    const sim = trackSimulator(cameraId, onObservation, 300)
    sim.setTracks(scenario)
    sim.start()
    simRef.current = sim
    setRunning(true)
  }, [cameraId, onObservation])

  const stop = useCallback(() => {
    simRef.current?.stop()
    simRef.current = null
    setRunning(false)
  }, [])

  const selectedCameraId = useCameraStore(s => s.selectedCameraId)
  const isNight = useCameraStore(s => s.isNight)

  // Auto-start/stop when camera changes
  useEffect(() => {
    if (selectedCameraId === cameraId) {
      start()
    } else {
      stop()
    }
    return () => stop()
    // start/stop are stable unless cameraId changes — no track-driven loops.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCameraId, cameraId])

  // Re-seed tracks when night mode changes
  useEffect(() => {
    if (!simRef.current) return
    const scenario = buildScenarioTracks(cameraId, isNight)
    simRef.current.setTracks(scenario)
  }, [cameraId, isNight])

  return { start, stop, running }
}
