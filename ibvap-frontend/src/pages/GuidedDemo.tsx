import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import {
  Play,
  Pause,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Car,
  User,
  ShieldAlert,
  Video,
  Download,
  ExternalLink,
  Clock,
  Radio,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react'
import { DemoScene } from '@/components/demo/DemoScene'
import {
  getChapters,
  chapterForPath,
  defaultScenario,
  scenarios,
  DEMO_DURATION,
  DEMO_PLATE,
  demoClock,
  scenarioAt,
  type ScenarioId
} from '@/components/demo/scenario'

const SCENARIO_ICONS: Record<ScenarioId, typeof Car> = {
  vehicle: Car,
  person: User,
  animal: ShieldAlert,
  health: Video,
}

export function GuidedDemo() {
  const [params, setParams] = useSearchParams()
  const location = useLocation()
  const sceneRef = useRef<HTMLDivElement>(null)

  const caseId: ScenarioId = scenarios.find(s => s.id === params.get('case'))?.id ?? defaultScenario(location.pathname)
  const selectedCase = scenarios.find(s => s.id === caseId)!
  const chapters = useMemo(() => getChapters(caseId), [caseId])

  const requested = chapters.find(c => c.id === params.get('chapter')) ?? chapters.find(c => c.id === chapterForPath(location.pathname).id) ?? chapters[0]
  const [time, setTime] = useState<number>(requested?.at ?? 0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<number>(1)

  const state = scenarioAt(time, caseId)
  const chapterIndex = chapters.findIndex(c => c.id === state.chapter.id)

  useEffect(() => {
    setTime(requested?.at ?? 0)
    setPlaying(false)
  }, [requested])

  useEffect(() => {
    if (!playing || time >= DEMO_DURATION) return
    const timer = window.setTimeout(() => {
      setTime(t => Math.min(DEMO_DURATION, Math.round((t + 0.1) * 10) / 10))
    }, 100 / speed)
    return () => window.clearTimeout(timer)
  }, [playing, time, speed])

  function jump(index: number) {
    const chapter = chapters[Math.max(0, Math.min(chapters.length - 1, index))]
    setParams({ case: caseId, chapter: chapter.id }, { replace: true })
    setTime(chapter.at)
    setPlaying(false)
  }

  function handleSelectScenario(id: ScenarioId) {
    setParams({ case: id, chapter: 'detection' }, { replace: true })
    setTime(0)
    setPlaying(false)
  }

  const record = {
    simulation: true,
    disclaimer: 'Illustrated, scripted demonstration. Not real surveillance or production evidence.',
    scenario: caseId,
    subject: selectedCase.subject,
    plate: caseId === 'vehicle' ? DEMO_PLATE : null,
    scenarioDate: '2026-09-30',
    timezone: 'Asia/Kolkata',
    playbackSeconds: time,
    events: state.events.map(e => ({ ...e, captureTime: demoClock(e.at) }))
  }

  function exportRecord() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `PRAHAAR-${caseId}-simulation.json`
    anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <div className="flex flex-col flex-1 p-3 md:p-4 gap-2.5 bg-[#060c14] text-slate-100 min-h-0">
      {/* ── UNIFIED COMMAND TOOLBAR (HEADER + SCENARIOS + PLAYBACK + SCRUBBER) ─ */}
      <div className="bg-[#0b1522] border border-slate-800 rounded-xl p-3 flex flex-col gap-2.5 shadow-sm flex-shrink-0">
        {/* Row 1: Title & Scenarios & Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Identity */}
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
              <Radio className="h-3.5 w-3.5 animate-pulse" />
            </div>
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                Interactive Demo
                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                  SANDBOX
                </span>
              </span>
            </div>
          </div>

          {/* Scenario Tabs */}
          <div className="flex flex-wrap items-center gap-1 bg-[#070e17] p-1 rounded-lg border border-slate-800" role="tablist">
            {scenarios.map(s => {
              const Icon = SCENARIO_ICONS[s.id]
              const active = caseId === s.id
              return (
                <button
                  key={s.id}
                  role="tab"
                  aria-selected={active}
                  onClick={() => handleSelectScenario(s.id)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all ${
                    active
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className="h-3 w-3" />
                  <span>
                    {s.id === 'vehicle'
                      ? 'Vehicle Intrusion'
                      : s.id === 'person'
                      ? 'Person Trespass'
                      : s.id === 'animal'
                      ? 'Animal Filter'
                      : 'Camera Outage'}
                  </span>
                </button>
              )
            })}
          </div>

          {/* Playback Controls & Time */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (time >= DEMO_DURATION) setTime(0)
                setPlaying(p => !p || time >= DEMO_DURATION)
              }}
              className="flex items-center gap-1.5 rounded-md bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-bold px-3 py-1 text-xs transition-colors shadow-sm"
            >
              {time >= DEMO_DURATION ? (
                <>
                  <RotateCcw className="h-3 w-3" /> Replay
                </>
              ) : playing ? (
                <>
                  <Pause className="h-3 w-3" /> Pause
                </>
              ) : (
                <>
                  <Play className="h-3 w-3 fill-current" /> Play
                </>
              )}
            </button>

            <button
              onClick={() => {
                setTime(0)
                setPlaying(false)
              }}
              title="Reset"
              className="p-1 rounded-md border border-slate-700 bg-slate-850 hover:bg-slate-700 text-slate-300"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>

            <div className="flex items-center bg-slate-900 border border-slate-700 rounded-md p-0.5 text-xs">
              <button
                onClick={() => setSpeed(1)}
                className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                  speed === 1 ? 'bg-cyan-500/25 text-cyan-300' : 'text-slate-400 hover:text-white'
                }`}
              >
                1×
              </button>
              <button
                onClick={() => setSpeed(2)}
                className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                  speed === 2 ? 'bg-cyan-500/25 text-cyan-300' : 'text-slate-400 hover:text-white'
                }`}
              >
                2×
              </button>
            </div>

            <div className="flex items-center gap-1.5 text-xs font-mono text-cyan-300 bg-slate-900/90 px-2.5 py-1 rounded border border-slate-800">
              <Clock className="h-3 w-3 text-cyan-400" />
              <span>{demoClock(time)} IST</span>
              <span className="text-slate-500 text-[10px]">({Math.floor(time)}s)</span>
            </div>
          </div>
        </div>

        {/* Row 2: Timeline Scrubber with Step Controls */}
        <div className="flex items-center gap-3 pt-1 border-t border-slate-800/80">
          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              disabled={chapterIndex <= 0}
              onClick={() => jump(chapterIndex - 1)}
              className="p-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none"
              title="Previous step"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <span className="text-xs font-medium text-slate-300 min-w-[210px]">
              <strong className="text-cyan-300">Step {chapterIndex + 1}/10:</strong> {state.chapter.name}
            </span>
            <button
              disabled={chapterIndex >= chapters.length - 1}
              onClick={() => jump(chapterIndex + 1)}
              className="p-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none"
              title="Next step"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="flex-1 flex items-center">
            <input
              type="range"
              min={0}
              max={DEMO_DURATION}
              step={0.5}
              value={time}
              onChange={e => {
                setTime(Number(e.target.value))
                setPlaying(false)
              }}
              className="w-full accent-cyan-400 h-1.5 bg-slate-800 rounded cursor-pointer"
              aria-label="Timeline scrubber"
            />
          </div>
        </div>
      </div>

      {/* ── MAIN CONTENT (BALANCED VIEWPORT, NO AWKWARD SCROLLING) ───────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-2.5 flex-1 min-h-0">
        {/* LEFT COLUMN: CAMERA MONITOR + IMMEDIATE INSIGHT (7 COLS) */}
        <div className="lg:col-span-7 flex flex-col gap-2.5 min-h-0">
          {/* Simulated CCTV Feed */}
          <div ref={sceneRef} className="relative rounded-xl overflow-hidden border border-slate-800 bg-black shadow-md flex-shrink-0">
            <DemoScene time={time} scenario={caseId} className="max-h-[250px] xl:max-h-[290px] flex items-center justify-center bg-black" />
            <div className="absolute top-2 left-2 flex items-center gap-1.5 pointer-events-none">
              <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-black/80 border border-cyan-500/40 text-[10px] font-mono text-cyan-300 backdrop-blur-sm">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
                SIMULATED CCTV FEED
              </span>
            </div>
          </div>

          {/* Immediate Context Card */}
          <div className="bg-[#0b1522] border border-cyan-500/25 rounded-xl p-3 flex flex-col justify-between gap-2 flex-1 min-h-0">
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                  {state.chapter.module} · Step {chapterIndex + 1} of 10
                </span>
                <Link
                  to={state.chapter.route}
                  className="flex items-center gap-1 text-[11px] text-cyan-300 hover:text-cyan-100 hover:underline"
                >
                  <span>Open workspace</span>
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>

              <h2 className="text-xs font-bold text-white">
                {state.chapter.question}
              </h2>

              <p className="text-xs text-slate-300 leading-relaxed">
                {state.chapter.explanation}
              </p>
            </div>

            <div className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-2 flex items-start gap-1.5 text-[11px]">
              <span className="font-bold text-cyan-300 shrink-0">Watch:</span>
              <p className="text-slate-300">{state.chapter.action}</p>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: RULE ENGINE VERDICT + SIGHTINGS + AUDIT LOG (5 COLS) ─── */}
        <div className="lg:col-span-5 flex flex-col gap-2.5 min-h-0">
          {/* Card 1: Rule Engine Decision & Detection */}
          <div className="bg-[#0b1522] border border-slate-800 rounded-xl p-3 space-y-2.5 flex-shrink-0">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                Rule Engine Verdict
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                Subject: <strong className="text-slate-200">{selectedCase.subject}</strong>
              </span>
            </div>

            {/* Verdict Status Box */}
            <div
              className={`rounded-lg border p-2.5 flex items-start gap-2 ${
                state.alert
                  ? 'border-rose-500/50 bg-rose-500/10 text-rose-200'
                  : caseId === 'animal' && time >= 42
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'
                  : state.outage
                  ? 'border-amber-500/40 bg-amber-500/10 text-amber-200'
                  : 'border-cyan-500/30 bg-cyan-500/5 text-cyan-200'
              }`}
            >
              {state.alert ? (
                <ShieldAlert className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              ) : caseId === 'animal' && time >= 42 ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : state.outage ? (
                <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
              )}
              <div className="min-w-0 flex-1">
                <div className="text-xs font-bold uppercase tracking-wide">
                  {caseId === 'health'
                    ? state.outage
                      ? 'Camera Outage / Signal Lost'
                      : 'Baseline Health Clear'
                    : caseId === 'animal' && time >= 42
                    ? 'Non-Threat Wildlife Excluded'
                    : state.alert
                    ? 'Restricted Zone Intrusion Alert'
                    : state.inside
                    ? 'Zone Entered · Evaluating Dwell'
                    : 'Normal Activity / No Alert'}
                </div>
                <div className="text-[10px] text-slate-300 mt-0.5 leading-snug">
                  {caseId === 'animal'
                    ? 'Perimeter configured for people/vehicles. Wildlife crossing does not trigger alarms.'
                    : caseId === 'health'
                    ? state.outage
                      ? 'CAM-12 offline. Tracking safely paused to avoid ghost detections.'
                      : 'Camera image clear and online.'
                    : state.alert
                    ? 'Dwell time > 3.0s exceeded in restricted zone. Incident created with full evidence.'
                    : state.inside
                    ? `Inside zone: ${(time - 39).toFixed(1)}s / 3.0s dwell threshold`
                    : 'Target outside restricted perimeter.'}
                </div>
              </div>
            </div>

            {/* Target & Pipeline Row */}
            <div className="grid grid-cols-3 gap-1.5 text-center pt-1 border-t border-slate-800">
              <div className="bg-slate-900/90 p-1.5 rounded border border-slate-800">
                <div className="text-[9px] text-slate-400 uppercase">Detection</div>
                <div className="text-xs font-mono font-bold text-white truncate">
                  {caseId === 'vehicle' ? (time >= 8 ? DEMO_PLATE : 'Pending') : caseId === 'health' ? (state.outage ? 'FAULT' : 'OK') : caseId.toUpperCase()}
                </div>
              </div>
              <div className="bg-slate-900/90 p-1.5 rounded border border-slate-800">
                <div className="text-[9px] text-slate-400 uppercase">Active Cam</div>
                <div className="text-xs font-mono font-bold text-cyan-300 truncate">
                  {state.camera}
                </div>
              </div>
              <div className="bg-slate-900/90 p-1.5 rounded border border-slate-800">
                <div className="text-[9px] text-slate-400 uppercase">Sightings</div>
                <div className="text-xs font-mono font-bold text-cyan-300 truncate">
                  {state.sightings.length} / 3
                </div>
              </div>
            </div>

            {/* Multi-Camera Sightings Stepper */}
            <div className="flex items-center justify-between gap-1 text-[10px] font-mono bg-slate-950 p-1.5 rounded border border-slate-800">
              {['CAM-07', 'CAM-08', 'CAM-12'].map((cam, idx) => {
                const reached = state.sightings.some(s => s.camera === cam)
                return (
                  <div key={cam} className="flex items-center gap-1 flex-1 justify-center">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        reached ? 'bg-cyan-400' : 'bg-slate-700'
                      }`}
                    />
                    <span className={reached ? 'text-cyan-200 font-semibold' : 'text-slate-500'}>
                      {cam}
                    </span>
                    {idx < 2 && <span className="text-slate-600">→</span>}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Card 2: Live Chronological Audit Events Feed */}
          <div className="bg-[#0b1522] border border-slate-800 rounded-xl p-3 flex flex-col flex-1 min-h-0">
            <div className="flex items-center justify-between mb-1.5 flex-shrink-0">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                Audit Trail ({state.events.length} Events)
              </span>
              <button
                onClick={exportRecord}
                className="flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-200 font-medium"
              >
                <Download className="h-3 w-3" />
                <span>Export JSON</span>
              </button>
            </div>

            {/* Audit log scroll container: clean internal scroll */}
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 max-h-[190px] xl:max-h-[240px]">
              {state.events.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-28 text-center text-slate-500 text-xs">
                  <Play className="h-5 w-5 stroke-1 text-slate-600 mb-1" />
                  <span>Click <strong>Play</strong> to watch real-time events.</span>
                </div>
              ) : (
                [...state.events].reverse().map(event => (
                  <div
                    key={`${event.at}-${event.camera}`}
                    className={`border-l-2 pl-2 py-1 text-xs rounded-r ${
                      event.kind === 'alert'
                        ? 'border-rose-400 bg-rose-500/5'
                        : event.kind === 'health'
                        ? 'border-amber-400 bg-amber-500/5'
                        : 'border-cyan-500/60 bg-cyan-500/5'
                    }`}
                  >
                    <div className="flex items-center justify-between font-mono text-[9px]">
                      <span className="text-cyan-300">{demoClock(event.at)} IST</span>
                      <span className="text-slate-400">{event.camera}</span>
                    </div>
                    <div className="font-semibold text-slate-200 text-[10px] mt-0.5">
                      {event.title}
                    </div>
                    <div className="text-[10px] text-slate-400 leading-tight">
                      {event.detail}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
