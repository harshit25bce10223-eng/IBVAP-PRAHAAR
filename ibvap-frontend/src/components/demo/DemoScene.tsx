import { DEMO_PLATE, demoClock, scenarioAt, type ScenarioId } from './scenario'
import { useId } from 'react'

export function DemoScene({ time, camera, scenario = 'vehicle', className }: { time: number; camera?: string; scenario?: ScenarioId; className?: string }) {
  const state = scenarioAt(time, scenario)
  const sceneId = useId()
  const view = camera ?? state.camera
  const active = view === state.camera
  const seenAt = view === 'CAM-07' ? 8 : view === 'CAM-08' ? 28 : 62
  const seen = time >= seenAt
  const local = view === 'CAM-07' ? time : view === 'CAM-08' ? time - 24 : time - 60
  const frozen = view === 'CAM-12' && state.outage
  const progress = active && !frozen ? Math.max(0, Math.min(1, local / 24)) : seen ? 0.85 : 0
  const x = 100 + progress * 670
  const y = view === 'CAM-08' ? 260 : 280
  const visibleCar = scenario !== 'health' && !frozen && (active || seen)
  const blurred = scenario === 'health' && view === 'CAM-07' && time >= 12 && time < 24
  const stamp = frozen ? 48 : active ? time : seen ? seenAt : 0
  const tone = view === 'CAM-08' && state.inside ? state.alert ? '#fb7185' : '#fbbf24' : '#67e8f9'

  return (
    <div className={`relative overflow-hidden rounded-xl border border-slate-700 bg-[#071119] ${className ?? ""}`}>
      <svg viewBox="0 0 960 500" className="block w-full h-auto max-h-full object-contain mx-auto" role="img" aria-label={`${view}: ${frozen ? 'frozen frame, camera offline' : blurred ? 'blurred camera image' : visibleCar ? `simulated ${scenario === 'vehicle' ? 'white car' : scenario} moving through checkpoint` : 'waiting for observation'}`}>
        <defs>
          <linearGradient id={`sky-${sceneId}`} x2="0" y2="1"><stop stopColor="#324b58" /><stop offset="1" stopColor="#0b1c28" /></linearGradient>
          <pattern id={`scan-${sceneId}`} width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0 0H4" stroke="#000" strokeOpacity=".14" /></pattern>
        </defs>
        <g style={{ filter: blurred ? 'blur(7px)' : undefined }}>
        <rect width="960" height="500" fill={`url(#sky-${sceneId})`} />
        <path d="M0 165L120 85 240 150 350 60 460 140 620 80 750 160 900 85 960 140V500H0Z" fill="#18312f" />
        <path d="M0 215L170 180 370 210 520 175 790 210 960 170V500H0Z" fill="#233a32" />
        <path d="M0 250L960 215V380L0 420Z" fill="#39424a" />
        <path d="M0 330L960 292" stroke="#c0bda6" strokeWidth="4" strokeDasharray="45 30" opacity=".6" />
        <path d="M0 235L960 200M0 430L960 390" stroke="#92978b" strokeWidth="5" />
        {Array.from({ length: 13 }, (_, i) => <g key={i} opacity=".7"><path d={`M${i * 80} 190V245`} stroke="#8ea8ac" strokeWidth="3" /><path d={`M${i * 80} 190l80 55m-80 0l80-55`} stroke="#749090" /></g>)}
        <path d="M0 195H960M0 220H960" stroke="#7d9698" opacity=".6" />
        <g transform={view === 'CAM-12' ? 'translate(90 5)' : 'translate(730 0)'}>
          <rect x="0" y="112" width="100" height="92" fill="#65736b" /><path d="M-10 112L50 78 110 112Z" fill="#364e4d" /><rect x="15" y="128" width="32" height="30" fill="#172c33" /><rect x="65" y="135" width="22" height="69" fill="#263b3c" />
          <rect x="-15" y="207" width="10" height="70" fill="#b6aa88" /><path d="M-10 207H125" stroke="#c9c2ae" strokeWidth="8" strokeDasharray="16 8" />
        </g>
        {view === 'CAM-08' && scenario !== 'health' && <g><path d="M510 225L890 210V373L510 389Z" fill={`${tone}18`} stroke={tone} strokeWidth="2" strokeDasharray="8 4" /><text x="540" y="365" fill={tone} fontSize="14">{scenario === 'animal' ? 'RULE: PEOPLE + VEHICLES ONLY' : 'RESTRICTED ZONE · 3s DWELL RULE'}</text></g>}
        {visibleCar && <g style={{ transform: `translate(${x}px, ${y}px)`, transition: 'transform 100ms linear' }}>
          <ellipse cx="0" cy="44" rx="78" ry="13" fill="#000" opacity=".4" />
          {scenario === 'vehicle' && <g>
          <path d="M-68 5L-45-25H30L56 0 74 12V37H-76V14Z" fill="#e0e5e4" stroke="#9cacb3" strokeWidth="2" />
          <path d="M-37-20H-5V0H-53ZM2-20H26L46 0H2Z" fill="#254c61" />
          <circle cx="-44" cy="35" r="16" fill="#10171e" /><circle cx="42" cy="35" r="16" fill="#10171e" /><circle cx="-44" cy="35" r="7" fill="#8e9aa4" /><circle cx="42" cy="35" r="7" fill="#8e9aa4" />
          <rect x="-31" y="11" width="72" height="16" rx="2" fill="#f9f6d8" /><text x="5" y="23" textAnchor="middle" fill="#17212b" fontSize="11" fontWeight="bold">{DEMO_PLATE}</text>
          </g>}
          {scenario === 'person' && <g><circle cx="0" cy="-27" r="13" fill="#c5aa8e" /><path d="M-14-10H14L20 20H-20Z" fill="#b89961" /><path d={`M-9 19L${-15 - Math.sin(time * 5) * 8} 45M9 19L${15 + Math.sin(time * 5) * 8} 45`} stroke="#243746" strokeWidth="10" /><path d="M-14-6L-25 15M14-6L25 15" stroke="#b89961" strokeWidth="8" /></g>}
          {scenario === 'animal' && <g><ellipse cx="0" cy="5" rx="41" ry="23" fill="#9a7a58" /><path d="M25 0L43-28 61-18 45 15" fill="#9a7a58" /><path d={`M-26 17L${-30 - Math.sin(time * 5) * 6} 44M23 17L${27 + Math.sin(time * 5) * 6} 44`} stroke="#866649" strokeWidth="8" /><path d="M45-27L38-40M51-25L59-37M-35 0L-53-12" stroke="#b7a284" strokeWidth="4" /></g>}
          {time >= 3 && <g><rect x="-88" y="-48" width="177" height="107" fill="none" stroke={tone} strokeWidth="2" /><rect x="-88" y="-72" width="210" height="22" fill="#06131e" /><text x="-80" y="-57" fill={tone} fontSize="12">{scenario === 'vehicle' ? 'VEHICLE · DEMO-CAR-01' : scenario === 'person' ? 'PERSON · TRACK-01' : 'ANIMAL · NON-TARGET CLASS'}</text></g>}
        </g>}
        </g>
        <rect width="960" height="500" fill={`url(#scan-${sceneId})`} pointerEvents="none" />
        <rect x="18" y="18" width="350" height="33" rx="4" fill="#051018" opacity=".9" /><text x="30" y="40" fill="#bde7ee" fontSize="15" fontFamily="monospace">{view} · {frozen ? 'OFFLINE / LAST FRAME' : active ? 'ANIMATED DEMO' : scenario === 'health' ? 'REFERENCE VIEW' : seen ? 'CAPTURED SIGHTING' : 'WAITING'}</text>
        <rect x="620" y="18" width="322" height="33" rx="4" fill="#051018" opacity=".9" /><text x="635" y="40" fill="#bde7ee" fontSize="14" fontFamily="monospace">30 SEP 2026 · {demoClock(stamp)} IST</text>
        <text x="24" y="475" fill="#cbd5e1" fontSize="13">ILLUSTRATED SIMULATION · FICTIONAL SCENARIO · NOT LIVE FOOTAGE</text>
        {blurred && <g><rect x="230" y="80" width="500" height="45" rx="5" fill="#15100a" /><text x="480" y="109" fill="#fbbf24" textAnchor="middle" fontSize="20">IMAGE BLUR · FRAME QUALITY DEGRADED</text></g>}
        {frozen && <g><rect width="960" height="500" fill="#06101b" opacity=".64" /><text x="480" y="238" fill="#fbbf24" fontSize="28" textAnchor="middle">CAMERA CONNECTION LOST</text><text x="480" y="275" fill="#cbd5e1" fontSize="17" textAnchor="middle">Last frame: 14:32:48 · New observations paused</text></g>}
      </svg>
    </div>
  )
}
