import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import type { DetectionResult } from '@/types/detection'
import { useCameraStore, useDetectionStore, useHealthStore, useTrackingStore } from '@/store'
import { CameraFeed } from '@/components/camera/CameraFeed'
import { CameraHealthTile } from '@/components/camera-health'
import {
  DetectionInspector,
  DetectionOverlay,
  DetectionStatus,
  type DetectionDisplayFilters,
} from '@/components/detection'
import {
  TrackOverlay,
  TrackInspector,
} from '@/components/tracking'
import { detectionService } from '@/services/detection'
import { buildFeedSummary } from '@/services/detection/detectionSummary'

/**
 * LIVE CAMERA WALL — the detection-ready wall of camera feeds (§44/§161).
 *
 * Each tile is a (demo) feed with an optional detection overlay, a feed status
 * line and camera health. Selecting a box opens the shared DetectionInspector;
 * clicking the camera id opens the Single Camera Detail. Overlays and class /
 * confidence DISPLAY filters are frontend-only — they never alter stored data.
 * No detection here is presented as an alert, risk or threat.
 */
export function CameraWall() {
  const cameras = useCameraStore(s => s.cameras)
  const feeds = useDetectionStore(s => s.feeds)
  const fetchFeed = useDetectionStore(s => s.fetchFeed)
  const fetchAllHealth = useHealthStore(s => s.fetchAll)
  const healthEntries = useHealthStore(s => s.entries)

  const trackingFeeds = useTrackingStore(s => s.feeds)
  const fetchTrackFeed = useTrackingStore(s => s.fetchFeed)
  const selectedTrack = useTrackingStore(s => s.selected)
  const selectTrack = useTrackingStore(s => s.selectTrack)
  const histories = useTrackingStore(s => s.histories)

  const [overlayOn, setOverlayOn] = useState(true)
  const [classFilter, setClassFilter] = useState<DetectionResult['class'] | 'ALL'>('ALL')
  const [confidenceMin, setConfidenceMin] = useState<number | null>(null)
  const [selected, setSelected] = useState<DetectionResult | null>(null)

  const cameraIds = useMemo(() => cameras.map(c => c.id), [cameras])

  useEffect(() => {
    fetchAllHealth(cameraIds).catch(() => {})
    cameraIds.forEach(id => {
      fetchFeed(id).catch(() => {})
      fetchTrackFeed(id).catch(() => {})
    })
  }, [cameraIds, fetchAllHealth, fetchFeed, fetchTrackFeed])

  const displayFilters: DetectionDisplayFilters = useMemo(
    () => ({
      classes: classFilter === 'ALL' ? null : [classFilter],
      confidenceMin,
    }),
    [classFilter, confidenceMin]
  )

  const selectOnTile = useCallback((_cameraId: string, d: DetectionResult) => {
    setSelected(d)
  }, [])

  return (
    <div className="relative h-full flex flex-col overflow-y-auto p-4 gap-4 bg-bg">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4 flex-shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <h1 className="text-xl font-semibold text-slate-100 tracking-[0.08em] uppercase">PARAKH · Live Camera Wall</h1>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#3FCB8C]/10 text-[#3FCB8C] border border-[#3FCB8C]/20 tracking-widest">परख</span>
          </div>
          <p className="text-sm text-slate-500 mt-0.5">Detector output across all cameras — observations, not alerts</p>
        </div>
        <div className="flex items-center gap-2">
          {detectionService.source === 'DEMO' ? (
            <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-1 font-mono text-[9px] uppercase tracking-wider text-cyan-400">
              Demo mode
            </span>
          ) : (
            <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 font-mono text-[9px] uppercase tracking-wider text-emerald-400">
              Live backend
            </span>
          )}
          <button
            onClick={() => setOverlayOn(v => !v)}
            className="flex items-center gap-1.5 rounded-md border border-white/10 px-2.5 py-1.5 text-[11px] text-slate-300 hover:border-cyan-400/40 hover:text-cyan-300 transition-colors"
            aria-pressed={overlayOn}
          >
            {overlayOn ? <Eye size={13} aria-hidden /> : <EyeOff size={13} aria-hidden />}
            Overlays {overlayOn ? 'on' : 'off'}
          </button>
        </div>
      </header>

      {/* Display filters — only affect what is drawn on this wall */}
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400" title="Display filter — boxes are only hidden, never altered">
          <span className="text-slate-500">Class</span>
          <select
            className="rounded border border-white/10 bg-bg px-2 py-1.5 text-xs text-slate-300 focus:border-cyan-400/60 focus:outline-none"
            value={classFilter}
            onChange={e => setClassFilter(e.target.value as DetectionResult['class'] | 'ALL')}
          >
            <option value="ALL">All</option>
            <option value="PERSON">Person</option>
            <option value="VEHICLE">Vehicle</option>
            <option value="ANIMAL">Animal</option>
            <option value="OBJECT">Object</option>
            <option value="UNKNOWN">Unknown</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400" title="Display filter — frontend only">
          <span className="text-slate-500">Min confidence</span>
          <select
            className="rounded border border-white/10 bg-bg px-2 py-1.5 text-xs text-slate-300 focus:border-cyan-400/60 focus:outline-none"
            value={confidenceMin ?? ''}
            onChange={e => setConfidenceMin(e.target.value === '' ? null : Number(e.target.value))}
          >
            {/* Overlay filters compare against the 0–1 confidence ratio, so the
                option values are ratios too (the label carries the percent). */}
            <option value="">Confidence: any</option>
            <option value={0.5}>Show ≥ 50%</option>
            <option value={0.7}>Show ≥ 70%</option>
            <option value={0.85}>Show ≥ 85%</option>
          </select>
        </label>
      </div>

      <main className="flex-1 min-h-0 overflow-y-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-4">
          {cameras.map(camera => {
            const entry = feeds[camera.id]
            const feed = entry?.feed ?? null
            const health = healthEntries[camera.id]?.data ?? null
            const detections = feed?.detections ?? []
            const summary = feed ? buildFeedSummary(feed) : null

            return (
              <article
                key={camera.id}
                className="rounded-xl border border-border bg-surface p-3 flex flex-col gap-2"
                aria-label={`Camera ${camera.id} tile`}
              >
                <div className="relative" style={{ aspectRatio: '16 / 9' }}>
                  <CameraFeed camera={camera} tracks={[]} isNight={false}>
                    {overlayOn && (
                      <>
                        <DetectionOverlay
                          detections={detections}
                          selectedDetectionId={selected?.detectionId ?? null}
                          onSelect={d => selectOnTile(camera.id, d)}
                          displayFilters={displayFilters}
                        />
                        <TrackOverlay
                          tracks={trackingFeeds[camera.id]?.feed?.tracks ?? []}
                          selectedTrackId={selectedTrack?.trackId ?? null}
                          onSelect={t => selectTrack(t, camera.id)}
                        />
                      </>
                    )}
                  </CameraFeed>
                  <div className="absolute bottom-2 left-2 z-10 flex items-center gap-1.5">
                    {summary && summary.total > 0 && (
                      <span className="rounded bg-black/70 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
                        {summary.total} object{summary.total === 1 ? '' : 's'}
                      </span>
                    )}
                    {(trackingFeeds[camera.id]?.feed?.tracks.length ?? 0) > 0 && (
                      <span className="rounded bg-cyan-950/80 border border-cyan-500/30 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300">
                        TRK: {trackingFeeds[camera.id]!.feed!.tracks.length}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between gap-2">
                  <Link
                    to={`/camera/${camera.id}`}
                    className="font-mono text-xs text-slate-200 hover:text-cyan-300 transition-colors"
                  >
                    {camera.id}
                  </Link>
                  {health && <CameraHealthTile health={health} />}
                </div>

                <DetectionStatus
                  feedState={feed?.state ?? null}
                  inference={feed?.inference ?? null}
                  lastUpdatedAt={feed?.lastUpdatedAt ?? null}
                />

                {summary && summary.total > 0 && (
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    {(['PERSON', 'VEHICLE', 'ANIMAL'] as const).map(c => (
                      <span key={c} className="flex items-center gap-1 text-[10px] text-slate-500">
                        <span className="font-mono text-slate-300">{summary.byClass[c] ?? 0}</span>
                        <span>{c.charAt(0) + c.slice(1).toLowerCase()}</span>
                      </span>
                    ))}
                  </div>
                )}
              </article>
            )
          })}
        </div>
      </main>

      <DetectionInspector open={selected !== null} onClose={() => setSelected(null)} detection={selected} />

      <TrackInspector
        open={selectedTrack !== null}
        onClose={() => selectTrack(null, null)}
        track={selectedTrack}
      />
    </div>
  )
}