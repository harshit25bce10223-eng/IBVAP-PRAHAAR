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
  AlertTriangle,
  Zap,
  ShieldCheck,
  Target,
  FileCheck,
  Eye,
  Activity,
  Layers,
  Sparkles
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

const SCENARIO_DETAILS: Record<ScenarioId, { title: string; subtitle: string; icon: typeof Car; badge: string; color: string }> = {
  vehicle: {
    title: 'Vehicle Intrusion & Plate Trail',
    subtitle: 'ANPR Detection ➔ Cross-Camera Handoff ➔ 3s Dwell Breach Alert',
    icon: Car,
    badge: 'PRIORITY 1 HIGH THREAT',
    color: 'border-cyan-500/40 text-cyan-300'
  },
  person: {
    title: 'Pedestrian Perimeter Breach',
    subtitle: 'Track-01 Detection ➔ Zone Infiltration ➔ Dwell Alert ➔ QRT Intercept',
    icon: User,
    badge: 'STEALTH INFILTRATION',
    color: 'border-rose-500/40 text-rose-300'
  },
  animal: {
    title: 'Wildlife Crossing (False Alarm Filter)',
    subtitle: 'Animal Classification ➔ Spatial Rule ➔ 94% False Alarm Suppression',
    icon: ShieldCheck,
    badge: 'FALSE ALARM SUPPRESSED',
    color: 'border-emerald-500/40 text-emerald-300'
  },
  health: {
    title: 'Sensor Outage & Zero-Trust Mesh',
    subtitle: 'Optical Degradation ➔ Stale Frame Lock ➔ Offline SAKSHAM Sync',
    icon: Video,
    badge: 'FAIL-SAFE DEFENSE',
    color: 'border-amber-500/40 text-amber-300'
  }
}

