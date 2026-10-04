import { useId } from 'react'
import type { ChallengeState } from './challengeEngine'

export type SceneLayers = {
  zones: boolean
  tracks: boolean
  routes: boolean
  heatmap: boolean
  enhanced: boolean
}

export function ChallengeScene({
  state: s,
  layers,
  selected,
  onSelect,
}: {
  state: ChallengeState
  layers: SceneLayers
  selected: string
  onSelect: (target: string) => void
}) {
  const id = useId().replace(/:/g, '')

  // ── Person path ───────────────────────────────────────────────────────
  const entry = s.entry ?? 45
  const px =
    s.time < 25
      ? 100 + s.time * 7
      : s.time < entry
        ? 275 + ((s.time - 25) * 155) / (entry - 25)
        : Math.min(850, 430 + (s.time - entry) * 17)
  const py =
    s.time < 25
      ? 330
      : s.time < entry
        ? 330 - ((s.time - 25) * 48) / (entry - 25)
        : Math.max(210, 282 - (s.time - entry) * 12)
  const inGap = px > 660 && s.cameraOffline
  const canSee = !s.healthOnly && s.time >= 8 && !inGap
  const tone = s.intrusion ? '#fb7185' : s.dwell > 0 ? '#fbbf24' : '#22d3ee'
  const legSwing = Math.sin(s.time * 5.5) * 5

  function selectProps(target: string) {
    return {
      role: 'button' as const,
      tabIndex: 0,
      'aria-label': `Inspect ${target}`,
      onClick: () => onSelect(target),
      onKeyDown: (e: React.KeyboardEvent<SVGGElement>) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(target) }
      },
      style: { cursor: 'pointer' },
    }
  }

  // ── Camera zone configs ───────────────────────────────────────────────
  const cameras = [
    {
      name: 'CAM1', x: 14, w: 290, color: '#22d3ee',
      status: s.camera1Blur ? 'OPTICAL BLUR' : s.camera1Occluded ? 'PARTIAL OCCLUSION' : s.fog ? 'LOW VIS' : 'ENTRY / ANPR',
      offline: false,
    },
    { name: 'CAM2', x: 314, w: 336, color: '#a78bfa', status: 'FENCE · TRACKING', offline: false },
    {
      name: 'CAM3', x: 660, w: 286, color: s.cameraOffline ? '#fbbf24' : '#34d399',
      status: s.cameraOffline ? 'OFFLINE · STALE' : s.time >= 90 ? 'RECOVERED' : 'EXIT WATCH',
      offline: s.cameraOffline,
    },
  ]

  return (
    <svg
      viewBox="0 0 960 520"
      className="challenge-scene"
      role="group"
      aria-label={`Sector 04 — ${s.mission}. ${s.fog ? 'Fog.' : 'Clear.'} ${s.cameraOffline ? 'CAM3 offline.' : '3 cameras online.'} ${s.intrusion ? 'Person dwell alert active.' : 'No dwell alert.'}`}
    >
      <defs>
        {/* Grid */}
        <pattern id={`grid-${id}`} width="32" height="32" patternUnits="userSpaceOnUse">
          <path d="M32 0H0V32" fill="none" stroke="#1a4040" strokeWidth=".5" opacity=".4" />
        </pattern>
        {/* Scanlines */}
        <pattern id={`scan-${id}`} width="2" height="4" patternUnits="userSpaceOnUse">
          <rect width="2" height="1" fill="#000" opacity=".07" />
        </pattern>
        {/* Fence cross-hatch */}
        <pattern id={`fence-${id}`} width="16" height="16" patternUnits="userSpaceOnUse">
          <path d="M0 0L16 16M16 0L0 16" stroke="#22d3ee" strokeWidth=".6" opacity=".3" />
        </pattern>
        {/* Heat */}
        <radialGradient id={`heat-${id}`}>
          <stop stopColor="#fb7185" stopOpacity=".55" />
          <stop offset="1" stopColor="#fb7185" stopOpacity="0" />
        </radialGradient>
        {/* Night / Fog gradient */}
        <linearGradient id={`fog-${id}`}>
          <stop stopColor="#b8ccd4" stopOpacity=".01" />
          <stop offset=".5" stopColor="#b8ccd4" stopOpacity={layers.enhanced ? '.07' : '.28'} />
          <stop offset="1" stopColor="#b8ccd4" stopOpacity=".01" />
        </linearGradient>
        {/* Camera zone gradients */}
        <linearGradient id={`cam1g-${id}`} x1="0" x2="1" y1="0" y2="0">
          <stop stopColor="#22d3ee" stopOpacity=".04" />
          <stop offset="1" stopColor="#22d3ee" stopOpacity=".01" />
        </linearGradient>
        <linearGradient id={`cam2g-${id}`} x1="0" x2="1" y1="0" y2="0">
          <stop stopColor="#a78bfa" stopOpacity=".04" />
          <stop offset="1" stopColor="#a78bfa" stopOpacity=".01" />
        </linearGradient>
        <linearGradient id={`cam3g-${id}`} x1="0" x2="1" y1="0" y2="0">
          <stop stopColor="#34d399" stopOpacity=".04" />
          <stop offset="1" stopColor="#34d399" stopOpacity=".01" />
        </linearGradient>
      </defs>

      {/* ── Sky / Ground base ─────────────────────────────────────────── */}
      <rect width="960" height="520" fill="#080f18" />
      {/* Mountain silhouette */}
      <path d="M0 80L100 50 180 90 280 30 390 75 500 20 620 65 730 22 840 70 960 35V0H0Z"
        fill="#0f1e28" />
      {/* Treeline */}
      {Array.from({ length: 20 }, (_, i) => (
        <g key={i} transform={`translate(${22 + i * 48} ${85 + (i % 4) * 14})`}>
          <ellipse rx="14" cy="-10" ry="20" fill="#122018" />
          <ellipse rx="10" cy="-22" ry="15" fill="#162a1e" />
        </g>
      ))}
      {/* Water body bottom */}
      <path d="M0 480Q200 440 380 460T700 488T960 460V520H0Z" fill="#0c1e30" />
      <path d="M0 495Q200 455 380 475T700 503T960 475"
        fill="none" stroke="#1e4060" strokeWidth="1.5" opacity=".6" />

      {/* Grid overlay */}
      <rect width="960" height="520" fill={`url(#grid-${id})`} />

      {/* ── Road network ─────────────────────────────────────────────── */}
      {/* Main road */}
      <path d="M-20 337H310L440 333 570 344H990"
        fill="none" stroke="#4a5a52" strokeWidth="52" />
      <path d="M-20 337H310L440 333 570 344H990"
        fill="none" stroke="#1c2830" strokeWidth="44" />
      {/* Road markings */}
      <path d="M-20 337H310L440 333 570 344H990"
        fill="none" stroke="#c8d0bc" strokeWidth="1.5" strokeDasharray="22 18" opacity=".55" />
      {/* Side track */}
      <path d="M180 520V397L335 398 420 420H850V361"
        fill="none" stroke="#243330" strokeWidth="28" />
      <path d="M180 520V397L335 398 420 420H850V361"
        fill="none" stroke="#5e8070" strokeWidth="1" strokeDasharray="6 8" opacity=".5" />

      {/* ── Restricted compound ───────────────────────────────────────── */}
      <rect x="424" y="164" width="218" height="130" fill="#182822"
        stroke={s.intrusion ? '#fb718560' : '#2a4836'} strokeWidth="1.5" />
      <rect x="424" y="276" width="218" height="18" fill={`url(#fence-${id})`} />
      {/* Compound building */}
      <g transform="translate(480 212)">
        <rect width="107" height="39" fill="#2a4236" stroke="#3d5e48" />
        <path d="M-5 0L54-18 112 0" fill="#364e40" />
        <rect x="12" y="9" width="25" height="13" fill="#0a1e1e" />
        <rect x="67" y="9" width="25" height="13" fill="#0a1e1e" />
        {/* Windows glowing */}
        <rect x="14" y="11" width="21" height="9" fill="#0e2e2e" opacity=".7" />
        <rect x="69" y="11" width="21" height="9" fill="#0e2e2e" opacity=".7" />
      </g>
      {/* Compound label */}
      <text x="533" y="184" textAnchor="middle" fill="#8aaaa0" fontSize="10" letterSpacing="2"
        fontWeight="700">RESTRICTED COMPOUND</text>

      {/* ── Entry / Exit posts ────────────────────────────────────────── */}
      <g transform="translate(130 253)">
        <rect width="67" height="37" fill="#2e4038" />
        <path d="M-7 0L33-19 74 0" fill="#3d5546" />
        <rect x="13" y="9" width="40" height="13" fill="#081820" />
        <circle cx="60" cy="3" r="3" fill="#22d3ee" opacity=".8" />
      </g>
      <text x="133" y="245" fill="#6aaa98" fontSize="9" fontWeight="700">ENTRY POST</text>
      <g transform="translate(836 249)">
        <rect width="69" height="40" fill="#2e4038" />
        <path d="M-7 0L34-20 76 0" fill="#3d5546" />
        <circle cx="5" cy="3" r="3" fill="#34d399" opacity=".8" />
      </g>
      <text x="839" y="240" fill="#6aaa98" fontSize="9" fontWeight="700">EXIT POST</text>

      {/* ── Camera coverage zones (SEPARATED, NO OVERLAP) ─────────────── */}
      {cameras.map((cam, ci) => {
        const grad = ci === 0 ? `url(#cam1g-${id})` : ci === 1 ? `url(#cam2g-${id})` : `url(#cam3g-${id})`
        return (
          <g key={cam.name}>
            {/* Coverage zone fill */}
            <rect x={cam.x} y="50" width={cam.w} height="408"
              fill={grad}
              stroke={cam.color}
              strokeOpacity={cam.offline ? '.7' : '.3'}
              strokeWidth={cam.offline ? '2' : '1'}
              strokeDasharray={cam.offline ? '6 4' : '4 6'}
              rx="4" />
            {/* Separator line (except last) */}
            {ci < 2 && (
              <line x1={cam.x + cam.w} y1="50" x2={cam.x + cam.w} y2="458"
                stroke={cam.color} strokeOpacity=".15" strokeWidth="1" />
            )}
            {/* Camera HUD header — clickable */}
            <g {...selectProps(cam.name)}>
              <rect x={cam.x + 6} y="56" width={cam.w - 12} height="44" rx="6"
                fill="#060e18" fillOpacity=".95"
                stroke={selected === cam.name ? '#f8fafc' : cam.color}
                strokeOpacity={selected === cam.name ? '.9' : '.6'}
                strokeWidth={selected === cam.name ? '1.5' : '1'} />
              {/* Live indicator */}
              <circle cx={cam.x + 20} cy="72" r="3.5"
                fill={cam.offline ? '#fbbf24' : cam.color}
                opacity={cam.offline ? '1' : '.9'} />
              {!cam.offline && (
                <circle cx={cam.x + 20} cy="72" r="6"
                  fill="none" stroke={cam.color} strokeWidth=".8" opacity=".4">
                  <animate attributeName="r" values="3.5;8;3.5" dur="2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values=".4;0;.4" dur="2s" repeatCount="indefinite" />
                </circle>
              )}
              <text x={cam.x + 30} y="77" fill={cam.color} fontSize="12" fontWeight="700"
                letterSpacing="1">{cam.name}</text>
              {/* Status badge */}
              <rect x={cam.x + 6} y="84" width={cam.w - 12} height="13" rx="3"
                fill={cam.color} fillOpacity=".08" />
              <text x={cam.x + 14} y="94" fill={cam.offline ? '#fbbf24' : '#b2d0dc'}
                fontSize="9" fontWeight="600" letterSpacing=".8">{cam.status}</text>
            </g>
          </g>
        )
      })}

      {/* ── Heatmap (historical) ──────────────────────────────────────── */}
      {layers.heatmap && (
        <g>
          <ellipse cx="535" cy="282" rx="155" ry="90" fill={`url(#heat-${id})`} />
          <ellipse cx="784" cy="346" rx="110" ry="65" fill={`url(#heat-${id})`} />
          <rect x="16" y="455" width="280" height="18" rx="4" fill="#0a0e18" fillOpacity=".9" />
          <text x="24" y="467" fill="#fda4af" fontSize="9" fontWeight="700">
            ILLUSTRATIVE 7-DAY EXPOSURE LAYER
          </text>
        </g>
      )}

      {/* ── Virtual fence zone (PARAKH) ──────────────────────────────── */}
      {layers.zones && (
        <g {...selectProps('Fence')}>
          <path d="M424 162H642V294H424Z"
            fill={tone} fillOpacity={s.intrusion ? '.12' : '.06'}
            stroke={tone} strokeWidth="2" strokeDasharray="7 4" />
          {/* Fence posts */}
          {[424, 474, 524, 574, 624].map(fx => (
            <rect key={fx} x={fx} y="160" width="3" height="6" fill={tone} opacity=".5" />
          ))}
          {/* Label */}
          <rect x="388" y="110" width="294" height="42" rx="6"
            fill="#05101a" fillOpacity=".95" stroke={tone} strokeWidth="1.5" />
          <text x="535" y="127" textAnchor="middle" fill={tone} fontSize="11" fontWeight="700"
            letterSpacing="1">PARAKH / PEOPLE-ONLY FENCE</text>
          <text x="535" y="143" textAnchor="middle" fill="#94a3b8" fontSize="10">
            {s.healthOnly
              ? 'Rule paused — maintenance mission'
              : s.intrusion
                ? `⚠ 3.0s dwell exceeded · ALERT LOGGED`
                : s.dwell > 0
                  ? `Dwell: ${s.dwell.toFixed(1)}s / 3.0s threshold`
                  : 'Animal class excluded · vehicle context logged'}
          </text>
        </g>
      )}

      {/* ── Tactical Routes ───────────────────────────────────────────── */}
      {layers.routes && (
        <g>
          {/* Route A — direct, riskier */}
          <path d="M180 488V337H850V256"
            fill="none" stroke="#fb7185" strokeWidth="2.5" strokeDasharray="8 5"
            opacity=".8" />
          {/* Route B — safer */}
          <path d="M180 488V398H330L422 421H850V256"
            fill="none" stroke="#34d399" strokeWidth="2.5" strokeDasharray="8 5"
            opacity=".8" />
          {/* Labels */}
          <rect x="470" y="392" width="196" height="22" rx="5" fill="#060e18" fillOpacity=".95" />
          <text x="480" y="407" fill="#34d399" fontSize="10" fontWeight="700">
            B · LOWER EXPOSURE · 6 MIN
          </text>
          <rect x="695" y="348" width="162" height="22" rx="5" fill="#060e18" fillOpacity=".95" />
          <text x="705" y="363" fill="#fb7185" fontSize="10" fontWeight="700">
            A · DIRECT · 4 MIN
          </text>
        </g>
      )}

      {/* ── Person trail ──────────────────────────────────────────────── */}
      {layers.tracks && !s.healthOnly && s.time >= 8 && (
        <path d={`M100 330H275L430 330L${Math.min(px, inGap ? 660 : px)} ${py}`}
          fill="none" stroke="#22d3ee" strokeWidth="2" strokeDasharray="3 5" opacity=".5" />
      )}

      {/* ── Vehicle ───────────────────────────────────────────────────── */}
      {s.vehicle && s.time >= 8 && (
        <g {...selectProps('Vehicle V-01')}
          transform={`translate(${Math.min(386, 90 + s.time * 8)} 349)`}>
          <ellipse rx="42" ry="14" fill="#000" opacity=".35" />
          {/* Car body */}
          <rect x="-36" y="-14" width="72" height="28" rx="8" fill="#d8e2e8" />
          {/* Windshield */}
          <rect x="-14" y="-11" width="28" height="22" rx="3" fill="#1a3a50" opacity=".85" />
          {/* Side panel */}
          <rect x="25" y="-9" width="7" height="18" fill="#2e5570" />
          {/* Wheels */}
          <circle cx="-26" cy="14" r="6" fill="#0a0e14" />
          <circle cx="26" cy="14" r="6" fill="#0a0e14" />
          <circle cx="-26" cy="14" r="3" fill="#3a4a56" />
          <circle cx="26" cy="14" r="3" fill="#3a4a56" />
          {/* Lights */}
          <rect x="27" y="-15" width="8" height="5" rx="2" fill="#fef08a" opacity=".8" />
          <rect x="27" y="10" width="8" height="5" rx="2" fill="#fca5a5" opacity=".7" />
          {/* Bounding box */}
          <rect x="-46" y="-22" width="92" height="52" fill="none" stroke="#22d3ee" strokeWidth="1.5" />
          {/* ANPR label */}
          <rect x="-78" y="30" width="155" height="22" rx="4" fill="#040c14" fillOpacity=".95" />
          <text y="45" textAnchor="middle" fill="#22d3ee" fontSize="10" fontWeight="700">
            {s.time >= 20 ? 'V-01 · PLATE: OCR CANDIDATE' : 'V-01 · VEHICLE DETECTED'}
          </text>
        </g>
      )}

      {/* ── Animal ────────────────────────────────────────────────────── */}
      {s.wildlife && s.time >= 12 && (
        <g {...selectProps('Animal A-01')}
          transform={`translate(${Math.min(612, 362 + (s.time - 12) * 24)} 224)`}>
          <ellipse rx="20" ry="10" fill="#b08850" />
          <path d="M14-2L26-12 34-8M-13 5L-17 17M10 6L15 17"
            fill="none" stroke="#b08850" strokeWidth="4" />
          {/* Green exclusion box */}
          <rect x="-34" y="-24" width="68" height="50"
            fill="none" stroke="#34d399" strokeWidth="1.5" strokeDasharray="3 2" />
          <rect x="-44" y="-40" width="88" height="16" rx="4" fill="#040c14" fillOpacity=".95" />
          <text x="0" y="-29" textAnchor="middle" fill="#34d399" fontSize="10" fontWeight="700">
            A-01 · ANIMAL · EXCLUDED
          </text>
        </g>
      )}

      {/* ── Person ────────────────────────────────────────────────────── */}
      {canSee && (
        <g {...selectProps('Person P-01')} transform={`translate(${px} ${py})`}>
          {/* Shadow */}
          <ellipse cx="0" cy="42" rx="14" ry="5" fill="#000" opacity=".4" />
          {/* Legs — animated */}
          <path d={`M-6 23L${-9 - legSwing} 41M6 23L${9 + legSwing} 41`}
            stroke="#9ab0bc" strokeWidth="7" strokeLinecap="round" />
          {/* Body */}
          <rect x="-12" y="-2" width="24" height="26" rx="4" fill={tone === '#22d3ee' ? '#3a6a8a' : tone === '#fbbf24' ? '#8a6a20' : '#8a2a3a'} />
          {/* Head */}
          <circle cy="-14" r="9" fill="#d4b8a0" />
          {/* Arms */}
          <path d={`M-12 5L${-18 + legSwing * 0.5} 18M12 5L${18 - legSwing * 0.5} 18`}
            stroke="#9ab0bc" strokeWidth="5" strokeLinecap="round" />
          {/* Bounding box */}
          <rect x="-24" y="-26" width="48" height="72" rx="2"
            fill="none" stroke={tone} strokeWidth={s.intrusion ? '2.5' : '1.5'} />
          {/* Track label */}
          <rect x={px > 800 ? -148 : -78} y="-48" width="156" height="20" rx="4"
            fill="#040c14" fillOpacity=".95" />
          <text x={px > 800 ? -70 : 0} y="-34" textAnchor="middle"
            fill={tone} fontSize="10" fontWeight="700">
            P-01 · {Math.round(s.confidence * 100)}% · {s.intrusion ? '⚠ ALERT' : 'PERSON'}
          </text>
        </g>
      )}

      {/* ── CAM3 offline overlay ──────────────────────────────────────── */}
      {s.cameraOffline && (
        <g>
          <rect x="660" y="100" width="286" height="358" fill="#04080f" opacity=".92" />
          {/* X marks */}
          <path d="M676 118L930 440M930 118L676 440"
            stroke="#fbbf24" strokeOpacity=".06" strokeWidth="30" />
          {/* Diagonal scan lines for visual interest */}
          {Array.from({ length: 8 }, (_, i) => (
            <line key={i} x1="660" y1={120 + i * 44} x2="946" y2={120 + i * 44}
              stroke="#fbbf24" strokeOpacity=".025" strokeWidth="1" />
          ))}
          {/* Alert box */}
          <rect x="686" y="195" width="234" height="90" rx="8"
            fill="#100e04" stroke="#fbbf2460" strokeWidth="1.5" />
          <text x="803" y="224" textAnchor="middle" fill="#fbbf24" fontSize="15" fontWeight="800">
            COVERAGE LOST
          </text>
          <text x="803" y="244" textAnchor="middle" fill="#e2c97a" fontSize="10">
            Last usable frame · T+{s.lastFrameAt.toFixed(0)}s
          </text>
          <text x="803" y="260" textAnchor="middle" fill="#8a9aaa" fontSize="10">
            No fresh detection or inferred path
          </text>
          <text x="803" y="280" textAnchor="middle" fill="#fcd34d" fontSize="10">
            {inGap && !s.healthOnly
              ? 'P-01 last seen at CAM2 boundary'
              : 'Adjacent cameras remain operational'}
          </text>
        </g>
      )}

      {/* ── CAM1 blur ─────────────────────────────────────────────────── */}
      {s.camera1Blur && (
        <g pointerEvents="none">
          <foreignObject x="14" y="100" width="290" height="358">
            <div style={{
              width: '100%', height: '100%',
              backdropFilter: 'blur(5px)',
              background: 'rgba(160,180,190,0.07)',
            }} />
          </foreignObject>
          <rect x="34" y="148" width="250" height="36" rx="6"
            fill="#06101a" fillOpacity=".95" stroke="#fbbf24" strokeWidth="1.5" />
          <text x="159" y="170" textAnchor="middle" fill="#fbbf24" fontSize="11" fontWeight="700">
            OPTICAL BLUR · REVIEW QUALITY
          </text>
        </g>
      )}

      {/* ── CAM1 occlusion ────────────────────────────────────────────── */}
      {s.camera1Occluded && (
        <g>
          <rect x="14" y="100" width="118" height="185" fill="#020710" opacity=".78" />
          <text x="28" y="145" fill="#fbbf24" fontSize="9" fontWeight="700">OCCLUDED</text>
        </g>
      )}

      {/* ── Fog layer ─────────────────────────────────────────────────── */}
      {s.fog && (
        <g pointerEvents="none">
          <rect x="0" y="100" width="960" height="320" fill={`url(#fog-${id})`} />
          <path className="fog-drift"
            d="M-100 155Q140 255 330 185T710 235T1110 175"
            stroke="#c0d0d8"
            opacity={layers.enhanced ? '.06' : '.14'}
            strokeWidth="60"
            fill="none" />
          <path className="fog-drift"
            d="M-50 280Q180 220 350 260T750 290T1050 260"
            stroke="#b0c4ce"
            opacity={layers.enhanced ? '.04' : '.1'}
            strokeWidth="40"
            fill="none"
            style={{ animationDelay: '-4s', animationDirection: 'alternate-reverse' }} />
        </g>
      )}

      {/* ── Night darkening ───────────────────────────────────────────── */}
      {s.time >= 12 && (
        <rect width="960" height="520" fill="#02070f"
          opacity={layers.enhanced ? '.04' : '.18'} pointerEvents="none" />
      )}

      {/* ── Scanlines (CRT feel) ──────────────────────────────────────── */}
      <rect width="960" height="520" fill={`url(#scan-${id})`} pointerEvents="none" opacity=".5" />

      {/* ── Status HUD — top left ─────────────────────────────────────── */}
      <rect x="14" y="12" width="380" height="28" rx="5" fill="#040c14" fillOpacity=".95"
        stroke="#1e3345" strokeWidth="1" />
      <text x="26" y="30" fill="#c8dce8" fontSize="11" fontWeight="600" letterSpacing=".8">
        SECTOR 04 · 3-CAMERA COVERAGE · SHARED WORLD
      </text>

      {/* ── Status HUD — top right ────────────────────────────────────── */}
      <rect x="680" y="12" width="268" height="28" rx="5" fill="#040c14" fillOpacity=".95"
        stroke={s.networkOffline ? '#fbbf2460' : '#1e3345'} strokeWidth="1" />
      <text x="694" y="30" fill={s.networkOffline ? '#fbbf24' : '#34d399'}
        fontSize="10" fontWeight="700" letterSpacing=".5">
        {s.networkOffline
          ? `⚡ EDGE LOCAL · ${s.queued} QUEUED`
          : `✓ UPLINK LIVE · ${s.synced} SYNCED`}
      </text>

      {/* ── Bottom caption ────────────────────────────────────────────── */}
      <text x="18" y="508" fill="#344a5a" fontSize="9" letterSpacing=".5">
        N ↑ · SCHEMATIC MAP · CLICK ENTITY OR CAMERA TO INSPECT
      </text>
      <text x="942" y="508" textAnchor="end" fill="#22d3ee" fontSize="10" fontWeight="600">
        {layers.enhanced ? 'NIGHT ENHANCED VIEW' : 'RAW LOW-LIGHT VIEW'}
      </text>
    </svg>
  )
}
