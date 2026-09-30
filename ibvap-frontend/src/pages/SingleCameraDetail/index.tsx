import { useCallback, useEffect, useMemo, useState } from 'react'
import { useCameraStore, useFenceStore, useRiskStore } from '@/store'
import { zoneService } from '@/services/zoneService'
import { incidentService } from '@/services/incidentService'
import { asApiError } from '@/services/api'
import {
  useCameraFeed,
  useCameraHealth,
  useCameraCorrelation,
  useDetectionSelection,
  useTrackPipeline,
  useCameraTracks,
  useTrackSelection,
} from '@/hooks'
import { CameraFeed } from '@/components/camera/CameraFeed'
import {
  CameraHealthDetails,
  CameraHealthRail,
  CameraHealthBadge,
  TechnicalDiagnosticsDrawer,
} from '@/components/camera-health'
import { Drawer, Skeleton } from '@/components/ui'
import { FenceZonePanel } from '@/components/fence/FenceZonePanel'
import { RiskFactorsPanel } from '@/components/risk/RiskFactorsPanel'
import { SeverityBadge } from '@/components/risk/SeverityBadge'
import { IncidentTimeline } from '@/components/timeline/IncidentTimeline'
import { CorrelationSummary } from '@/components/correlation'
import {
  DetectionInspector,
  DetectionList,
  DetectionOverlay,
  DetectionStatus,
  type DetectionDisplayFilters,
} from '@/components/detection'
import {
  TrackOverlay,
  TrackInspector,
  TrackList,
} from '@/components/tracking'
import { latestRisk } from '@/store/riskState'
import type { DetectionResult } from '@/types/detection'
import { FEED_ASPECT } from '@/components/camera/feedViewport'

