import { DEMO_PLATE, demoClock, scenarioAt, type ScenarioId } from './scenario'

// A shared world coordinate system keeps the subject and coverage boundaries fixed.
export function UnifiedDemoScene({ time, scenario }: { time: number; scenario: ScenarioId }) {
  const state = scenarioAt(time, scenario)
  const x = time <= 24 ? 90 + time * 10 : time <= 48 ? 330 + (time - 24) * 10 : time <= 60 ? 570 + (time - 48) * 6 : Math.min(870, 642 + (time - 60) * 9.5)
  const zoneColor = state.inside ? state.alert ? '#fb7185' : '#fbbf24' : '#94a3b8'
  const dwell = Math.min(3, Math.max(0, time - 39))
  const blur = scenario === 'health' && time >= 12 && time < 24
  const features = [
    { name: 'PARAKH', detail: scenario === 'health' ? 'No intrusion inferred' : scenario === 'animal' && time >= 42 ? 'Animal excluded by rule' : state.alert ? 'Dwell alert · review required' : state.inside ? `Inside · ${dwell.toFixed(1)} / 3s` : 'Fence rule · armed', on: state.alert },
    { name: 'SUTRA', detail: time >= 76 ? 'Related events grouped' : 'Building observation timeline', on: time >= 76 },
    { name: 'PRAMAAN', detail: time >= 113 ? 'Demo record ready to export' : 'Capture times + provenance', on: time >= 113 },
    { name: 'SAKSHAM', detail: time >= 92 ? 'Field report synced' : time >= 87 ? 'Report queued offline' : state.outage ? 'Camera gap · edge buffering' : 'Edge connection available', on: time >= 92 },
    { name: 'MARGDARSHAN', detail: scenario === 'animal' ? 'No response requested' : time >= 101 ? 'Route B suggested · operator decides' : 'Response route comparison', on: time >= 101 && scenario !== 'animal' },
  ]
  return <div className="bg-[#071119]">
    <svg viewBox="0 0 960 540" className="block w-full" role="img" aria-label={`Unified border scene. CAM1 entrance, CAM2 virtual fence, CAM3 exit. ${scenario} scenario at ${time.toFixed(1)} seconds. ${state.outage ? 'CAM3 coverage compromised.' : ''}`}>
      <rect width="960" height="540" fill="#09151e" />
      <path d="M0 168L95 110 170 152 295 82 440 155 580 102 720 166 858 90 960 146V420H0Z" fill="#18332e" />
      <path d="M0 214Q190 180 380 212T760 198T960 210V430H0Z" fill="#234238" />
      <text x="24" y="30" fill="#e2e8f0" fontSize="16" fontWeight="bold">PRAHAAR / INTEGRATED BORDER VIEW</text>
      <text x="936" y="30" textAnchor="end" fill="#94a3b8" fontSize="12">{demoClock(time)} IST · SIMULATION</text>
      {[{ left: 18, right: 325, name: 'CAM1 / CAM-07', desc: 'ENTRY · DETECTION + ANPR', color: '#22d3ee', current: time < 24 }, { left: 335, right: 635, name: 'CAM2 / CAM-08', desc: 'PERIMETER · TRACK + FENCE', color: '#a78bfa', current: time >= 24 && time < 48 }, { left: 645, right: 942, name: 'CAM3 / CAM-12', desc: 'EXIT · HEALTH + REACQUISITION', color: '#34d399', current: time >= 48 }].map(cam => <g key={cam.name}>
        <rect x={cam.left} y="52" width={cam.right - cam.left} height="350" rx="8" fill={cam.color} fillOpacity={cam.current ? '.07' : '.025'} stroke={cam.color} strokeOpacity={cam.current ? '.8' : '.3'} strokeDasharray="6 5" />
        <rect x={cam.left + 9} y="63" width={cam.right - cam.left - 18} height="43" rx="5" fill="#0b1925" />
        <circle cx={cam.left + 22} cy="78" r="4" fill={cam.name.startsWith('CAM3') && state.outage ? '#fbbf24' : cam.color} />
        <text x={cam.left + 34} y="83" fill={cam.color} fontSize="14" fontWeight="bold">{cam.name}</text>
        <text x={cam.left + 20} y="98" fill="#cbd5e1" fontSize="10">{cam.desc}</text>
      </g>)}
      <path d="M0 269H960V371H0Z" fill="#303d46" />
      <path d="M0 320H960" stroke="#b5b9ad" strokeWidth="3" strokeDasharray="30 22" />
      <path d="M0 270H960M0 372H960" stroke="#667b7a" strokeWidth="4" />
      {Array.from({ length: 25 }, (_, i) => <g key={i}><path d={`M${i * 40} 208V259m0-50l40 48m-40 0l40-48`} stroke="#77918b" strokeOpacity=".6" /></g>)}
      <path d="M0 210H960M0 248H960" stroke="#77918b" />
      <rect x="480" y="253" width="90" height="124" fill={zoneColor} fillOpacity=".12" stroke={zoneColor} strokeWidth="2" strokeDasharray="5 3" />
      <path d="M480 245V380" stroke={zoneColor} strokeWidth="3" />
      <rect x="421" y="156" width="208" height="42" rx="5" fill="#0b1925" stroke={zoneColor} />
      <text x="525" y="174" textAnchor="middle" fill={zoneColor} fontSize="12" fontWeight="bold">VIRTUAL FENCE / RESTRICTED</text>
      <text x="525" y="189" textAnchor="middle" fill="#cbd5e1" fontSize="11">{scenario === 'animal' && time >= 42 ? 'Animal excluded · no intrusion' : state.inside ? `DWELL ${dwell.toFixed(1)}s / 3.0s${state.alert ? ' · ALERT' : ''}` : 'People + vehicles · 3s dwell rule'}</text>
      <path d="M525 198V249" stroke={zoneColor} strokeDasharray="3 3" />
      <g transform="translate(52 215)"><rect width="42" height="47" fill="#52625b" /><path d="M-8 0L21-19 50 0Z" fill="#718379" /><rect x="8" y="10" width="24" height="15" fill="#132c38" /></g>
      <g transform="translate(868 213)"><rect width="48" height="49" fill="#52625b" /><path d="M-8 0L24-21 56 0Z" fill="#718379" /><rect x="10" y="12" width="27" height="15" fill="#132c38" /></g>
      {scenario !== 'health' && <g transform={`translate(${x} 300)`}>
        <ellipse cy="38" rx="47" ry="9" fill="#000" opacity=".35" />
        {scenario === 'vehicle' ? <g><path d="M-48 1L-29-21H19L38 0 51 10V29H-51V10Z" fill="#e2e8f0" stroke="#94a3b8" /><path d="M-24-16H-3V0H-35M3-16H16L31 0H3" fill="#2b6074" /><circle cx="-30" cy="28" r="10" fill="#0f172a" /><circle cx="31" cy="28" r="10" fill="#0f172a" /><rect x="-21" y="10" width="45" height="10" rx="2" fill="#fde68a" /></g> : scenario === 'person' ? <g><circle cy="-25" r="9" fill="#c5aa8e" /><path d="M-10-13H10L14 11H-14Z" fill="#b89961" /><path d={`M-6 11L${-10 - Math.sin(time * 5) * 5} 35M6 11L${10 + Math.sin(time * 5) * 5} 35`} stroke="#abc1c7" strokeWidth="7" /></g> : <g><ellipse cy="5" rx="25" ry="14" fill="#ad8b64" /><path d="M17 1L29-18 39-12 27 12M-15 13L-19 35M15 13L19 35" stroke="#ad8b64" strokeWidth="6" /></g>}
        {time >= 3 && <g><rect x="-57" y="-35" width="114" height="79" rx="3" fill="none" stroke={scenario === 'animal' ? '#34d399' : '#22d3ee'} strokeWidth="2" /><rect x="-67" y="-57" width="134" height="20" rx="3" fill="#06121d" /><text y="-43" textAnchor="middle" fill="#67e8f9" fontSize="10">{scenario === 'vehicle' ? time >= 8 ? DEMO_PLATE : 'VEHICLE · TRACK 01' : scenario === 'person' ? 'PERSON · TRACK 01' : 'ANIMAL · NON-TARGET'}</text></g>}
      </g>}
      {scenario === 'vehicle' && time >= 26 && <g transform={`translate(${Math.min(590, 430 + (time - 26) * 4)} 228)`}><circle cy="-18" r="7" fill="#c5aa8e" /><path d="M-8-9H8L11 10H-11M-5 10L-10 28M5 10L10 28" stroke="#b89961" strokeWidth="6" /><rect x="-18" y="-29" width="36" height="63" fill="none" stroke="#38bdf8" /><text x="24" y="-15" fill="#7dd3fc" fontSize="10">PERSON · TRACK 02</text></g>}
      {state.outage && <g><rect x="645" y="111" width="297" height="291" rx="5" fill="#0b1420" fillOpacity=".9" /><text x="793" y="222" textAnchor="middle" fill="#fbbf24" fontSize="16" fontWeight="bold">COVERAGE COMPROMISED</text><text x="793" y="246" textAnchor="middle" fill="#cbd5e1" fontSize="11">CAM3 offline · last frame 14:32:48</text><text x="793" y="266" textAnchor="middle" fill="#94a3b8" fontSize="11">No fresh detections in this region</text></g>}
      {blur && <g><rect x="28" y="115" width="287" height="280" fill="#cbd5e1" fillOpacity=".15" /><text x="172" y="148" textAnchor="middle" fill="#fbbf24" fontSize="13">CAM1 BLUR · QUALITY DEGRADED</text></g>}
      <text x="27" y="392" fill="#94a3b8" fontSize="10">CAM1 → CAM2 → CAM3 · same scene coordinates · camera gaps remain unobserved</text>
      {time >= 96 && scenario !== 'animal' && <g><path d="M96 421H450L690 385H905" fill="none" stroke="#34d399" strokeWidth="3" strokeDasharray="8 5" /><text x="105" y="443" fill="#6ee7b7" fontSize="11">ROUTE B · illustrative response path · operator approval</text></g>}
      {features.map((feature, i) => <g key={feature.name} transform={`translate(${18 + i * 187} 464)`}><rect width="179" height="61" rx="6" fill={feature.on ? '#12342e' : '#0e2230'} stroke={feature.on ? '#34d399' : '#284352'} /><text x="10" y="20" fill={feature.on ? '#6ee7b7' : '#67e8f9'} fontSize="12" fontWeight="bold">{feature.name}</text><foreignObject x="10" y="28" width="159" height="31"><div style={{ color: '#cbd5e1', fontSize: 10, lineHeight: '13px' }}>{feature.detail}</div></foreignObject></g>)}
    </svg>
  </div>
}
