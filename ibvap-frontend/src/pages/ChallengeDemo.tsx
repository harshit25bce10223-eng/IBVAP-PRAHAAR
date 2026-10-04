import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import {
  Play,
  Pause,
  RotateCcw,
  Shield,
  CloudFog,
  WifiOff,
  VideoOff,
  ChevronRight,
  Download,
  Maximize2,
  Minimize2,
  Check,
  AlertTriangle,
  ArrowRight,
  Fingerprint,
  X,
  Eye,
  Layers,
  Navigation,
  ListChecks,
  Crosshair,
} from 'lucide-react'
import { ChallengeScene, type SceneLayers } from '@/components/demo/ChallengeScene'
import {
  CHALLENGE_DURATION,
  missionActs,
  challengeAt,
  emptyFaults,
  featureCatalog,
  missions,
  sha256,
  type FaultId,
  type Faults,
  type FaultStarts,
  type MissionId,
} from '@/components/demo/challengeEngine'
import './guidedDemo.css'

type AuditAction = { at: number; action: string; detail: string }
type EvidenceSeal = { payload: string; digest: string }
const initialLayers: SceneLayers = {
  zones: true,
  tracks: true,
  routes: false,
  heatmap: false,
  enhanced: true,
}
const faultButtons = [
  { id: 'fog' as const, label: 'Dense fog', icon: CloudFog },
  { id: 'camera' as const, label: 'Kill CAM3', icon: VideoOff },
  { id: 'network' as const, label: 'Cut uplink', icon: WifiOff },
]
const chapterTimes: Record<string, number> = {
  detection: 0,
  anpr: 20,
  tracking: 28,
  fence: 45,
  health: 65,
  gis: 90,
  incident: 55,
  field: 74,
  route: 100,
  evidence: 125,
}

export function ChallengeDemo() {
  const [params, setParams] = useSearchParams()
  const location = useLocation()
  const fallback: MissionId = location.pathname.includes('health')
    ? 'health'
    : location.pathname === '/field'
      ? 'animal'
      : location.pathname === '/virtual-fence' || location.pathname.startsWith('/track/')
        ? 'person'
        : location.pathname.includes('anpr') || location.pathname.startsWith('/vehicle/')
          ? 'vehicle'
          : 'compound'
  const mission = missions.find(m => m.id === params.get('case'))?.id ?? fallback
  const start = chapterTimes[params.get('chapter') ?? ''] ?? 0
  return (
    <ChallengeRun
      key={`${mission}-${start}`}
      mission={mission}
      start={start}
      onMissionSelect={id => setParams({ case: id }, { replace: true })}
    />
  )
}