export function SingleCameraDetail() {
  const {
    cameras,
    selectedCameraId,
    tracks,
    isNight,
    setSelectedCamera,
    toggleNightMode,
  } = useCameraStore()

  const { setZones } = useFenceStore()
  const { incidents, lastEvaluations, setIncidents, setError: setRiskError, error: riskError } = useRiskStore()
  const [events, setEvents] = useState<import('@/types').EventRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const camera = cameras.find(c => c.id === selectedCameraId) ?? cameras[0]

  const { running } = useTrackPipeline(camera.id)
  const { health, state: healthState, error: healthError, retry: retryHealth } = useCameraHealth(camera.id)
  const { groups: relatedGroups, state: relatedState, error: relatedError, retry: retryRelated } = useCameraCorrelation(camera.id)
  const { selected, select } = useDetectionSelection()
  const [healthOpen, setHealthOpen] = useState(false)
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false)

  // Detection feed for the current camera (Component 5).
  const { feed, state: feedState, error: feedError, retry: retryFeed } = useCameraFeed(camera.id)
  const detections = feed?.detections ?? []

  // Tracking feed for the current camera (Component 6).
  const {
    feed: trackingFeed,
    tracks: cameraTracks,
    state: trackingState,
    error: trackingError,
    retry: retryTracking,
  } = useCameraTracks(camera.id)

  const { selected: selectedTrack, selectTrack } = useTrackSelection()

  const [panelTab, setPanelTab] = useState<'tracks' | 'detections'>('tracks')

  // Detection overlay display filters — local UI state only.
  const [overlayOn, setOverlayOn] = useState(true)
  const [classFilter, setClassFilter] = useState<DetectionResult['class'] | 'ALL'>('ALL')
  const [confidenceMin, setConfidenceMin] = useState<number | null>(null)
  const displayFilters: DetectionDisplayFilters = useMemo(
    () => ({ classes: classFilter === 'ALL' ? null : [classFilter], confidenceMin }),
    [classFilter, confidenceMin]
  )

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [zoneData, incidentData, eventData] = await Promise.all([
        zoneService.list(camera.id, false),
        incidentService.list(camera.id, 20),
        incidentService.listEvents(camera.id, 30),
      ])
      setZones(zoneData)
      setIncidents(incidentData)
      setEvents(eventData)
    } catch (err) {
      const msg = asApiError(err).message
      setLoadError(msg)
      setRiskError(msg)
    } finally {
      setLoading(false)
    }
  }, [camera.id, setZones, setIncidents, setRiskError])

  // Load zones, incidents & events on camera change (with cancellation)
  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      setLoadError(null)
      try {
        const [zoneData, incidentData, eventData] = await Promise.all([
          zoneService.list(camera.id, false),
          incidentService.list(camera.id, 20),
          incidentService.listEvents(camera.id, 30),
        ])
        if (!cancelled) {
          setZones(zoneData)
          setIncidents(incidentData)
          setEvents(eventData)
        }
      } catch (err) {
        if (!cancelled) {
          const msg = asApiError(err).message
          setLoadError(msg)
          setRiskError(msg)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [camera.id, setZones, setIncidents, setRiskError])

  const risk = latestRisk(lastEvaluations)
  // Reliability/confidence arrive with the evaluated observation stream;
  // the panel reports what the backend saw, never a fabricated score.
  const uncertainty = useMemo(() => {
    const latest = lastEvaluations[0]
    if (!latest) return null
    return {
      trackId: latest.track.track_id,
      zones: latest.evaluation.zones.length,
      inside: latest.evaluation.zones.filter(z => z.is_inside).map(z => z.zone_name),
    }
  }, [lastEvaluations])

  const activeTracks = tracks.length

  return (
    <div className="h-full flex flex-col overflow-hidden bg-[#080c12]">
      {/* Camera header: identity → liveness → sector → risk */}
      <header className="flex items-center justify-between gap-3 h-14 px-4 border-b border-[#1e2d40] bg-[#0d1117]/80">
        <div className="flex items-center gap-3 min-w-0">
          <label htmlFor="camera-select" className="sr-only">Select camera</label>
          <select
            id="camera-select"
            className="rounded border border-white/10 bg-[#080c12] px-2 py-1 text-xs text-slate-200 focus:border-cyan-400/60 focus:outline-none"
            value={selectedCameraId}
            onChange={e => setSelectedCamera(e.target.value)}
          >
            {cameras.map(c => (
              <option key={c.id} value={c.id}>
                {c.label} ({c.id})
              </option>
            ))}
          </select>
          {camera.sectorProfile && (
            <span className="hidden md:inline-flex flex-col leading-tight" title="Deployment sector profile">
              <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-600">Sector profile</span>
              <span className="font-mono text-[10px] text-slate-400">{camera.sectorProfile}</span>
            </span>
          )}
          <button
            onClick={toggleNightMode}
            className="rounded border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-300 hover:bg-white/10 transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500/60"
            title={isNight ? 'Switch to day mode' : 'Switch to night mode'}
            aria-pressed={isNight}
          >
            {isNight ? 'Night' : 'Day'}
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setHealthOpen(true)}
            className="flex items-center gap-1.5 px-2 py-1 rounded border border-white/10 bg-white/5 text-xs text-slate-300 hover:bg-white/10 transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500/60 cursor-pointer"
            title="Inspect camera health & telemetry"
          >
            <CameraHealthBadge status={health?.status ?? 'UNKNOWN'} cameraId={camera.id} />
          </button>
          {risk && <SeverityBadge severity={risk.severity} score={risk.risk_score} />}
          <span className="flex items-center gap-1.5 font-mono text-[10px] text-slate-500" role="status">
            <span className={running ? 'h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse-dot' : 'h-1.5 w-1.5 rounded-full bg-slate-500'} aria-hidden />
            {running ? 'DEMO MODE' : 'IDLE'}
          </span>
          <span className="hidden lg:inline font-mono text-[10px] text-slate-600 tabular-nums" title="Active tracks">
            TRK {activeTracks}
          </span>
          <button
            onClick={() => setOverlayOn(v => !v)}
            className="flex items-center gap-1.5 rounded border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-300 hover:bg-white/10 transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500/60"
            aria-pressed={overlayOn}
          >
            Overlays {overlayOn ? 'on' : 'off'}
          </button>
        </div>
      </header>

      {(loadError || riskError) && !loading && (
        <div role="alert" className="mx-4 mt-3 rounded-md border border-red-500/30 bg-red-500/5 px-3 py-2">
          <p className="text-xs font-semibold text-red-400">Failed to load camera data</p>
          <p className="text-[11px] text-red-300/80">{loadError ?? riskError} Impact: fence, risk and timeline may be stale.</p>
          <button
            className="mt-1 text-[11px] font-medium text-slate-200 underline underline-offset-2 hover:text-white"
            onClick={() => load()}
          >
            Retry
          </button>
        </div>
      )}

      {/* Main content: ~70% viewport column, ~30% information rail */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left column: viewport + timeline */}
        <section className="flex-1 flex flex-col min-w-0 p-4 gap-4 overflow-y-auto" style={{ flex: '0 1 70%' }}>
          <div className="relative" style={{ aspectRatio: FEED_ASPECT, maxHeight: 'calc(100vh - 320px)', minHeight: 280 }}>
            {loading ? (
              <div className="absolute inset-0 rounded-xl border border-[#1e2d40] bg-[#0d1117] animate-pulse" aria-label="Loading camera feed" role="status">
                <span className="sr-only">Loading camera feed…</span>
              </div>
            ) : (
              <CameraFeed camera={camera} tracks={tracks} isNight={isNight}>
                {overlayOn && (
                  <>
                    <DetectionOverlay
                      detections={detections}
                      selectedDetectionId={selected?.detectionId ?? null}
                      onSelect={d => select(d, camera.id)}
                      displayFilters={displayFilters}
                    />
                    <TrackOverlay
                      tracks={cameraTracks}
                      selectedTrackId={selectedTrack?.trackId ?? null}
                      onSelect={t => selectTrack(t, camera.id)}
                    />
                  </>
                )}
                <div className="absolute left-2 bottom-2 z-10">
                  <FenceModeBadge />
                </div>
<DetectionStatus
                  feedState={feed?.state ?? null}
                  inference={feed?.inference ?? null}
                  lastUpdatedAt={feed?.lastUpdatedAt ?? null}
                  className="absolute right-2 bottom-2 z-10"
                />
              </CameraFeed>
            )}
          </div>

          <div className="w-full">
            <FenceZonePanel />
          </div>

          <IncidentTimeline incidents={incidents} events={events} />
        </section>

        {/* Right rail: uncertainty → health → risk */}
        <aside className="flex flex-col gap-4 p-4 border-l border-[#1e2d40] bg-[#0d1117]/60 overflow-y-auto shrink-0" style={{ flex: '0 0 30%', minWidth: 300, maxWidth: 400 }}>
          <UncertaintyPanel
            trackId={uncertainty?.trackId ?? null}
            zonesChecked={uncertainty?.zones ?? null}
            inside={uncertainty?.inside ?? null}
          />

          {healthState === 'loading' && !health ? (
            <div role="status" aria-label="Loading camera health">
              <Skeleton className="h-44 w-full" />
            </div>
          ) : health ? (
            <>
              <CameraHealthRail health={health} onOpenDetails={() => setHealthOpen(true)} />
              {healthState === 'last-known' && (
                <p role="status" className="rounded-md border border-amber-500/30 bg-amber-500/5 px-2 py-1.5 text-[11px] text-amber-300">
                  Showing last known state{healthError ? ` — ${healthError}` : ''}.
                  <button onClick={() => retryHealth()} className="ml-1 underline underline-offset-2">Retry</button>
                </p>
              )}
            </>
          ) : (
            <div role="alert" className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-300">Camera health unavailable</p>
              <p className="mt-1 text-[11px] text-slate-500">
                {healthError ?? 'Health telemetry could not be retrieved.'} Fence, risk and feed continue where possible.
              </p>
              <div className="mt-2 flex gap-3">
                <button onClick={() => retryHealth()} className="text-[11px] font-medium text-cyan-400 hover:text-cyan-300 underline underline-offset-2">
                  Retry
                </button>
              </div>
            </div>
          )}

          <Drawer
            open={healthOpen}
            onClose={() => setHealthOpen(false)}
            title={`Sensor Health · ${camera.id}`}
            width="w-[520px]"
          >
            <div className="p-4 overflow-y-auto">
              <p className="text-[11px] text-slate-400 mb-3">
                Comprehensive 12-section operational telemetry, baseline deviation, and border coverage diagnostics.
              </p>
              {health ? (
                <CameraHealthDetails
                  health={health}
                  onOpenDiagnostics={() => setDiagnosticsOpen(true)}
                />
              ) : (
                <p className="text-[12px] text-slate-500">No health telemetry for this camera.</p>
              )}
            </div>
          </Drawer>

          <TechnicalDiagnosticsDrawer
            open={diagnosticsOpen}
            onClose={() => setDiagnosticsOpen(false)}
            health={health}
          />

          <RelatedEventsPanel groups={relatedGroups} state={relatedState} error={relatedError} onRetry={retryRelated} />

          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4" aria-label="Tracking and Detections">
            {/* Tab Selector between Tracks and Detections */}
            <div className="flex items-center justify-between gap-2 border-b border-[#1e2d40] pb-2 mb-3">
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setPanelTab('tracks')}
                  className={`px-2.5 py-1 text-xs font-mono rounded transition-colors ${
                    panelTab === 'tracks'
                      ? 'bg-cyan-500/15 text-cyan-300 font-semibold border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Movement Tracks ({cameraTracks.length})
                </button>
                <button
                  type="button"
                  onClick={() => setPanelTab('detections')}
                  className={`px-2.5 py-1 text-xs font-mono rounded transition-colors ${
                    panelTab === 'detections'
                      ? 'bg-cyan-500/15 text-cyan-300 font-semibold border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Detections ({detections.length})
                </button>
              </div>
            </div>

            {panelTab === 'tracks' ? (
              <div>
                <TrackList
                  tracks={cameraTracks}
                  selectedId={selectedTrack?.trackId ?? null}
                  onSelect={t => selectTrack(t, camera.id)}
                  feedState={trackingFeed?.state}
                  state={trackingState}
                  error={trackingError}
                  onRetry={() => retryTracking()}
                  hideCamera
                />
                <p className="mt-2 text-[10px] leading-snug text-slate-500">
                  Observation continuity hypotheses for {camera.id}. Click a track to inspect observation history, trajectory, and downstream references.
                </p>
              </div>
            ) : (
              <div>
                <div className="mt-1">
                  <DetectionList
                    detections={detections}
                    selectedId={selected?.detectionId ?? null}
                    onSelect={d => select(d, camera.id)}
                    feedState={feed?.state}
                    state={feedState === 'loading' || feedState === 'idle' ? 'loading' : feedState === 'error' ? 'error' : 'ready'}
                    error={feedError}
                    onRetry={() => retryFeed()}
                    hideCamera
                  />
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-1 text-[11px] text-slate-500" title="Display filter — boxes are only hidden, never altered">
                    Class filter
                    <select
                      className="rounded border border-white/10 bg-[#080c12] px-1.5 py-1 text-[11px] text-slate-300 focus:border-cyan-400/60 focus:outline-none"
                      value={classFilter}
                      onChange={e => setClassFilter(e.target.value as DetectionResult['class'] | 'ALL')}
                    >
                      <option value="ALL">All</option>
                      {(['PERSON', 'VEHICLE', 'ANIMAL', 'OBJECT', 'UNKNOWN'] as const).map(c => (
                        <option key={c} value={c}>{c.charAt(0) + c.slice(1).toLowerCase()}</option>
                      ))}
                    </select>
                  </label>
                  <label className="flex items-center gap-1 text-[11px] text-slate-500" title="Display filter — frontend only">
                    Min confidence
                    <select
                      className="rounded border border-white/10 bg-[#080c12] px-1.5 py-1 text-[11px] text-slate-300 focus:border-cyan-400/60 focus:outline-none"
                      value={confidenceMin ?? ''}
                      onChange={e => setConfidenceMin(e.target.value === '' ? null : Number(e.target.value))}
                    >
                      <option value="">Any</option>
                      <option value={0.5}>≥ 50%</option>
                      <option value={0.7}>≥ 70%</option>
                      <option value={0.85}>≥ 85%</option>
                    </select>
                  </label>
                  {feedState === 'error' && (
                    <button onClick={() => retryFeed()} className="text-[11px] text-cyan-400 underline underline-offset-2 hover:text-cyan-300">
                      Retry
                    </button>
                  )}
                </div>
                <p className="mt-2 text-[10px] leading-snug text-slate-600">
                  Detector observations for {camera.id}. Nothing here is an alert; risk and correlation live in their own engines.
                </p>
              </div>
            )}
          </section>

          <div className="flex-1 flex flex-col min-h-0">
            {risk ? (
              <RiskFactorsPanel
                score={risk.risk_score}
                severity={risk.severity}
                factors={risk.factors}
                reliability={selectedTrack?.cameraHealthContext?.reliability ?? 'HIGH'}
                cameraHealthState={camera.status}
                cameraId={camera.id}
                trackId={selectedTrack?.trackId ?? null}
              />
            ) : (
              <div className="flex-1 flex items-center justify-center rounded-xl border border-dashed border-slate-700 p-4 text-center">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">No active incident</p>
                  <p className="mt-1 text-[11px] text-slate-500 max-w-xs">
                    No scored zone-entry incident is currently associated with this camera. Demo tracks raise incidents as they breach the fence.
                  </p>
                </div>
              </div>
            )}
          </div>
        </aside>
      </main>

      <DetectionInspector
        open={selected !== null}
        onClose={() => select(null, camera.id)}
        detection={selected}
      />

      <TrackInspector
        open={selectedTrack !== null}
        onClose={() => selectTrack(null, camera.id)}
        track={selectedTrack}
      />
    </div>
  )
}