// 5 Key Story Beats that judges can immediately click to jump to key moments
const STORY_BEATS: { label: string; at: number; act: string }[] = [
  { label: 'Checkpoint Entry', at: 8, act: 'Act 1' },
  { label: 'Cross-Cam Handoff', at: 28, act: 'Act 2' },
  { label: 'Perimeter Breach', at: 42, act: 'Act 3' },
  { label: 'Sensor Outage & Mesh', at: 62, act: 'Act 4' },
  { label: 'Court Evidence Signed', at: 113, act: 'Act 5' },
]

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
  const activeScenarioMeta = SCENARIO_DETAILS[caseId]

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

  // Simulated cryptographic evidence digest (matches PRAMAAN architecture)
  const evidenceDigest = useMemo(() => {
    const seed = `${caseId}-${selectedCase.subject}-${Math.floor(time / 10)}`
    let hash = 0
    for (let i = 0; i < seed.length; i++) hash = (hash << 5) - hash + seed.charCodeAt(i)
    const hex = Math.abs(hash).toString(16).padStart(8, '0')
    return `sha256:7f83b165...${hex.substring(0, 6)}`
  }, [caseId, selectedCase.subject, time])

  const record = {
    simulation: true,
    platform: 'PRAHAAR Integrated Border Video Analytics Platform',
    sha256Proof: evidenceDigest,
    disclaimer: 'Scripted operational demonstration for SSB evaluation. Demonstrates full stack AI + Rule Engine + Evidence Ledger.',
    scenario: caseId,
    subject: selectedCase.subject,
    plate: caseId === 'vehicle' ? DEMO_PLATE : null,
    scenarioDate: '2026-09-30',
    timezone: 'Asia/Kolkata',
    playbackSeconds: time,
    verdict: state.alert
      ? 'CRITICAL_INTRUSION_ALERT'
      : caseId === 'animal' && time >= 42
      ? 'NON_THREAT_FILTERED'
      : state.outage
      ? 'SENSOR_HEALTH_FAILOVER'
      : 'SURVEILLANCE_NORMAL',
    events: state.events.map(e => ({ ...e, captureTime: demoClock(e.at) }))
  }

  function exportRecord() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `PRAHAAR-Forensic-${caseId}-Record.json`
    anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <div className="flex flex-col flex-1 p-2.5 md:p-3.5 gap-2.5 bg-[#050b12] text-slate-100 min-h-0 font-sans">
      {/* ── TOP BANNER: MISSION IDENTITY & JUDGE HIGHLIGHTS ────────────────── */}
      <div className="bg-[#0b1420] border border-cyan-500/25 rounded-xl px-3.5 py-2 flex flex-wrap items-center justify-between gap-2.5 shadow-lg shadow-black/40 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/30 to-blue-600/30 text-cyan-300 border border-cyan-400/40 shadow-inner">
            <Radio className="h-4 w-4 animate-pulse text-cyan-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xs md:text-sm font-black tracking-wider text-white uppercase">
                प्रहार · Interactive Storyline Demo
              </h1>
              <span className="hidden sm:inline-flex items-center gap-1 text-[9px] font-mono px-2 py-0.5 rounded-full bg-cyan-400/15 text-cyan-300 border border-cyan-400/30 font-bold">
                <Sparkles className="h-2.5 w-2.5 text-cyan-400" /> SIH GRAND FINALE READY
              </span>
            </div>
            <p className="text-[10px] text-slate-400">
              End-to-End Operational Narrative · Edge AI ➔ Spatial Rule Engine ➔ Offline SAKSHAM Mesh ➔ PRAMAAN Ledger
            </p>
          </div>
        </div>

        {/* 4 Winning Differentiators for Judges */}
        <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
          <div className="flex items-center gap-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 px-2 py-0.5 rounded">
            <ShieldCheck className="h-3 w-3 text-emerald-400" />
            <span>94% False Alarm Drop</span>
          </div>
          <div className="flex items-center gap-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 px-2 py-0.5 rounded">
            <Zap className="h-3 w-3 text-cyan-400" />
            <span>&lt;300ms Edge Latency</span>
          </div>
          <div className="flex items-center gap-1 bg-amber-500/10 border border-amber-500/30 text-amber-300 px-2 py-0.5 rounded">
            <Activity className="h-3 w-3 text-amber-400" />
            <span>SAKSHAM Offline Mesh</span>
          </div>
          <div className="flex items-center gap-1 bg-blue-500/10 border border-blue-500/30 text-blue-300 px-2 py-0.5 rounded">
            <FileCheck className="h-3 w-3 text-blue-400" />
            <span>SHA-256 Legal Proof</span>
          </div>
        </div>
      </div>

      {/* ── STORYLINE SELECTOR & PLAYBACK CONTROL STRIP ─────────────────────── */}
      <div className="bg-[#09111c] border border-slate-800 rounded-xl p-2.5 flex flex-col gap-2 shadow-sm flex-shrink-0">
        {/* Row 1: 4 Story Tabs & Playback */}
        <div className="flex flex-wrap items-center justify-between gap-2.5">
          {/* Scenario Tabs */}
          <div className="flex flex-wrap items-center gap-1.5 bg-[#060c14] p-1 rounded-lg border border-slate-800" role="tablist">
            {scenarios.map(s => {
              const meta = SCENARIO_DETAILS[s.id]
              const Icon = meta.icon
              const active = caseId === s.id
              return (
                <button
                  key={s.id}
                  role="tab"
                  aria-selected={active}
                  onClick={() => handleSelectScenario(s.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all ${
                    active
                      ? 'bg-gradient-to-r from-cyan-500 to-cyan-400 text-slate-950 font-bold shadow-md shadow-cyan-500/20'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/60 font-medium'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{meta.title.split('(')[0]}</span>
                </button>
              )
            })}
          </div>

          {/* Quick Mission Play Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (time >= DEMO_DURATION) setTime(0)
                setPlaying(p => !p || time >= DEMO_DURATION)
              }}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-400 to-cyan-300 hover:from-cyan-300 hover:to-cyan-200 text-slate-950 font-black px-4 py-1.5 text-xs transition-all shadow-md shadow-cyan-400/25"
            >
              {time >= DEMO_DURATION ? (
                <>
                  <RotateCcw className="h-3.5 w-3.5" /> Replay Mission
                </>
              ) : playing ? (
                <>
                  <Pause className="h-3.5 w-3.5" /> Pause
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current" /> Play Storyline
                </>
              )}
            </button>

            <button
              onClick={() => {
                setTime(0)
                setPlaying(false)
              }}
              title="Reset Timeline"
              className="p-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>

            <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5 text-xs">
              <button
                onClick={() => setSpeed(1)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  speed === 1 ? 'bg-cyan-500/25 text-cyan-300' : 'text-slate-400 hover:text-white'
                }`}
              >
                1×
              </button>
              <button
                onClick={() => setSpeed(2)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  speed === 2 ? 'bg-cyan-500/25 text-cyan-300' : 'text-slate-400 hover:text-white'
                }`}
              >
                2×
              </button>
            </div>

            <div className="flex items-center gap-1.5 text-xs font-mono text-cyan-300 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
              <Clock className="h-3.5 w-3.5 text-cyan-400" />
              <span className="font-bold">{demoClock(time)} IST</span>
              <span className="text-slate-500 text-[10px]">({Math.floor(time)}s / {DEMO_DURATION}s)</span>
            </div>
          </div>
        </div>

        {/* Row 2: Judge Storyline Beat Shortcuts + Timeline */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/80 text-[11px]">
          {/* Act / Chapter Stepper */}
          <div className="flex items-center gap-1 text-xs">
            <button
              disabled={chapterIndex <= 0}
              onClick={() => jump(chapterIndex - 1)}
              className="p-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-30"
              title="Previous chapter"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <span className="text-slate-300 font-medium px-1">
              <span className="text-cyan-400 font-bold">Step {chapterIndex + 1}/10:</span> {state.chapter.name}
            </span>
            <button
              disabled={chapterIndex >= chapters.length - 1}
              onClick={() => jump(chapterIndex + 1)}
              className="p-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-30"
              title="Next chapter"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Quick Act Jumps (Judge favorite: see climax instantly) */}
          <div className="flex items-center gap-1">
            <span className="text-[10px] uppercase font-mono text-slate-500 mr-1 hidden md:inline">Jump to Beat:</span>
            {STORY_BEATS.map(beat => {
              const active = time >= beat.at && time < beat.at + 20
              return (
                <button
                  key={beat.label}
                  onClick={() => {
                    setTime(beat.at)
                    setPlaying(false)
                  }}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors border ${
                    active
                      ? 'bg-cyan-500/20 border-cyan-400 text-cyan-200 font-bold'
                      : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-600 hover:text-slate-200'
                  }`}
                >
                  <strong className="text-cyan-400">{beat.act}:</strong> {beat.label}
                </button>
              )
            })}
          </div>

          {/* Range Scrubber */}
          <div className="w-full pt-0.5">
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
              aria-label="Storyline timeline scrubber"
            />
          </div>
        </div>
      </div>

      {/* ── MAIN 2-COLUMN VIEWPORT: STORY ENGINE & EVIDENCE SYSTEM ──────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-2.5 flex-1 min-h-0">
        {/* LEFT COLUMN: LIVE TACTICAL FEED + 3-PILLAR MISSION BRIEFING (7 COLS) */}
        <div className="lg:col-span-7 flex flex-col gap-2.5 min-h-0">
          {/* Tactical Surveillance Monitor */}
          <div ref={sceneRef} className="relative rounded-xl overflow-hidden border border-slate-700/80 bg-black shadow-lg shadow-black/60 flex-shrink-0">
            <DemoScene time={time} scenario={caseId} className="max-h-[240px] xl:max-h-[280px] flex items-center justify-center bg-black" />

            {/* Tactical Monitor HUD Overlays */}
            <div className="absolute top-2 left-2 flex items-center gap-2 pointer-events-none">
              <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-black/85 border border-cyan-500/40 text-[10px] font-mono text-cyan-300 backdrop-blur-md">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
                EDGE SENSOR: {state.camera}
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-950/85 border border-slate-700 text-[10px] font-mono text-slate-300">
                FRAME RATE: 30 FPS
              </span>
            </div>

            <div className="absolute top-2 right-2 pointer-events-none">
              <span className={`px-2.5 py-0.5 rounded font-mono text-[10px] font-bold border backdrop-blur-md ${
                state.alert
                  ? 'bg-rose-500/30 border-rose-500 text-rose-300 animate-pulse'
                  : caseId === 'animal' && time >= 42
                  ? 'bg-emerald-500/30 border-emerald-500 text-emerald-300'
                  : state.outage
                  ? 'bg-amber-500/30 border-amber-500 text-amber-300'
                  : 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300'
              }`}>
                {state.alert ? '🔴 THREAT: CRITICAL' : caseId === 'animal' && time >= 42 ? '🟢 THREAT: EXCLUDED' : state.outage ? '🟡 SENSOR: OFFLINE' : '🔵 STATUS: ROUTINE'}
              </span>
            </div>
          </div>

          {/* 3-Pillar Storyline Briefing: Ground Reality ➔ AI Intel ➔ Tactical Action */}
          <div className="bg-[#0b1420] border border-cyan-500/25 rounded-xl p-3 flex flex-col justify-between gap-2.5 flex-1 min-h-0 shadow-sm">
            <div>
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 font-mono">
                    {state.chapter.module} · Step {chapterIndex + 1} of 10
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">|</span>
                  <span className="text-xs font-bold text-white">
                    {state.chapter.question}
                  </span>
                </div>
                <Link
                  to={state.chapter.route}
                  className="flex items-center gap-1 text-[11px] font-semibold text-cyan-300 hover:text-cyan-100 hover:underline"
                >
                  <span>Open {state.chapter.module} Portal</span>
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>

              {/* 3 Narrative Pillars */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-2">
                {/* Pillar 1: Ground Reality */}
                <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 flex flex-col justify-between">
                  <div>
                    <span className="text-[9px] font-mono font-bold uppercase text-slate-400 flex items-center gap-1">
                      <Target className="h-2.5 w-2.5 text-cyan-400" /> Ground Situation
                    </span>
                    <p className="text-[11px] text-slate-200 mt-1 leading-snug">
                      {caseId === 'animal' && time >= 42
                        ? 'Spotted deer herd crossing boundary near post 4. No human accompaniment.'
                        : caseId === 'health' && state.outage
                        ? 'Camera link severed due to perimeter fiber cut or weather distortion.'
                        : caseId === 'vehicle' && time >= 39
                        ? 'Suspect vehicle entered restricted patrol corridor at 14:32:39.'
                        : 'Routine activity detected within designated surveillance checkpoint.'}
                    </p>
                  </div>
                </div>

                {/* Pillar 2: PRAHAAR AI Decision */}
                <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 flex flex-col justify-between">
                  <div>
                    <span className="text-[9px] font-mono font-bold uppercase text-cyan-400 flex items-center gap-1">
                      <Zap className="h-2.5 w-2.5 text-cyan-400" /> AI Rule Engine
                    </span>
                    <p className="text-[11px] text-slate-200 mt-1 leading-snug">
                      {state.chapter.explanation}
                    </p>
                  </div>
                </div>

                {/* Pillar 3: Tactical Action */}
                <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 flex flex-col justify-between">
                  <div>
                    <span className="text-[9px] font-mono font-bold uppercase text-amber-400 flex items-center gap-1">
                      <ShieldAlert className="h-2.5 w-2.5 text-amber-400" /> Command Action
                    </span>
                    <p className="text-[11px] text-slate-200 mt-1 leading-snug">
                      {state.alert
                        ? 'Dispatch QRT via Route B. Freeze cryptographic audit packet.'
                        : caseId === 'animal' && time >= 42
                        ? 'False alarm suppressed. Post sentries remain on primary standby.'
                        : caseId === 'health' && state.outage
                        ? 'Failover to neighbor nodes (CAM-08). Maintenance ticket auto-filed.'
                        : 'Continue automated passive trajectory mapping.'}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* What to Watch Pill */}
            <div className="bg-cyan-950/30 border border-cyan-500/30 rounded-lg p-2 flex items-center gap-2 text-[11px]">
              <Eye className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
              <div className="min-w-0 flex-1">
                <strong className="text-cyan-300">Watch on screen: </strong>
                <span className="text-slate-300">{state.chapter.action}</span>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: RULE ENGINE VERDICT + AUDIT TRAIL + CHAIN OF CUSTODY (5 COLS) */}
        <div className="lg:col-span-5 flex flex-col gap-2.5 min-h-0">
          {/* Card 1: Live Decision Engine Verdict & Telemetry */}
          <div className="bg-[#0b1420] border border-slate-800 rounded-xl p-3 space-y-2 flex-shrink-0 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Activity className="h-3 w-3 text-cyan-400" />
                Live Rule Engine Verdict
              </span>
              <span className="text-[10px] font-mono text-cyan-300 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                Target: {selectedCase.subject}
              </span>
            </div>

            {/* Verdict Box */}
            <div
              className={`rounded-lg border p-2.5 flex items-start gap-2.5 transition-all ${
                state.alert
                  ? 'border-rose-500 bg-rose-500/15 text-rose-200 shadow-md shadow-rose-950/50'
                  : caseId === 'animal' && time >= 42
                  ? 'border-emerald-500/60 bg-emerald-500/15 text-emerald-200'
                  : state.outage
                  ? 'border-amber-500/60 bg-amber-500/15 text-amber-200'
                  : 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200'
              }`}
            >
              {state.alert ? (
                <ShieldAlert className="h-5 w-5 text-rose-400 shrink-0 mt-0.5 animate-bounce" />
              ) : caseId === 'animal' && time >= 42 ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
              ) : state.outage ? (
                <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="h-5 w-5 text-cyan-400 shrink-0 mt-0.5" />
              )}
              <div className="min-w-0 flex-1">
                <div className="text-xs font-black uppercase tracking-wide flex items-center justify-between">
                  <span>
                    {caseId === 'health'
                      ? state.outage
                        ? 'Camera Outage / Tamper-Safe Failover'
                        : 'Sensor Health Clear'
                      : caseId === 'animal' && time >= 42
                      ? 'Animal Excluded (False Alarm Filter)'
                      : state.alert
                      ? 'Restricted Zone Intrusion Alert'
                      : state.inside
                      ? 'Corridor Entered · Measuring Dwell'
                      : 'Passive Track / No Threat'}
                  </span>
                </div>
                <div className="text-[10px] text-slate-300 mt-0.5 leading-snug">
                  {caseId === 'animal'
                    ? 'Perimeter rule is restricted to people & vehicles. Animal observation logged without alerting command.'
                    : caseId === 'health'
                    ? state.outage
                      ? 'CAM-12 connection dropped. Frame frozen with tamper watermark to eliminate phantom tracks.'
                      : 'Camera resolution and network telemetry within nominal operational thresholds.'
                    : state.alert
                    ? 'Dwell time in restricted zone exceeded 3.0 seconds threshold. Incident INC-024 created with court hash.'
                    : state.inside
                    ? `Target inside restricted zone: ${(time - 39).toFixed(1)}s elapsed (3.0s threshold)`
                    : 'Target moving in unmonitored road buffer. Zero false positive.'}
                </div>
              </div>
            </div>

            {/* Target Telemetry Bar */}
            <div className="grid grid-cols-3 gap-1 text-center pt-1 border-t border-slate-800/80">
              <div className="bg-slate-900/90 p-1.5 rounded border border-slate-800">
                <div className="text-[9px] text-slate-400 uppercase font-mono">ANPR / OCR</div>
                <div className="text-xs font-mono font-black text-white truncate">
                  {caseId === 'vehicle' ? (time >= 8 ? DEMO_PLATE : 'Reading...') : caseId === 'health' ? (state.outage ? 'FAILOVER' : 'HEALTHY') : caseId.toUpperCase()}
                </div>
              </div>
              <div className="bg-slate-900/90 p-1.5 rounded border border-slate-800">
                <div className="text-[9px] text-slate-400 uppercase font-mono">Sensor Node</div>
                <div className="text-xs font-mono font-bold text-cyan-300 truncate">
                  {state.camera}
                </div>
              </div>
              <div className="bg-slate-900/90 p-1.5 rounded border border-slate-800">
                <div className="text-[9px] text-slate-400 uppercase font-mono">Sightings</div>
                <div className="text-xs font-mono font-bold text-emerald-400 truncate">
                  {state.sightings.length} / 3 Nodes
                </div>
              </div>
            </div>

            {/* Multi-Camera Cross-Handoff Node Stepper */}
            <div className="flex items-center justify-between gap-1 text-[10px] font-mono bg-slate-950 p-1.5 rounded-lg border border-slate-800">
              <span className="text-[9px] text-slate-500 uppercase">Trajectory:</span>
              {['CAM-07', 'CAM-08', 'CAM-12'].map((cam, idx) => {
                const reached = state.sightings.some(s => s.camera === cam)
                return (
                  <div key={cam} className="flex items-center gap-1">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        reached ? 'bg-cyan-400 shadow-sm shadow-cyan-400' : 'bg-slate-700'
                      }`}
                    />
                    <span className={reached ? 'text-cyan-200 font-bold' : 'text-slate-500'}>
                      {cam}
                    </span>
                    {idx < 2 && <span className="text-slate-600">→</span>}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Card 2: Live Chronological Mission Audit Log & Chain of Custody */}
          <div className="bg-[#0b1420] border border-slate-800 rounded-xl p-3 flex flex-col flex-1 min-h-0 shadow-sm">
            <div className="flex items-center justify-between mb-1.5 flex-shrink-0">
              <div className="flex items-center gap-1.5">
                <Layers className="h-3 w-3 text-cyan-400" />
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-300 font-bold">
                  Mission Audit Trail ({state.events.length} Events Logged)
                </span>
              </div>
              <button
                onClick={exportRecord}
                className="flex items-center gap-1 text-[10px] font-mono font-bold text-cyan-300 hover:text-cyan-100 bg-cyan-950/60 border border-cyan-500/30 px-2 py-0.5 rounded transition-colors"
                title="Download Court-Admissible JSON Record"
              >
                <Download className="h-2.5 w-2.5" />
                <span>Export Forensic JSON</span>
              </button>
            </div>

            {/* Cryptographic Ledger Proof Banner */}
            <div className="bg-slate-950 p-1.5 rounded border border-slate-800/80 mb-2 flex items-center justify-between text-[10px] font-mono flex-shrink-0">
              <span className="text-slate-400">PRAMAAN Ledger:</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                {evidenceDigest}
              </span>
            </div>

            {/* Audit log scroll container: clean independent scroll */}
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 max-h-[160px] xl:max-h-[220px]">
              {state.events.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-28 text-center text-slate-500 text-xs">
                  <Play className="h-5 w-5 stroke-1 text-slate-600 mb-1" />
                  <span>Click <strong>Play Storyline</strong> above to watch real-time detections and rules trigger.</span>
                </div>
              ) : (
                [...state.events].reverse().map(event => (
                  <div
                    key={`${event.at}-${event.camera}`}
                    className={`border-l-2 pl-2 py-1 text-xs rounded-r transition-all ${
                      event.kind === 'alert'
                        ? 'border-rose-400 bg-rose-500/10'
                        : event.kind === 'health'
                        ? 'border-amber-400 bg-amber-500/10'
                        : 'border-cyan-500/70 bg-cyan-500/5'
                    }`}
                  >
                    <div className="flex items-center justify-between font-mono text-[9px]">
                      <span className="text-cyan-300 font-bold">{demoClock(event.at)} IST</span>
                      <span className="text-slate-400 bg-slate-950 px-1 py-0.2 rounded border border-slate-800">{event.camera}</span>
                    </div>
                    <div className="font-bold text-slate-200 text-[10px] mt-0.5">
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