function ChallengeRun({
  mission,
  start,
  onMissionSelect,
}: {
  mission: MissionId
  start: number
  onMissionSelect: (id: MissionId) => void
}) {
  const meta = missions.find(m => m.id === mission)!
  const steps = useMemo(() => missionActs(mission), [mission])
  const [time, setTime] = useState(start)
  const [wantsToPlay, setPlaying] = useState(false)
  const playing = wantsToPlay && time < CHALLENGE_DURATION
  const [speed, setSpeed] = useState(1)
  const [faults, setFaults] = useState<Faults>(emptyFaults)
  const [faultStarts, setFaultStarts] = useState<FaultStarts>({})
  const [layers, setLayers] = useState(initialLayers)
  const [selected, setSelected] = useState(mission === 'health' ? 'CAM3' : 'Person P-01')
  const [tab, setTab] = useState<'story' | 'features' | 'routes' | 'evidence'>('story')
  const [focus, setFocus] = useState(false)
  const [audit, setAudit] = useState<AuditAction[]>([])
  const [seal, setSeal] = useState<EvidenceSeal | null>(null)
  const [changed, setChanged] = useState(false)
  const [verification, setVerification] = useState<
    'none' | 'working' | 'match' | 'mismatch' | 'error'
  >('none')
  const [message, setMessage] = useState('')
  const [toasts, setToasts] = useState<{ id: number; text: string; kind: string }[]>([])
  const toastIdRef = useRef(0)
  const prevEventLen = useRef(0)
  const cryptoGeneration = useRef(0)
  const state = useMemo(
    () => challengeAt(time, mission, faults, faultStarts),
    [time, mission, faults, faultStarts]
  )
  const actions = audit.filter(a => a.at <= time)
  const decision = [...actions]
    .reverse()
    .find(a => a.action === 'ACKNOWLEDGED' || a.action === 'REJECTED')
  const activeFeatures = featureCatalog.filter(
    f =>
      time >= f.stage &&
      !(
        state.healthOnly &&
        ['detection', 'tracking', 'anpr', 'fence', 'risk', 'animal', 'correlation'].includes(f.id)
      ) &&
      !(f.id === 'anpr' && !state.vehicle) &&
      !(f.id === 'animal' && !state.wildlife)
  )

  function clearRun() {
    setPlaying(false)
    setFaults({ ...emptyFaults })
    setFaultStarts({})
    setLayers({ ...initialLayers })
    setAudit([])
    setSeal(null)
    setChanged(false)
    setVerification('none')
    setMessage('')
    cryptoGeneration.current++
  }
  useEffect(() => {
    if (!playing) return
    let previous = performance.now()
    const timer = window.setInterval(() => {
      const now = performance.now()
      const delta = ((now - previous) / 1000) * speed
      previous = now
      setTime(t => Math.min(CHALLENGE_DURATION, t + delta))
    }, 100)
    return () => window.clearInterval(timer)
  }, [playing, speed])
  useEffect(() => {
    if (!focus) return
    const close = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setFocus(false)
    }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [focus])

  function log(action: string, detail: string) {
    setAudit(list => [...list, { at: Number(time.toFixed(1)), action, detail }])
  }
  function inject(id: FaultId) {
    const enabled = !faults[id]
    setFaults(f => ({ ...f, [id]: enabled }))
    setFaultStarts(starts => ({
      ...starts,
      ...(enabled ? { [id]: time } : {}),
      ...(id === 'network'
        ? { networkResume: enabled ? undefined : time }
        : id === 'camera'
          ? { cameraResume: enabled ? undefined : time }
          : {}),
    }))
    log(enabled ? 'FAULT_INJECTED' : 'FAULT_RELEASED', id)
  }
  function seek(at: number) {
    if (at < time) {
      setSeal(null)
      setChanged(false)
      setVerification('none')
      cryptoGeneration.current++
      setFaults({ ...emptyFaults })
      setFaultStarts({})
    }
    setPlaying(false)
    setTime(at)
    setAudit(list => list.filter(a => a.at <= at))
    setMessage('')
  }
  function selectMission(id: MissionId) {
    onMissionSelect(id)
    setSelected(id === 'health' ? 'CAM3' : 'Person P-01')
  }
  // ── Toast notifications for new events ─────────────────────────────────
  useEffect(() => {
    const curr = state.events.length
    if (curr > prevEventLen.current) {
      const fresh = state.events.slice(prevEventLen.current)
      prevEventLen.current = curr
      fresh.slice(-2).forEach(e => {
        const id = ++toastIdRef.current
        setToasts(t => [...t.slice(-3), { id, text: e.title, kind: e.kind }])
        window.setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4500)
      })
    }
  }, [state.events])

  // ── Derived threat level ─────────────────────────────────────────────────
  const threatLevel =
    state.risk >= 70 ? 'CRITICAL' :
    state.risk >= 45 ? 'ELEVATED' :
    state.risk >= 20 ? 'WATCHFUL' : 'SECURE'
  const threatColor =
    state.risk >= 70 ? '#fb7185' :
    state.risk >= 45 ? '#fbbf24' :
    state.risk >= 20 ? '#60a5fa' : '#34d399'
  const threatBg =
    state.risk >= 70 ? '#1e0610' :
    state.risk >= 45 ? '#1c1204' :
    state.risk >= 20 ? '#060e20' : '#061410'

  // ── AI module live confidence (scripted) ─────────────────────────────────
  const aiModules = [
    { name: 'YOLOv8', pct: Math.min(99, 91 + Math.round(Math.sin(time * 0.3) * 3)), ok: true },
    { name: 'ANPR-OCR', pct: state.vehicle ? Math.min(99, 88 + Math.round(Math.cos(time * 0.4) * 4)) : 0, ok: !!state.vehicle },
    { name: 'Re-ID', pct: Math.min(99, 84 + Math.round(Math.sin(time * 0.2) * 5)), ok: !state.healthOnly },
    { name: 'PARAKH', pct: state.intrusion ? 100 : Math.min(99, 76 + Math.round(time * 0.2)), ok: true },
    { name: 'SAKSHAM', pct: state.networkOffline ? 100 : 97, ok: true },
  ]

  function judgeTour() {
    setTime(0)
    clearRun()
    setSpeed(5)
    setPlaying(true)
    setTab('story')
  }
  function decide(action: 'ACKNOWLEDGED' | 'REJECTED') {
    log(
      action,
      action === 'ACKNOWLEDGED'
        ? 'Officer acknowledges the demo alert; no real dispatch.'
        : 'Officer rejects the demo alert and retains observations for review.'
    )
    setMessage(
      action === 'ACKNOWLEDGED'
        ? 'Demo alert acknowledged. Response remains an officer decision.'
        : 'Demo alert rejected. Observations and officer feedback retained.'
    )
  }
  const currentPayload = JSON.stringify(
    {
      simulation: true,
      scenario: mission,
      captureSeconds: Number(time.toFixed(1)),
      environment: { night: time >= 12, fog: state.fog },
      coverage: { camera3Offline: state.cameraOffline, uplinkOffline: state.networkOffline },
      rule: {
        thresholdSeconds: 3,
        dwell: state.dwell,
        personAlert: state.intrusion,
        animalExcluded: state.animalExcluded,
      },
      risk: { score: state.risk, factors: state.factors, confidence: state.confidence },
      offline: { captured: state.captured, queued: state.queued, synced: state.synced },
      events: state.events,
      officerActions: actions,
    },
    null,
    2
  )
  const verificationPayload = seal
    ? changed
      ? seal.payload.replace('"simulation": true', '"simulation": false')
      : seal.payload
    : ''
  async function sealEvidence() {
    const generation = ++cryptoGeneration.current
    setVerification('working')
    setMessage('')
    const payload = currentPayload
    try {
      const digest = await sha256(payload)
      if (generation !== cryptoGeneration.current) return
      setSeal({ payload, digest })
      setChanged(false)
      setVerification('match')
      log('EVIDENCE_SEALED', 'SHA-256 computed locally for a frozen demo snapshot.')
    } catch {
      if (generation === cryptoGeneration.current) {
        setVerification('error')
        setMessage('SHA-256 is unavailable in this browser context. Use localhost or HTTPS.')
      }
    }
  }
  async function verifyEvidence(tampered: boolean) {
    if (!seal) return
    const generation = ++cryptoGeneration.current
    setChanged(tampered)
    setVerification('working')
    try {
      const digest = await sha256(
        tampered ? seal.payload.replace('"simulation": true', '"simulation": false') : seal.payload
      )
      if (generation !== cryptoGeneration.current) return
      const match = digest === seal.digest
      setVerification(match ? 'match' : 'mismatch')
      log(
        match ? 'INTEGRITY_MATCH' : 'INTEGRITY_MISMATCH',
        tampered
          ? 'Payload simulation flag changed; digest no longer matches.'
          : 'Original payload matches the sealed digest.'
      )
    } catch {
      if (generation === cryptoGeneration.current) setVerification('error')
    }
  }
  function exportRecord() {
    const record = {
      format: 'PRAHAAR challenge demo v2',
      simulation: true,
      disclaimer: 'Scripted scenario, not real sensor performance or a production ledger record.',
      snapshot: JSON.parse(seal?.payload ?? currentPayload),
      integrity: seal
        ? {
            algorithm: 'SHA-256',
            expectedDigest: seal.digest,
            testedPayload: verificationPayload,
            result: verification,
            testPayloadChanged: changed,
          }
        : { result: 'NOT_SEALED' },
      sessionAudit: actions,
    }
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' })
    )
    const a = document.createElement('a')
    a.href = url
    a.download = `PRAHAAR-${mission}-challenge.json`
    a.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    log('DEMO_EXPORTED', 'Simulation snapshot and session audit downloaded.')
  }
  const targetDetail =
    selected === 'Person P-01'
      ? `${state.continuity}. Confidence ${Math.round(state.confidence * 100)}%. ${state.lowConfidence ? 'Low confidence: human review required.' : 'Usable scripted observation.'}`
      : selected === 'Animal A-01'
        ? 'Animal class excluded by this people-only zone rule. Its observation is retained. Nearby person is evaluated independently.'
        : selected === 'Vehicle V-01'
          ? 'OCR candidates: DEMO 2026 (0.62), DEMO 2028 (0.31). Plate remains unresolved; proximity to a person is context, not identity.'
          : selected === 'Fence'
            ? `People-only polygon. Three-second dwell threshold. Current dwell: ${state.dwell.toFixed(1)}s. ${state.healthOnly ? 'No intrusion inferred in this maintenance mission.' : 'Operator review follows the rule trigger.'}`
            : selected === 'CAM3'
              ? state.cameraOffline
                ? 'Frozen / offline. Last usable frame is explicitly marked stale. No fresh target detection; coverage compromised.'
                : 'Usable stream. New timestamps resume after recovery; the historical gap remains.'
              : selected === 'CAM1'
                ? state.time >= 40 && state.time < 90
                  ? 'Partial occlusion. Camera-quality warning reduces usable coverage.'
                  : state.fog
                    ? 'Low light and fog reduce scripted confidence. Enhancement changes visualization, not missing evidence.'
                    : 'Entry camera covers detection and candidate ANPR observations.'
                : 'Perimeter camera covers the virtual fence. Candidate handoff and zone observations remain reviewable.'

  return (
    <div className="stress-demo">
      <header className="stress-header">
        <div>
          <div className="stress-eyebrow">
            <Shield size={13} /> PRAHAAR / CHALLENGE LAB <span>SCRIPTED SIMULATION</span>
          </div>
          <h1>When the border gets difficult.</h1>
          <p>One sector. Simultaneous failures. Every decision explained.</p>
        </div>
        <button className="stress-button stress-primary" onClick={judgeTour}>
          <Play size={14} /> 30s judge tour
        </button>
      </header>

      {/* THREAT LEVEL COMMAND BANNER */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 12, marginBottom: 10, padding: '9px 16px', borderRadius: 10,
        background: threatBg,
        border: `1px solid ${threatColor}50`,
        boxShadow: state.risk >= 70 ? `0 0 24px ${threatColor}22, inset 0 1px ${threatColor}20` : `inset 0 1px ${threatColor}10`,
        transition: 'all 0.6s ease',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 9, height: 9, borderRadius: '50%',
            background: threatColor,
            boxShadow: `0 0 10px ${threatColor}, 0 0 22px ${threatColor}70`,
            flexShrink: 0,
          }} />
          <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: 2.5, color: threatColor }}>
            THREAT · {threatLevel}
          </span>
          <span style={{ width: 1, height: 14, background: threatColor, opacity: 0.2, display: 'inline-block' }} />
          <span style={{ fontSize: 10, color: '#5a7888', fontFamily: 'ui-monospace, monospace' }}>
            Risk <span style={{ color: threatColor, fontWeight: 700 }}>{state.risk}</span>/100
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' as const }}>
          {[
            { label: 'CAMERAS', val: state.cameraOffline ? '2/3' : '3/3', ok: !state.cameraOffline },
            { label: 'UPLINK',  val: state.networkOffline ? 'EDGE' : 'LIVE', ok: !state.networkOffline },
            { label: 'EVENTS',  val: String(state.events.length), ok: true },
            { label: 'LATENCY', val: '<300ms', ok: true },
            { label: 'UPTIME',  val: '99.97%', ok: true },
          ].map(chip => (
            <div key={chip.label} style={{
              display: 'flex', flexDirection: 'column' as const, alignItems: 'center',
              padding: '3px 9px', borderRadius: 6,
              background: chip.ok ? '#0a1820' : '#1c1204',
              border: `1px solid ${chip.ok ? '#1e3345' : '#4a3818'}`,
              minWidth: 52,
            }}>
              <span style={{ fontSize: 7, fontWeight: 700, letterSpacing: 1.2, color: '#3a5868' }}>{chip.label}</span>
              <span style={{ fontSize: 10, fontWeight: 700, color: chip.ok ? '#34d399' : '#fbbf24', fontFamily: 'ui-monospace, monospace' }}>{chip.val}</span>
            </div>
          ))}
        </div>
      </div>

      {/* AI MODULE LIVE STATUS BAR */}
      <div style={{
        display: 'flex', gap: 6, marginBottom: 14, padding: '7px 12px',
        background: '#060e18', border: '1px solid #131f2e', borderRadius: 8,
        flexWrap: 'wrap' as const, alignItems: 'center',
      }}>
        <span style={{ fontSize: 8, fontWeight: 700, letterSpacing: 1.8, color: '#2e5060', marginRight: 4 }}>
          AI ENGINES
        </span>
        {aiModules.map(m => (
          <div key={m.name} style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '4px 8px', borderRadius: 5,
            background: m.ok ? '#09141e' : '#0a0a0a',
            border: `1px solid ${m.ok ? '#1a3040' : '#2a2a2a'}`,
          }}>
            <span style={{ fontSize: 8, fontWeight: 700, color: m.ok ? '#4a8898' : '#3a4040', letterSpacing: 0.5 }}>{m.name}</span>
            {m.ok ? (
              <>
                <div style={{ width: 36, height: 3, background: '#0a1820', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${m.pct}%`, background: m.pct > 90 ? '#34d399' : '#fbbf24', borderRadius: 3, transition: 'width 0.5s' }} />
                </div>
                <span style={{ fontSize: 9, fontWeight: 700, color: m.pct > 90 ? '#34d399' : '#fbbf24', fontFamily: 'ui-monospace, monospace' }}>{m.pct}%</span>
              </>
            ) : (
              <span style={{ fontSize: 9, color: '#3a4040' }}>—</span>
            )}
          </div>
        ))}
        <span style={{ marginLeft: 'auto', fontSize: 8, color: '#2e4858', fontFamily: 'ui-monospace, monospace' }}>
          EDGE · 30 FPS · {state.events.length} DETECTIONS
        </span>
      </div>

      <div className="mission-picker" role="group" aria-label="Challenge mission">
        {missions.map((m, i) => (
          <button
            key={m.id}
            aria-pressed={mission === m.id}
            onClick={() => selectMission(m.id)}
            className={mission === m.id ? 'selected' : ''}
          >
            <span className="mission-number">0{i + 1}</span>
            <strong>{m.title}</strong>
            <small>{m.subtitle}</small>
          </button>
        ))}
      </div>

      <div className="stress-toolbar">
        <div className="stress-playback">
          <button
            className="stress-button stress-primary"
            onClick={() => {
              if (time >= CHALLENGE_DURATION) {
                setTime(0)
                clearRun()
                setPlaying(true)
              } else setPlaying(p => !p)
            }}
          >
            {playing ? <Pause size={14} /> : <Play size={14} />}
            {playing ? 'Pause' : time >= CHALLENGE_DURATION ? 'Replay' : 'Play mission'}
          </button>
          <button
            className="stress-button icon-button"
            aria-label="Reset mission"
            onClick={() => {
              setTime(0)
              clearRun()
            }}
          >
            <RotateCcw size={14} />
          </button>
          <select
            aria-label="Playback speed"
            value={speed}
            onChange={e => setSpeed(Number(e.target.value))}
          >
            <option value={1}>1× real time</option>
            <option value={2}>2×</option>
            <option value={5}>5× / 30s tour</option>
          </select>
          <span className="stress-clock">
            T+{Math.floor(time).toString().padStart(3, '0')} / {CHALLENGE_DURATION}s
          </span>
        </div>
        <div className="fault-controls">
          <span>JUDGE CONTROLS</span>
          {faultButtons.map(f => (
            <button
              key={f.id}
              className={`stress-button ${faults[f.id] ? 'fault-active' : ''}`}
              aria-pressed={faults[f.id]}
              onClick={() => inject(f.id)}
            >
              <f.icon size={13} />
              {f.label}
            </button>
          ))}
        </div>
      </div>
      <div className="stress-timeline">
        <input
          aria-label="Mission timeline"
          type="range"
          min="0"
          max={CHALLENGE_DURATION}
          step="0.1"
          value={time}
          onChange={e => seek(Number(e.target.value))}
        />
        <div className="act-buttons">
          {steps.map((act, i) => (
            <button
              key={act.at}
              className={state.act.at === act.at ? 'active' : time > act.at ? 'complete' : ''}
              onClick={() => seek(act.at)}
            >
              <span>{time > act.at ? <Check size={11} /> : `0${i + 1}`}</span>
              {act.name}
              <small>T+{act.at}s</small>
            </button>
          ))}
        </div>
      </div>

      <div className="challenge-layout">
        <section
          className={`stress-world ${focus ? 'stress-focus' : ''}`}
          aria-label="Unified operational frame"
        >
          <div className="world-heading">
            <div>
              <span className="live-dot" />
              <strong>{meta.title}</strong>
              <small>{state.act.description}</small>
            </div>
            <button
              className="stress-button icon-button"
              aria-label={focus ? 'Exit scene focus' : 'Focus scene'}
              onClick={() => setFocus(f => !f)}
            >
              {focus ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            </button>
          </div>
          {focus && (
            <div className="focus-controls">
              <button
                className="stress-button stress-primary"
                onClick={() => setPlaying(p => !p)}
                disabled={time >= CHALLENGE_DURATION}
              >
                {playing ? <Pause size={13} /> : <Play size={13} />}
                {playing ? 'Pause scene' : 'Play scene'}
              </button>
              <input
                type="range"
                aria-label="Scene timeline"
                min="0"
                max={CHALLENGE_DURATION}
                step="0.1"
                value={time}
                onChange={e => seek(Number(e.target.value))}
              />
              <span className="stress-clock">T+{Math.floor(time)}s</span>
              {faultButtons.map(f => (
                <button
                  key={f.id}
                  aria-label={`Scene fault: ${f.label}`}
                  className={`stress-button ${faults[f.id] ? 'fault-active' : ''}`}
                  aria-pressed={faults[f.id]}
                  onClick={() => inject(f.id)}
                >
                  <f.icon size={12} />
                  {f.label}
                </button>
              ))}
            </div>
          )}
          <div className="scene-layers" role="group" aria-label="Scene layers">
            {(['zones', 'tracks', 'routes', 'heatmap', 'enhanced'] as const).map(layer => (
              <button
                key={layer}
                aria-pressed={layers[layer]}
                className={layers[layer] ? 'active' : ''}
                onClick={() => setLayers(l => ({ ...l, [layer]: !l[layer] }))}
              >
                {layer === 'enhanced' ? <Eye size={12} /> : <Layers size={12} />}
                {layer === 'enhanced'
                  ? 'Night enhancement'
                  : layer === 'heatmap'
                    ? 'Risk heatmap'
                    : layer}
              </button>
            ))}
          </div>
          <ChallengeScene
            state={state}
            layers={{ ...layers, routes: layers.routes || tab === 'routes' }}
            selected={selected}
            onSelect={setSelected}
          />
          <div className="frame-pillars">
            <button
              onClick={() => {
                setTab('story')
                setFocus(false)
              }}
            >
              <small>PARAKH</small>
              <strong>
                {state.healthOnly
                  ? 'Maintenance only'
                  : state.intrusion
                    ? `${state.risk}/100 · review`
                    : `${state.dwell.toFixed(1)}s / 3s dwell`}
              </strong>
            </button>
            <button
              onClick={() => {
                setTab('story')
                setFocus(false)
              }}
            >
              <small>SUTRA</small>
              <strong>{time >= 55 ? 'Context timeline ready' : 'Linking observations'}</strong>
            </button>
            <button
              onClick={() => {
                setTab('evidence')
                setFocus(false)
              }}
            >
              <small>PRAMAAN</small>
              <strong>
                {verification === 'match'
                  ? 'Hash verified'
                  : verification === 'mismatch'
                    ? 'Tamper detected'
                    : time >= 125
                      ? 'Ready to seal'
                      : 'Capture provenance'}
              </strong>
            </button>
            <button
              onClick={() => {
                setTab('story')
                setFocus(false)
              }}
            >
              <small>SAKSHAM</small>
              <strong>
                {state.networkOffline
                  ? `${state.queued} queued locally`
                  : `${state.synced} records synced`}
              </strong>
            </button>
            <button
              onClick={() => {
                setTab('routes')
                setFocus(false)
              }}
            >
              <small>MARGDARSHAN</small>
              <strong>B · {state.routes[1].exposure}/100 exposure</strong>
            </button>
          </div>
          <div className="world-telemetry">
            <div>
              <small>VISIBILITY</small>
              <strong className={state.fog ? 'amber' : 'mint'}>
                {state.fog ? 'Fog / low confidence' : 'Clear / usable'}
              </strong>
            </div>
            <div>
              <small>COVERAGE</small>
              <strong className={state.cameraOffline ? 'amber' : 'mint'}>
                {state.cameraOffline ? '2 / 3 cameras usable' : '3 / 3 cameras online'}
              </strong>
            </div>
            <div>
              <small>LOCAL → CENTRAL</small>
              <strong>
                {state.queued} pending / {state.synced} synced
              </strong>
            </div>
            <div>
              <small>ANIMAL RULE</small>
              <strong className="mint">
                {state.animalExcluded
                  ? 'Excluded · person independent'
                  : state.wildlife
                    ? 'Awaiting classification'
                    : 'Not exercised'}
              </strong>
            </div>
          </div>
          <div className="scene-inspector">
            <Crosshair size={15} />
            <div>
              <strong>{selected}</strong>
              <p>{targetDetail}</p>
            </div>
          </div>
        </section>

        <aside className="stress-risk-panel">
          <div className="stress-eyebrow">PARAKH / EXPLAINABLE DECISION</div>
          <div className="risk-score">
            <strong className={state.intrusion ? 'rose' : 'mint'}>
              {state.risk}
              <small>/100</small>
            </strong>
            <span className={state.intrusion ? 'risk-label risk-alert' : 'risk-label'}>
              {state.healthOnly ? 'MAINTENANCE' : state.severity.toUpperCase()}
            </span>
          </div>
          <h2>
            {state.healthOnly
              ? 'A fault is not an intrusion.'
              : decision
                ? decision.action === 'ACKNOWLEDGED'
                  ? 'Acknowledged for review.'
                  : 'Officer rejected this alert.'
                : state.intrusion
                  ? 'Fence dwell needs review.'
                  : 'Observe before escalating.'}
          </h2>
          <p>
            {state.healthOnly
              ? 'Camera issues form a maintenance timeline. No person, plate or intrusion is invented.'
              : state.intrusion
                ? 'Person P-01 remained in the configured zone. Wildlife and vehicle context are evaluated separately.'
                : 'Presence alone does not establish a threat. The fence rule waits for entry and sustained dwell.'}
          </p>
          <div className="dwell-meter">
            <div>
              <span>RECORDED ZONE DWELL</span>
              <strong>{state.dwell.toFixed(1)} / 3.0s</strong>
            </div>
            <div className="meter">
              <i style={{ width: `${(state.dwell / 3) * 100}%` }} />
            </div>
          </div>
          <div className="risk-factors">
            {state.factors.length ? (
              state.factors.map(f => (
                <div key={f.label}>
                  <span>{f.label}</span>
                  <strong className={f.value ? 'cyan' : ''}>+{f.value}</strong>
                </div>
              ))
            ) : (
              <div>
                <span>Intrusion factors applicable</span>
                <strong>0</strong>
              </div>
            )}
          </div>
          {(state.lowConfidence || state.cameraOffline) && (
            <div className="uncertainty">
              <AlertTriangle size={14} />
              <span>
                {state.lowConfidence ? 'Weak visual confidence. ' : ''}
                {state.cameraOffline ? 'CAM3 is unobserved. ' : ''}Human review required; missing
                frames are never filled in.
              </span>
            </div>
          )}
          <div className="review-buttons">
            <button
              className="stress-button stress-primary"
              disabled={!state.intrusion || !!decision}
              onClick={() => decide('ACKNOWLEDGED')}
            >
              <Check size={13} /> Acknowledge
            </button>
            <button
              className="stress-button"
              disabled={!state.intrusion || !!decision}
              onClick={() => decide('REJECTED')}
            >
              <X size={13} /> Reject alert
            </button>
          </div>
          <small className="review-footnote">Demo actions only · no automatic dispatch</small>
        </aside>
      </div>

      <section className="stress-detail">
        <div className="detail-toolbar">
          <div role="tablist" aria-label="Mission detail">
            <button role="tab" aria-selected={tab === 'story'} onClick={() => setTab('story')}>
              <ListChecks size={14} /> Timeline
            </button>
            <button
              role="tab"
              aria-selected={tab === 'features'}
              onClick={() => setTab('features')}
            >
              <Layers size={14} /> Feature coverage{' '}
              <span>
                {activeFeatures.length}/{featureCatalog.length}
              </span>
            </button>
            <button role="tab" aria-selected={tab === 'routes'} onClick={() => setTab('routes')}>
              <Navigation size={14} /> Route comparison
            </button>
            <button
              role="tab"
              aria-selected={tab === 'evidence'}
              onClick={() => setTab('evidence')}
            >
              <Fingerprint size={14} /> Integrity lab
            </button>
          </div>
          <button className="stress-button" onClick={exportRecord}>
            <Download size={13} /> Export demo
          </button>
        </div>
        {message && (
          <div role="status" className="stress-message">
            {message}
          </div>
        )}
        {tab === 'story' && (
          <div className="story-layout">
            <div className="mission-narration">
              <span className="stress-eyebrow">
                ACT {steps.findIndex(a => a.at === state.act.at) + 1} / {steps.length}
              </span>
              <h2>{state.act.name} under pressure.</h2>
              <p>{state.act.description}</p>
              <div className="challenge-summary">
                <strong>
                  {state.intrusion && !state.healthOnly
                    ? '1 contextual intrusion timeline'
                    : state.healthOnly
                      ? '1 maintenance timeline'
                      : 'No intrusion alert yet'}
                </strong>
                <span>
                  {state.events.length} observations / {actions.length} officer & judge actions
                </span>
                <span>
                  {state.animalExcluded
                    ? 'Wildlife alarm suppressed by this rule'
                    : 'Every class follows its configured rule'}
                </span>
              </div>
              <p className="concept-note">
                The scene and sensor readings are scripted. SHA-256 runs locally on actual payload
                bytes. Audio, thermal, weather adaptation and external blockchain are illustrated
                concepts, not validated live integrations.
              </p>
            </div>
            <div className="challenge-event-list" aria-label="Mission event timeline">
              {[
                ...state.events.map(e => ({
                  at: e.at,
                  title: e.title,
                  detail: e.detail,
                  camera: e.camera,
                  kind: e.kind,
                })),
                ...actions.map(a => ({
                  at: a.at,
                  title: a.action.replace(/_/g, ' '),
                  detail: a.detail,
                  camera: 'OFFICER / JUDGE',
                  kind: 'operator',
                })),
              ]
                .sort((a, b) => b.at - a.at)
                .map((e, i) => (
                  <div
                    key={`${e.title}-${e.at}-${i}`}
                    className={`challenge-event event-${e.kind}`}
                  >
                    <span>T+{e.at.toFixed(0)}s</span>
                    <div>
                      <strong>{e.title}</strong>
                      <p>{e.detail}</p>
                    </div>
                    <small>{e.camera}</small>
                  </div>
                ))}
            </div>
          </div>
        )}
        {tab === 'features' && (
          <div className="feature-grid">
            {featureCatalog.map(f => {
              const exercised = activeFeatures.some(a => a.id === f.id)
              return (
                <article key={f.id} className={exercised ? 'exercised' : ''}>
                  <div>
                    <small>{f.module}</small>
                    <span>
                      {exercised
                        ? 'EXERCISED'
                        : time < f.stage
                          ? `AT T+${f.stage}s`
                          : 'NOT IN THIS CASE'}
                    </span>
                  </div>
                  <h3>{f.title}</h3>
                  <p>{f.note}</p>
                  {f.route ? (
                    <Link to={f.route}>
                      Open module <ArrowRight size={12} />
                    </Link>
                  ) : (
                    <small className="concept-note">Scripted concept signal</small>
                  )}
                </article>
              )
            })}
          </div>
        )}
        {tab === 'routes' && (
          <div className="route-layout">
            <div className="mission-narration">
              <span className="stress-eyebrow">MARGDARSHAN / CURRENT CONDITIONS</span>
              <h2>Exposure changes when faults change.</h2>
              <p>
                Toggle camera loss or dense fog above and compare these illustrative route scores.
                Distance and time are fictional; the officer makes the choice.
              </p>
              <div className="uncertainty">
                <AlertTriangle size={14} />
                <span>
                  A lower score indicates lower modeled exposure, not a guarantee of safety.
                </span>
              </div>
            </div>
            {state.routes.map(r => (
              <article className={`route-card ${r.id === 'B' ? 'recommended' : ''}`} key={r.id}>
                <span className="stress-eyebrow">
                  ROUTE {r.id} {r.id === 'B' ? ' / LOWER EXPOSURE' : ''}
                </span>
                <h3>{r.name}</h3>
                <div className="route-score">
                  <strong>
                    {r.exposure}
                    <small>/100</small>
                  </strong>
                  <span>
                    {r.distance}
                    <br />
                    {r.minutes} min
                  </span>
                </div>
                <p>{r.reason}</p>
                <button
                  className="stress-button"
                  disabled={time < 100}
                  onClick={() => {
                    log('ROUTE_REVIEWED', `Route ${r.id} selected for demo review; no dispatch.`)
                    setMessage(
                      `Route ${r.id} recorded as the officer's demo choice. No team was dispatched.`
                    )
                  }}
                >
                  Review route {r.id}
                  <ChevronRight size={13} />
                </button>
              </article>
            ))}
          </div>
        )}
        {tab === 'evidence' && (
          <div className="evidence-layout">
            <div className="mission-narration">
              <span className="stress-eyebrow">PRAMAAN / ACTUAL SHA-256</span>
              <h2>Change one field. Watch integrity fail.</h2>
              <p>
                Seal a frozen snapshot of this demo. The tamper button changes the payload's
                simulation flag and hashes the changed bytes against the original digest.
              </p>
              <button
                className="stress-button stress-primary"
                disabled={time < 125 || verification === 'working'}
                onClick={sealEvidence}
              >
                <Fingerprint size={14} />
                {seal ? 'Seal new snapshot' : 'Seal demo snapshot'}
              </button>
              {time < 125 && <small className="review-footnote">Available in Act 6 · T+125s</small>}
              <p className="concept-note">
                Local content integrity only. No signature, blockchain transaction or court
                admissibility is asserted.
              </p>
            </div>
            <div className="integrity-card">
              <div className={`integrity-result ${verification}`} role="status">
                {verification === 'none'
                  ? 'NOT SEALED'
                  : verification === 'working'
                    ? 'HASHING PAYLOAD…'
                    : verification === 'match'
                      ? 'MATCH / ORIGINAL BYTES VERIFIED'
                      : verification === 'mismatch'
                        ? 'MISMATCH / CONTENT CHANGE DETECTED'
                        : 'VERIFICATION UNAVAILABLE'}
              </div>
              <small>SEALED SHA-256 DIGEST</small>
              <code>
                {seal?.digest ?? 'Seal a snapshot to generate its actual 64-character digest.'}
              </code>
              <div className="review-buttons">
                <button
                  className="stress-button"
                  disabled={!seal || verification === 'working'}
                  onClick={() => verifyEvidence(true)}
                >
                  Tamper one field
                </button>
                <button
                  className="stress-button"
                  disabled={!seal || verification === 'working'}
                  onClick={() => verifyEvidence(false)}
                >
                  Restore & verify
                </button>
              </div>
              {changed && (
                <p className="rose">
                  Changed field: simulation true → false. Export retains the original simulation
                  label and separately records the altered test payload.
                </p>
              )}
              <details>
                <summary>Inspect {seal ? 'sealed' : 'current'} JSON snapshot</summary>
                <pre>{seal ? verificationPayload : currentPayload}</pre>
              </details>
            </div>
          </div>
        )}
      </section>
      <footer className="stress-footer">
        <span>
          <Shield size={12} /> Five pillars · C1–C7 · explainable outcomes
        </span>
        <span>Stress scenario demonstration ≠ validated real-world performance</span>
      </footer>

      {/* EVENT TOAST NOTIFICATIONS */}
      <div style={{
        position: 'fixed', bottom: 24, right: 24, zIndex: 200,
        display: 'flex', flexDirection: 'column' as const, gap: 8,
        pointerEvents: 'none',
      }}>
        {toasts.map(toast => (
          <div key={toast.id} style={{
            background: toast.kind === 'alert' ? '#1a040c' : toast.kind === 'health' ? '#141008' : '#081420',
            border: `1px solid ${toast.kind === 'alert' ? '#fb718555' : toast.kind === 'health' ? '#fbbf2455' : '#22d3ee40'}`,
            borderLeft: `3px solid ${toast.kind === 'alert' ? '#fb7185' : toast.kind === 'health' ? '#fbbf24' : '#22d3ee'}`,
            color: toast.kind === 'alert' ? '#fda4af' : toast.kind === 'health' ? '#fcd34d' : '#7dd3fc',
            padding: '10px 14px', borderRadius: 9, fontSize: 11, fontWeight: 600,
            boxShadow: '0 4px 28px #00000070',
            animation: 'toast-in 0.35s cubic-bezier(0.34,1.56,0.64,1)',
            maxWidth: 290,
          }}>
            <div style={{ fontSize: 8, fontWeight: 700, letterSpacing: 1.5, opacity: 0.6, marginBottom: 3, fontFamily: 'ui-monospace, monospace' }}>
              PRAHAAR · T+{Math.floor(time)}s
            </div>
            {toast.text}
          </div>
        ))}
      </div>

      {/* MISSION COMPLETE OVERLAY */}
      {time >= CHALLENGE_DURATION && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 150,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#00000095', backdropFilter: 'blur(10px)',
          animation: 'fade-in 0.5s ease',
        }}>
          <div style={{
            background: 'linear-gradient(160deg, #08182a, #050d18)',
            border: '1px solid #22d3ee40', borderRadius: 18,
            padding: '44px 52px', maxWidth: 540, width: '90%', textAlign: 'center',
            boxShadow: '0 0 60px #22d3ee14, 0 24px 100px #00000090',
            position: 'relative', overflow: 'hidden',
          }}>
            <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: 3.5, color: '#22d3ee', marginBottom: 14, opacity: 0.8 }}>
              PRAHAAR · SECTOR 04 · SIMULATION END
            </div>
            <div style={{
              fontSize: 36, fontWeight: 900, marginBottom: 6, letterSpacing: -1.5,
              background: 'linear-gradient(135deg, #f1f5f9 40%, #67e8f9)',
              WebkitBackgroundClip: 'text' as const, WebkitTextFillColor: 'transparent',
            }}>
              SECTOR SECURED
            </div>
            <div style={{ color: '#34d399', fontSize: 12, fontWeight: 700, marginBottom: 20, letterSpacing: 1 }}>
              FULL INCIDENT LIFECYCLE DEMONSTRATED
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 10, marginBottom: 26 }}>
              {[
                { label: 'Risk Score', value: `${state.risk}/100`, color: state.risk >= 70 ? '#fb7185' : '#34d399' },
                { label: 'Detections', value: String(state.events.length), color: '#22d3ee' },
                { label: 'Actions', value: String(audit.length), color: '#a78bfa' },
                { label: 'Evidence', value: seal ? 'SEALED' : 'OPEN', color: seal ? '#34d399' : '#fbbf24' },
              ].map(stat => (
                <div key={stat.label} style={{
                  background: '#06101a', border: '1px solid #1a2e40', borderRadius: 10, padding: '14px 8px',
                }}>
                  <div style={{ fontSize: 20, fontWeight: 800, color: stat.color, letterSpacing: -0.5 }}>{stat.value}</div>
                  <div style={{ fontSize: 8, color: '#3a5868', marginTop: 5, letterSpacing: 1.2, fontWeight: 700 }}>{stat.label}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' as const, justifyContent: 'center', marginBottom: 26 }}>
              {['PARAKH', 'C7 ANPR', 'Re-ID', 'SUTRA', 'PRAMAAN', 'SAKSHAM', 'MARGDARSHAN'].map(m => (
                <span key={m} style={{
                  padding: '3px 9px', borderRadius: 5, background: '#0a1c2a',
                  border: '1px solid #1e4040', fontSize: 9, fontWeight: 700, color: '#34d399', letterSpacing: 0.8,
                }}>✓ {m}</span>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button className="stress-button stress-primary"
                onClick={() => { setTime(0); clearRun(); setPlaying(true) }}>
                Replay Mission
              </button>
              <button className="stress-button" onClick={exportRecord}>
                Export Evidence
              </button>
            </div>
            <div style={{ fontSize: 9, color: '#263545', marginTop: 18 }}>
              Scripted simulation · SSB Border Intelligence · SIH Grand Finale
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