/** Reliability / uncertainty rail block — reports evaluated observations only. */
function UncertaintyPanel({ trackId, zonesChecked, inside }: {
  trackId: string | null
  zonesChecked: number | null
  inside: string[] | null
}) {
  if (!trackId) {
    return (
      <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4" aria-label="Observation reliability">
        <h3 className="text-sm font-semibold text-slate-200">Observation Reliability</h3>
        <p className="mt-2 text-[11px] text-slate-500">
          No evaluated observation yet. Reliability appears here once the backend evaluates a track.
        </p>
        <dl className="mt-2 space-y-1 text-[11px]">
          <div className="flex justify-between"><dt className="text-slate-500">Detection confidence</dt><dd className="font-mono text-slate-400">N/A</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">Frame quality</dt><dd className="font-mono text-slate-400">N/A</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">Viewpoint stability</dt><dd className="font-mono text-slate-400">N/A</dd></div>
        </dl>
      </section>
    )
  }
  return (
    <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4" aria-label="Observation reliability">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Observation Reliability</h3>
        <span className="font-mono text-[10px] text-slate-500" title="Evaluated track">{trackId}</span>
      </div>
      <dl className="mt-2 space-y-1 text-[11px]">
        <div className="flex justify-between"><dt className="text-slate-500">Zones evaluated</dt><dd className="font-mono text-slate-200 tabular-nums">{zonesChecked ?? 'N/A'}</dd></div>
        <div className="flex justify-between"><dt className="text-slate-500">Inside now</dt><dd className="font-mono text-slate-200">{inside && inside.length > 0 ? inside.join(', ') : 'none'}</dd></div>
        <div className="flex justify-between"><dt className="text-slate-500">Detection confidence</dt><dd className="font-mono text-slate-400">backend-scored</dd></div>
        <div className="flex justify-between"><dt className="text-slate-500">Occlusion</dt><dd className="font-mono text-slate-400">N/A</dd></div>
      </dl>
      <p className="mt-2 text-[10px] text-slate-600">Uncertainty penalties, if any, are listed under Risk Assessment.</p>
    </section>
  )
}

