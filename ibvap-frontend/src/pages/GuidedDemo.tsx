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
  Sparkles,
  Navigation,
  Compass,
  Database,
  Cpu,
  Flame,
  Check,
  ScanLine
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

// 5 Key Story Beats for instant jump
const STORY_BEATS: { label: string; at: number; act: string; tip: string }[] = [
  { label: 'Checkpoint ANPR', at: 8, act: 'Act 1', tip: 'Camera 07 reads demo plate' },
  { label: 'Cross-Cam Handoff', at: 28, act: 'Act 2', tip: 'Target appears on Camera 08' },
  { label: 'Perimeter Breach (Alert)', at: 42, act: 'Act 3', tip: '3-second dwell threshold exceeded' },
  { label: 'Sensor Outage Failover', at: 62, act: 'Act 4', tip: 'CAM-12 recovers, offline queue synced' },
  { label: 'Court Evidence Signed', at: 113, act: 'Act 5', tip: 'PRAMAAN SHA-256 block locked' },
]

// All 10 core capabilities of PRAHAAR for judge evaluation
const CAPABILITIES = [
  { id: 'fence', name: 'PARAKH', label: 'Virtual Fence & Dwell', icon: ShieldAlert, color: 'text-rose-400', route: '/virtual-fence', desc: 'Custom polygon tripwire + dwell time rules prevent phantom alerts.' },
  { id: 'anpr', name: 'C7 ANPR', label: 'License Plate OCR', icon: Car, color: 'text-cyan-400', route: '/anpr', desc: 'Sub-second optical plate recognition with candidate matching.' },
  { id: 'animal', name: 'SAKSHAM', label: 'Human / Animal AI', icon: ShieldCheck, color: 'text-emerald-400', route: '/field', desc: 'Class-aware spatial rules eliminate 94% false alarms from wildlife.' },
  { id: 'field', name: 'SAKSHAM', label: 'Offline Edge Mesh', icon: Database, color: 'text-amber-400', route: '/field', desc: 'Store-and-forward buffers observations during satellite/fiber drops.' },
  { id: 'route', name: 'MARGDARSHAN', label: 'Tactical Route Intel', icon: Navigation, color: 'text-blue-400', route: '/route-analysis', desc: 'Calculates safest intercept route avoiding camera blind spots.' },
  { id: 'incident', name: 'SUTRA', label: 'Incident Correlation', icon: Layers, color: 'text-purple-400', route: '/incident-intel', desc: 'Correlates disjoint sensor events into a single actionable dossier.' },
  { id: 'evidence', name: 'PRAMAAN', label: 'Evidence Ledger', icon: FileCheck, color: 'text-indigo-400', route: '/evidence', desc: 'Immutable SHA-256 cryptographic chain of custody for court.' },
  { id: 'health', name: 'Sensor Health', label: 'Optical Quality & Outage', icon: Activity, color: 'text-amber-400', route: '/health', desc: 'Flags optical blur and freezes stale frames to stop false positives.' },
  { id: 'radar', name: 'C5 Detection', label: 'Edge YOLOv8 Engine', icon: Cpu, color: 'text-cyan-300', route: '/detections', desc: 'High-throughput 30 FPS multi-class neural inference at edge.' },
  { id: 'gis', name: 'Digital Twin', label: 'GIS Geospatial Map', icon: Compass, color: 'text-emerald-300', route: '/gis', desc: 'Live operational map with camera field-of-view cones.' },
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
  // Default speed set to 2x so judges don't have to wait!
  const [speed, setSpeed] = useState<number>(2)
  const [activeTab, setActiveTab] = useState<'story' | 'capabilities' | 'routes'>('story')
  const [quickTourActive, setQuickTourActive] = useState(false)

  const state = scenarioAt(time, caseId)
  const chapterIndex = chapters.findIndex(c => c.id === state.chapter.id)

  useEffect(() => {
    setTime(requested?.at ?? 0)
    setPlaying(false)
  }, [requested])

  // Playback timer with support for 1x, 2x, 4x turbo speeds
  useEffect(() => {
    if (!playing || time >= DEMO_DURATION) {
      if (quickTourActive && time >= DEMO_DURATION) setQuickTourActive(false)
      return
    }
    const interval = Math.max(25, Math.round(100 / speed))
    const timer = window.setTimeout(() => {
      setTime(t => Math.min(DEMO_DURATION, Math.round((t + 0.1 * (speed >= 4 ? 2 : 1)) * 10) / 10))
    }, interval)
    return () => window.clearTimeout(timer)
  }, [playing, time, speed, quickTourActive])

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
    setQuickTourActive(false)
  }

  // 30-Second Rapid Judge Tour Mode
  function startQuickTour() {
    setQuickTourActive(true)
    setSpeed(4) // Turbo speed for 30s tour
    setTime(0)
    setPlaying(true)
  }

  // Cryptographic evidence digest simulation
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
    <div className="flex flex-col flex-1 p-2 md:p-3 gap-2 bg-[#050b12] text-slate-100 min-h-0 font-sans">
      {/* ── TOP MISSION CONTROL HEADER & PITCH HIGHLIGHTS ──────────────────── */}
      <div className="bg-[#0b1420] border border-cyan-500/25 rounded-xl px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 shadow-md shadow-black/40 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/30 to-blue-600/30 text-cyan-300 border border-cyan-400/40">
            <Radio className="h-3.5 w-3.5 animate-pulse text-cyan-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs md:text-sm font-black tracking-wider text-white uppercase flex items-center gap-1.5">
                प्रहार · Interactive Demo
                <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-cyan-400/15 text-cyan-300 border border-cyan-400/30">
                  ALL 10 MODULES
                </span>
              </span>
            </div>
            <p className="text-[10px] text-slate-400 hidden sm:block">
              Rapid Pitch Sandbox · Edge AI ➔ Spatial Rule Engine ➔ Offline SAKSHAM Mesh ➔ PRAMAAN Ledger
            </p>
          </div>
        </div>

        {/* 4 Winning Differentiator Badges */}
        <div className="flex flex-wrap items-center gap-1 text-[10px] font-mono">
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

      {/* ── UNIFIED TOOLBAR: SCENARIOS + RAPID PLAYBACK CONTROLS (FAST PACED) ─ */}
      <div className="bg-[#09111c] border border-slate-800 rounded-xl p-2.5 flex flex-col gap-2 shadow-sm flex-shrink-0">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {/* Scenario Tabs */}
          <div className="flex flex-wrap items-center gap-1 bg-[#060c14] p-1 rounded-lg border border-slate-800" role="tablist">
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
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs transition-all ${
                    active
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/60 font-medium'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{meta.title.split('(')[0].replace('& Plate Trail', '').trim()}</span>
                </button>
              )
            })}
          </div>

          {/* Rapid Playback Controls with 1x, 2x, 4x Turbo & 30s Judge Quick Pitch */}
          <div className="flex items-center gap-1.5">
            {/* 30-Sec Quick Pitch Button */}
            <button
              onClick={startQuickTour}
              className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-black transition-all border ${
                quickTourActive
                  ? 'bg-amber-400 text-slate-950 border-amber-300 animate-pulse'
                  : 'bg-amber-500/15 border-amber-500/40 text-amber-300 hover:bg-amber-500/25'
              }`}
              title="Fast 30-second automated walkthrough of all key moments"
            >
              <Flame className="h-3.5 w-3.5 text-amber-400 fill-current" />
              <span>⚡ 30s Judge Tour</span>
            </button>

            {/* Play/Pause */}
            <button
              onClick={() => {
                if (time >= DEMO_DURATION) setTime(0)
                setPlaying(p => !p || time >= DEMO_DURATION)
              }}
              className="flex items-center gap-1.5 rounded-lg bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-black px-3.5 py-1 text-xs transition-all shadow-sm"
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
                setQuickTourActive(false)
              }}
              title="Reset Timeline"
              className="p-1 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-300"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>

            {/* Speed Selector: 1x, 2x (default), 4x (Turbo) */}
            <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5 text-xs font-mono font-bold">
              <button
                onClick={() => setSpeed(1)}
                className={`px-1.5 py-0.5 rounded text-[10px] ${
                  speed === 1 ? 'bg-cyan-500/30 text-cyan-300' : 'text-slate-400 hover:text-white'
                }`}
              >
                1×
              </button>
              <button
                onClick={() => setSpeed(2)}
                className={`px-1.5 py-0.5 rounded text-[10px] ${
                  speed === 2 ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-white'
                }`}
              >
                2× Fast
              </button>
              <button
                onClick={() => setSpeed(4)}
                className={`px-1.5 py-0.5 rounded text-[10px] ${
                  speed === 4 ? 'bg-amber-400 text-slate-950' : 'text-slate-400 hover:text-white'
                }`}
                title="Turbo 4x speed"
              >
                4× Turbo
              </button>
            </div>

            <div className="flex items-center gap-1.5 text-xs font-mono text-cyan-300 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
              <Clock className="h-3 w-3 text-cyan-400" />
              <span>{demoClock(time)} IST</span>
              <span className="text-slate-500 text-[10px]">({Math.floor(time)}s)</span>
            </div>
          </div>
        </div>

        {/* Row 2: 5 Key Acts (Instant Climax Jumpers) & Scrubber */}
        <div className="flex flex-wrap items-center justify-between gap-1.5 pt-1 border-t border-slate-800/80 text-[11px]">
          <div className="flex items-center gap-1">
            <span className="text-[10px] uppercase font-mono text-slate-500 mr-1 hidden md:inline">Instant Climax:</span>
            {STORY_BEATS.map(beat => {
              const active = time >= beat.at && time < beat.at + 18
              return (
                <button
                  key={beat.label}
                  onClick={() => {
                    setTime(beat.at)
                    setPlaying(false)
                    setQuickTourActive(false)
                  }}
                  title={beat.tip}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors border ${
                    active
                      ? 'bg-cyan-500/25 border-cyan-400 text-cyan-200 font-bold'
                      : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-600 hover:text-slate-200'
                  }`}
                >
                  <strong className="text-cyan-400">{beat.act}:</strong> {beat.label}
                </button>
              )
            })}
          </div>

          <div className="flex items-center gap-1 text-xs">
            <button
              disabled={chapterIndex <= 0}
              onClick={() => jump(chapterIndex - 1)}
              className="p-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-30"
              title="Previous step"
            >
              <ChevronLeft className="h-3 w-3" />
            </button>
            <span className="text-slate-300 font-medium px-1">
              <span className="text-cyan-400 font-bold">Step {chapterIndex + 1}/10:</span> {state.chapter.name}
            </span>
            <button
              disabled={chapterIndex >= chapters.length - 1}
              onClick={() => jump(chapterIndex + 1)}
              className="p-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-30"
              title="Next step"
            >
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>

          {/* Timeline Slider */}
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
                setQuickTourActive(false)
              }}
              className="w-full accent-cyan-400 h-1.5 bg-slate-800 rounded cursor-pointer"
              aria-label="Storyline timeline scrubber"
            />
          </div>
        </div>
      </div>

      {/* ── MAIN 2-COLUMN VIEWPORT (ZERO DOUBLE SCROLL, CRISP SINGLE SCREEN) ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-2 flex-1 min-h-0">
        {/* LEFT COLUMN: LIVE TACTICAL MONITOR + MULTI-FEATURE VIEW (7 COLS) */}
        <div className="lg:col-span-7 flex flex-col gap-2 min-h-0">
          {/* Tactical Monitor */}
          <div ref={sceneRef} className="relative rounded-xl overflow-hidden border border-slate-700/80 bg-black shadow-md flex-shrink-0">
            <DemoScene time={time} scenario={caseId} className="max-h-[225px] xl:max-h-[260px] flex items-center justify-center bg-black" />

            {/* Tactical Monitor Overlays */}
            <div className="absolute top-2 left-2 flex items-center gap-1.5 pointer-events-none">
              <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-black/85 border border-cyan-500/40 text-[10px] font-mono text-cyan-300 backdrop-blur-md">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
                SENSOR: {state.camera}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-slate-950/85 border border-slate-800 text-[10px] font-mono text-slate-300">
                EDGE INFERENCE: 28ms
              </span>
            </div>

            <div className="absolute top-2 right-2 pointer-events-none">
              <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border backdrop-blur-md ${
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

          {/* Interactive Feature Panel Switcher Tabs */}
          <div className="bg-[#0b1420] border border-cyan-500/25 rounded-xl p-2.5 flex flex-col justify-between gap-2 flex-1 min-h-0 shadow-sm">
            {/* View Sub-tabs: Story Briefing | 10 Capabilities Matrix | Route Intercept */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
              <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800">
                <button
                  onClick={() => setActiveTab('story')}
                  className={`px-2.5 py-0.5 rounded text-xs font-bold transition-all ${
                    activeTab === 'story' ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Mission Briefing
                </button>
                <button
                  onClick={() => setActiveTab('capabilities')}
                  className={`px-2.5 py-0.5 rounded text-xs font-bold transition-all flex items-center gap-1 ${
                    activeTab === 'capabilities' ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Sparkles className="h-3 w-3" />
                  <span>10-in-1 Capabilities</span>
                </button>
                <button
                  onClick={() => setActiveTab('routes')}
                  className={`px-2.5 py-0.5 rounded text-xs font-bold transition-all flex items-center gap-1 ${
                    activeTab === 'routes' ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Navigation className="h-3 w-3" />
                  <span>Tactical Route</span>
                </button>
              </div>

              <Link
                to={state.chapter.route}
                className="flex items-center gap-1 text-[11px] font-semibold text-cyan-300 hover:text-cyan-100 hover:underline"
              >
                <span>Live {state.chapter.module}</span>
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>

            {/* TAB 1: STORY BRIEFING (3 PILLARS) */}
            {activeTab === 'story' && (
              <div className="space-y-2">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-2">
                    <span className="text-[9px] font-mono font-bold uppercase text-slate-400 flex items-center gap-1">
                      <Target className="h-2.5 w-2.5 text-cyan-400" /> Ground Situation
                    </span>
                    <p className="text-[11px] text-slate-200 mt-1 leading-snug">
                      {caseId === 'animal' && time >= 42
                        ? 'Spotted deer crossing near boundary post 4. No human presence.'
                        : caseId === 'health' && state.outage
                        ? 'Optical signal lost at CAM-12. Zero-trust lock engaged.'
                        : caseId === 'vehicle' && time >= 39
                        ? 'Suspect vehicle entered restricted patrol corridor at 14:32:39.'
                        : 'Routine activity detected within designated surveillance checkpoint.'}
                    </p>
                  </div>

                  <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-2">
                    <span className="text-[9px] font-mono font-bold uppercase text-cyan-400 flex items-center gap-1">
                      <Zap className="h-2.5 w-2.5 text-cyan-400" /> PRAHAAR Engine Logic
                    </span>
                    <p className="text-[11px] text-slate-200 mt-1 leading-snug">
                      {state.chapter.explanation}
                    </p>
                  </div>

                  <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-2">
                    <span className="text-[9px] font-mono font-bold uppercase text-amber-400 flex items-center gap-1">
                      <ShieldAlert className="h-2.5 w-2.5 text-amber-400" /> Military Action
                    </span>
                    <p className="text-[11px] text-slate-200 mt-1 leading-snug">
                      {state.alert
                        ? 'Dispatch QRT via Route B. Freeze forensic audit packet.'
                        : caseId === 'animal' && time >= 42
                        ? 'False alarm suppressed. Sentries stay on primary duty.'
                        : caseId === 'health' && state.outage
                        ? 'Failover to neighbor node CAM-08. Work ticket filed.'
                        : 'Continuous passive trajectory mapping active.'}
                    </p>
                  </div>
                </div>

                <div className="bg-cyan-950/30 border border-cyan-500/30 rounded-lg p-1.5 flex items-center gap-2 text-[11px]">
                  <Eye className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <strong className="text-cyan-300">Watch on screen: </strong>
                    <span className="text-slate-300">{state.chapter.action}</span>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: 10-IN-1 CAPABILITIES MATRIX */}
            {activeTab === 'capabilities' && (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-1.5 overflow-y-auto max-h-[140px] pr-1">
                {CAPABILITIES.map(cap => {
                  const Icon = cap.icon
                  return (
                    <Link
                      key={cap.id}
                      to={cap.route}
                      className="bg-slate-950 border border-slate-800 hover:border-cyan-500/50 p-1.5 rounded-lg flex flex-col justify-between transition-colors group"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <Icon className={`h-3.5 w-3.5 ${cap.color}`} />
                          <span className="text-[9px] font-mono text-cyan-400 opacity-0 group-hover:opacity-100">Open ↗</span>
                        </div>
                        <div className="text-[10px] font-bold text-white mt-1 leading-tight">{cap.name}</div>
                        <div className="text-[9px] text-slate-400 leading-tight">{cap.label}</div>
                      </div>
                    </Link>
                  )
                })}
              </div>
            )}

            {/* TAB 3: TACTICAL ROUTE ANALYSIS (MARGDARSHAN) */}
            {activeTab === 'routes' && (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-950 p-2 rounded-lg border border-rose-500/30">
                  <div className="flex items-center justify-between font-mono font-bold text-rose-400 text-[10px]">
                    <span>ROUTE A (DIRECT)</span>
                    <span>RISK: HIGH ⚠️</span>
                  </div>
                  <div className="text-[11px] text-slate-200 mt-1">1.8 km · 4 mins travel time</div>
                  <div className="text-[10px] text-rose-300 mt-1 leading-tight">
                    Crosses CAM-12 outage blind zone. QRT might lose target visual contact.
                  </div>
                </div>

                <div className="bg-slate-950 p-2 rounded-lg border border-emerald-500/40">
                  <div className="flex items-center justify-between font-mono font-bold text-emerald-400 text-[10px]">
                    <span>ROUTE B (RECOMMENDED)</span>
                    <span>92% INTERCEPT PROBABILITY ✅</span>
                  </div>
                  <div className="text-[11px] text-slate-200 mt-1">2.4 km · 5 mins travel time</div>
                  <div className="text-[10px] text-emerald-300 mt-1 leading-tight">
                    Circumvents unmonitored road buffer. Intercept angle ensures zero blind spot.
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: DECISION VERDICT + AUDIT TRAIL + CHAIN OF CUSTODY (5 COLS) */}
        <div className="lg:col-span-5 flex flex-col gap-2 min-h-0">
          {/* Card 1: Live Decision Engine Verdict & Telemetry */}
          <div className="bg-[#0b1420] border border-slate-800 rounded-xl p-2.5 space-y-2 flex-shrink-0 shadow-sm">
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
              className={`rounded-lg border p-2 flex items-start gap-2 transition-all ${
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
                <ShieldAlert className="h-4 w-4 text-rose-400 shrink-0 mt-0.5 animate-bounce" />
              ) : caseId === 'animal' && time >= 42 ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : state.outage ? (
                <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
              )}
              <div className="min-w-0 flex-1">
                <div className="text-xs font-black uppercase tracking-wide">
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
              <div className="bg-slate-900/90 p-1 rounded border border-slate-800">
                <div className="text-[8px] text-slate-400 uppercase font-mono">ANPR / OCR</div>
                <div className="text-xs font-mono font-black text-white truncate">
                  {caseId === 'vehicle' ? (time >= 8 ? DEMO_PLATE : 'Reading...') : caseId === 'health' ? (state.outage ? 'FAILOVER' : 'HEALTHY') : caseId.toUpperCase()}
                </div>
              </div>
              <div className="bg-slate-900/90 p-1 rounded border border-slate-800">
                <div className="text-[8px] text-slate-400 uppercase font-mono">Active Sensor</div>
                <div className="text-xs font-mono font-bold text-cyan-300 truncate">
                  {state.camera}
                </div>
              </div>
              <div className="bg-slate-900/90 p-1 rounded border border-slate-800">
                <div className="text-[8px] text-slate-400 uppercase font-mono">Sightings</div>
                <div className="text-xs font-mono font-bold text-emerald-400 truncate">
                  {state.sightings.length} / 3 Nodes
                </div>
              </div>
            </div>

            {/* Multi-Camera Trajectory Handoff Stepper */}
            <div className="flex items-center justify-between gap-1 text-[10px] font-mono bg-slate-950 p-1 rounded border border-slate-800">
              <span className="text-[8px] text-slate-500 uppercase">Handoff:</span>
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

          {/* Card 2: Chronological Mission Audit Log & PRAMAAN Chain of Custody */}
          <div className="bg-[#0b1420] border border-slate-800 rounded-xl p-2.5 flex flex-col flex-1 min-h-0 shadow-sm">
            <div className="flex items-center justify-between mb-1.5 flex-shrink-0">
              <div className="flex items-center gap-1.5">
                <Layers className="h-3 w-3 text-cyan-400" />
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-300 font-bold">
                  Audit Log ({state.events.length} Events)
                </span>
              </div>
              <button
                onClick={exportRecord}
                className="flex items-center gap-1 text-[10px] font-mono font-bold text-cyan-300 hover:text-cyan-100 bg-cyan-950/60 border border-cyan-500/30 px-2 py-0.5 rounded transition-colors"
                title="Download Court-Admissible JSON Record"
              >
                <Download className="h-2.5 w-2.5" />
                <span>Forensic JSON</span>
              </button>
            </div>

            {/* Cryptographic Ledger Proof Banner */}
            <div className="bg-slate-950 p-1.5 rounded border border-slate-800/80 mb-1.5 flex items-center justify-between text-[10px] font-mono flex-shrink-0">
              <span className="text-slate-400">PRAMAAN Hash:</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1 truncate max-w-[210px]">
                <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
                {evidenceDigest}
              </span>
            </div>

            {/* Audit log scroll container */}
            <div className="flex-1 overflow-y-auto space-y-1 pr-1 max-h-[160px] xl:max-h-[200px]">
              {state.events.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-24 text-center text-slate-500 text-xs">
                  <Play className="h-5 w-5 stroke-1 text-slate-600 mb-1" />
                  <span>Click <strong>Play</strong> or <strong>⚡ 30s Judge Tour</strong> to watch events.</span>
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