function FenceModeBadge() {
  const { mode, draftPoints } = useFenceStore()
  if (mode === 'view') return null
  const valid = draftPoints.length >= 3
  return (
    <div className="rounded-lg border border-amber-500/40 bg-black/70 px-2.5 py-1.5 text-[11px] font-medium text-amber-300 flex items-center gap-1.5" role="status">
      {mode === 'draw' ? 'Fence edit mode' : 'Fence reshape mode'}
      <span className="font-mono text-[10px] text-amber-500/80 tabular-nums">points {draftPoints.length}</span>
      <span className="font-mono text-[10px] tabular-nums">{valid ? '· valid polygon' : '· need 3+'}</span>
    </div>
  )
}

/** Related-events context for a single camera (§164). Lightweight group list only. */
function RelatedEventsPanel({ groups, state, error, onRetry }: {
  groups: import('@/types/eventCorrelation').CorrelationGroup[]
  state: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  onRetry: () => void
}) {
  return (
    <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4" aria-label="Related events">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Related events</h3>
        <span className="font-mono text-[10px] text-slate-500">{groups.length}</span>
      </div>
      {state === 'loading' && groups.length === 0 && (
        <p className="mt-2 text-[11px] text-slate-500" role="status">Loading…</p>
      )}
      {state === 'error' && groups.length === 0 && (
        <p className="mt-2 text-[11px] text-slate-500">
          Could not load related events{error ? ` — ${error}` : ''}.
          <button onClick={onRetry} className="ml-1 text-cyan-400 underline underline-offset-2">Retry</button>
        </p>
      )}
      {state !== 'loading' && groups.length === 0 && (
        <p className="mt-2 text-[11px] text-slate-500">No correlated activity involving this camera in the current window.</p>
      )}
      {groups.length > 0 && (
        <div className="mt-3 space-y-2">
          {groups.map(g => (
            <CorrelationSummary key={g.correlationId} group={g} density="compact" to={`/incident/${g.correlationId}`} />
          ))}
        </div>
      )}
    </section>
  )
}
