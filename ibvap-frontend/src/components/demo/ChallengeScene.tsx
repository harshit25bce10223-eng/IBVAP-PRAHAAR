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
  const color = s.intrusion ? '#fb7185' : s.dwell > 0 ? '#fbbf24' : '#67e8f9'
  function selectProps(target: string) {
    return {
      role: 'button' as const,
      tabIndex: 0,
      'aria-label': `Inspect ${target}`,
      onClick: () => onSelect(target),
      onKeyDown: (e: React.KeyboardEvent<SVGGElement>) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect(target)
        }
      },
      style: { cursor: 'pointer' },
    }
  }
  return (
    <svg
      viewBox="0 0 960 520"
      className="challenge-scene"
      role="group"
      aria-label={`Single sector view for ${s.mission}. ${s.fog ? 'Fog and low light.' : 'Clear visibility.'} ${s.cameraOffline ? 'CAM3 coverage compromised.' : 'Three camera regions available.'} ${s.intrusion ? 'Person dwell alert.' : 'No person dwell alert yet.'}`}
    >
      <defs>
        <pattern id={`grid-${id}`} width="32" height="32" patternUnits="userSpaceOnUse">
          <path d="M32 0H0V32" fill="none" stroke="#3c746f" strokeWidth=".6" opacity=".15" />
        </pattern>
        <pattern id={`fence-${id}`} width="18" height="18" patternUnits="userSpaceOnUse">
          <path d="M0 0L18 18M18 0L0 18" stroke="#729389" strokeWidth=".7" />
        </pattern>
        <radialGradient id={`heat-${id}`}>
          <stop stopColor="#fb7185" stopOpacity=".5" />
          <stop offset="1" stopColor="#fb7185" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`fog-${id}`}>
          <stop stopColor="#b8ccd4" stopOpacity=".02" />
          <stop offset=".5" stopColor="#b8ccd4" stopOpacity={layers.enhanced ? '.09' : '.3'} />
          <stop offset="1" stopColor="#b8ccd4" stopOpacity=".03" />
        </linearGradient>
      </defs>
      <rect width="960" height="520" fill="#102820" />
      <path d="M0 57L160 97 227 31 338 84 469 19 627 69 718 26 838 87 960 30V0H0Z" fill="#1e3b30" />
      <path d="M0 466Q185 410 308 450T620 476T960 434V520H0Z" fill="#163947" />
      <path
        d="M0 482Q185 426 308 466T620 492T960 450"
        fill="none"
        stroke="#427681"
        strokeWidth="2"
        opacity=".5"
      />
      <rect width="960" height="520" fill={`url(#grid-${id})`} />
      {Array.from({ length: 18 }, (_, i) => (
        <g key={i} transform={`translate(${30 + i * 51} ${95 + (i % 3) * 26})`}>
          <circle r="16" fill="#274b37" />
          <circle cx="-5" cy="-5" r="11" fill="#2f5940" />
        </g>
      ))}
      <path d="M-30 337H310L440 333 570 344H990" fill="none" stroke="#66756b" strokeWidth="91" />
      <path d="M-30 337H310L440 333 570 344H990" fill="none" stroke="#303d44" strokeWidth="83" />
      <path
        d="M-30 337H310L440 333 570 344H990"
        fill="none"
        stroke="#a7b4ac"
        strokeWidth="2"
        strokeDasharray="18 15"
      />
      <path
        d="M180 520V397L335 398 420 420H850V361"
        fill="none"
        stroke="#2d423a"
        strokeWidth="35"
      />
      <path
        d="M180 520V397L335 398 420 420H850V361"
        fill="none"
        stroke="#7d9989"
        strokeWidth="1"
        strokeDasharray="6 8"
      />
      <rect x="424" y="164" width="218" height="130" fill="#2b3829" stroke="#637762" />
      <rect x="424" y="276" width="218" height="18" fill={`url(#fence-${id})`} />
      <text x="533" y="189" textAnchor="middle" fill="#b8c5ab" fontSize="12" letterSpacing="2">
        RESTRICTED COMPOUND
      </text>
      <g transform="translate(480 212)">
        <rect width="107" height="39" fill="#506251" stroke="#798978" />
        <path d="M-5 0L54-18 112 0" fill="#71816a" />
        <rect x="12" y="9" width="25" height="13" fill="#102323" />
        <rect x="67" y="9" width="25" height="13" fill="#102323" />
      </g>
      <g transform="translate(130 253)">
        <rect width="67" height="37" fill="#51625a" />
        <path d="M-7 0L33-19 74 0" fill="#7a8875" />
        <rect x="13" y="9" width="40" height="13" fill="#10262c" />
      </g>
      <text x="133" y="245" fill="#94b5ad" fontSize="10">
        ENTRY POST
      </text>
      <g transform="translate(836 249)">
        <rect width="69" height="40" fill="#51625a" />
        <path d="M-7 0L34-20 76 0" fill="#7a8875" />
      </g>
      <text x="839" y="240" fill="#94b5ad" fontSize="10">
        EXIT POST
      </text>
      {layers.heatmap && (
        <g>
          <ellipse cx="535" cy="282" rx="160" ry="94" fill={`url(#heat-${id})`} />
          <ellipse cx="784" cy="346" rx="120" ry="70" fill={`url(#heat-${id})`} />
          <text x="25" y="471" fill="#fda4af" fontSize="10">
            ILLUSTRATIVE HISTORICAL EXPOSURE LAYER
          </text>
        </g>
      )}
      {[
        {
          name: 'CAM1',
          left: 16,
          width: 287,
          tint: '#22d3ee',
          sub: s.camera1Blur
            ? 'OPTICAL BLUR / DEGRADED'
            : s.camera1Occluded
              ? 'PARTIAL OCCLUSION'
              : s.fog
                ? 'LOW VISIBILITY'
                : 'ENTRY / ANPR',
        },
        { name: 'CAM2', left: 313, width: 337, tint: '#a78bfa', sub: 'FENCE / TRACKING' },
        {
          name: 'CAM3',
          left: 660,
          width: 284,
          tint: s.cameraOffline ? '#fbbf24' : '#34d399',
          sub: s.cameraOffline
            ? 'OFFLINE · STALE FRAME'
            : s.time >= 90
              ? 'RECOVERED / FRESH'
              : 'EXIT / COVERAGE',
        },
      ].map(cam => (
        <g key={cam.name}>
          <rect
            x={cam.left}
            y="52"
            width={cam.width}
            height="403"
            rx="7"
            fill={cam.tint}
            fillOpacity=".025"
            stroke={cam.tint}
            strokeOpacity=".45"
            strokeDasharray="5 7"
          />
          <g {...selectProps(cam.name)}>
            <rect
              x={cam.left + 10}
              y="64"
              width={cam.width - 20}
              height="42"
              rx="5"
              fill="#081720"
              stroke={selected === cam.name ? '#f8fafc' : cam.tint}
              strokeOpacity=".7"
            />
            <circle cx={cam.left + 24} cy="79" r="4" fill={cam.tint} />
            <text x={cam.left + 36} y="83" fill={cam.tint} fontSize="13" fontWeight="bold">
              {cam.name}
            </text>
            <text x={cam.left + 24} y="98" fill="#bdced5" fontSize="10">
              {cam.sub}
            </text>
          </g>
        </g>
      ))}
      {layers.zones && (
        <g {...selectProps('Fence')}>
          <path
            d="M424 162H642V294H424Z"
            fill={color}
            fillOpacity=".08"
            stroke={color}
            strokeWidth="2"
            strokeDasharray="7 4"
          />
          <rect x="390" y="116" width="281" height="35" rx="5" fill="#0a1822" stroke={color} />
          <text x="530" y="131" textAnchor="middle" fill={color} fontSize="11" fontWeight="bold">
            PARAKH / PEOPLE-ONLY FENCE
          </text>
          <text x="530" y="144" textAnchor="middle" fill="#cbd5e1" fontSize="10">
            {s.healthOnly
              ? 'Rule paused for maintenance case'
              : s.intrusion
                ? '3.0s dwell · operator review'
                : s.dwell > 0
                  ? `${s.dwell.toFixed(1)}s / 3.0s dwell`
                  : 'Animal excluded · vehicle proximity is context'}
          </text>
        </g>
      )}
      {layers.routes && (
        <g>
          <path
            d="M180 488V337H850V256"
            fill="none"
            stroke="#fb7185"
            strokeWidth="3"
            strokeDasharray="8 6"
          />
          <path
            d="M180 488V398H330L422 421H850V256"
            fill="none"
            stroke="#34d399"
            strokeWidth="3"
            strokeDasharray="8 6"
          />
          <rect x="472" y="394" width="181" height="21" rx="4" fill="#0a1822" />
          <text x="482" y="408" fill="#6ee7b7" fontSize="10">
            B / LOWER EXPOSURE · 6 MIN
          </text>
          <rect x="699" y="354" width="150" height="21" rx="4" fill="#0a1822" />
          <text x="709" y="368" fill="#fda4af" fontSize="10">
            A / DIRECT · 4 MIN
          </text>
        </g>
      )}
      {layers.tracks && !s.healthOnly && s.time >= 8 && (
        <path
          d={`M100 330H275L430 330L${Math.min(px, 660)} ${py}`}
          fill="none"
          stroke="#67e8f9"
          strokeWidth="2"
          strokeDasharray="3 5"
          opacity=".6"
        />
      )}
      {s.vehicle && s.time >= 8 && (
        <g
          {...selectProps('Vehicle V-01')}
          transform={`translate(${Math.min(386, 90 + s.time * 8)} 349)`}
        >
          <ellipse rx="39" ry="16" fill="#000" opacity=".3" />
          <rect x="-34" y="-14" width="68" height="28" rx="7" fill="#e2e8f0" />
          <rect x="-12" y="-11" width="26" height="22" rx="3" fill="#24465a" />
          <rect x="23" y="-9" width="6" height="18" fill="#355d72" />
          <rect x="-28" y="-19" width="10" height="5" fill="#071119" />
          <rect x="-28" y="14" width="10" height="5" fill="#071119" />
          <rect x="18" y="-19" width="10" height="5" fill="#071119" />
          <rect x="18" y="14" width="10" height="5" fill="#071119" />
          <rect
            x="-44"
            y="-25"
            width="88"
            height="50"
            fill="none"
            stroke="#22d3ee"
            strokeWidth="1.5"
          />
          <rect x="-75" y="29" width="150" height="23" rx="4" fill="#0a1822" />
          <text y="44" textAnchor="middle" fill="#67e8f9" fontSize="10">
            {s.time >= 20 ? 'V-01 / OCR NEEDS REVIEW' : 'V-01 / VEHICLE'}
          </text>
        </g>
      )}
      {s.wildlife && s.time >= 12 && (
        <g
          {...selectProps('Animal A-01')}
          transform={`translate(${Math.min(612, 362 + (s.time - 12) * 24)} 224)`}
        >
          <ellipse rx="19" ry="9" fill="#be9b68" />
          <path
            d="M14-2L25-12 32-8M-12 5L-16 17M9 6L14 17"
            fill="none"
            stroke="#be9b68"
            strokeWidth="4"
          />
          <rect x="-32" y="-24" width="65" height="49" fill="none" stroke="#34d399" />
          <text x="0" y="-31" textAnchor="middle" fill="#6ee7b7" fontSize="10">
            A-01 / EXCLUDED
          </text>
        </g>
      )}
      {canSee && (
        <g {...selectProps('Person P-01')} transform={`translate(${px} ${py})`}>
          <circle cy="-8" r="8" fill="#d3b99b" />
          <path d="M-10 2H10L14 23H-14Z" fill="#b89961" />
          <path
            d={`M-7 23L${-10 - Math.sin(s.time * 6) * 4} 37M7 23L${10 + Math.sin(s.time * 6) * 4} 37`}
            stroke="#bbc7c9"
            strokeWidth="6"
          />
          <rect
            x="-24"
            y="-24"
            width="48"
            height="69"
            rx="2"
            fill="none"
            stroke={color}
            strokeWidth="2"
          />
          <rect x={px > 800 ? -138 : -72} y="-47" width="144" height="20" rx="4" fill="#0a1822" />
          <text x={px > 800 ? -66 : 0} y="-33" textAnchor="middle" fill={color} fontSize="10">
            P-01 / {Math.round(s.confidence * 100)}% · {s.intrusion ? 'ALERT LOGGED' : 'PERSON'}
          </text>
        </g>
      )}
      {s.cameraOffline && (
        <g>
          <rect x="660" y="110" width="284" height="345" fill="#08121f" opacity=".88" />
          <path
            d="M674 126L930 440M930 126L674 440"
            stroke="#fbbf24"
            strokeOpacity=".08"
            strokeWidth="25"
          />
          <text x="802" y="234" textAnchor="middle" fill="#fbbf24" fontSize="17" fontWeight="bold">
            COVERAGE LOST
          </text>
          <text x="802" y="256" textAnchor="middle" fill="#cbd5e1" fontSize="11">
            Last frame · T+{s.lastFrameAt.toFixed(0)}s
          </text>
          <text x="802" y="275" textAnchor="middle" fill="#94a3b8" fontSize="10">
            No fresh detections or inferred path
          </text>
          <text x="802" y="305" textAnchor="middle" fill="#fcd34d" fontSize="11">
            {inGap && !s.healthOnly
              ? 'P-01 last seen near CAM2 boundary'
              : 'Other camera regions remain available'}
          </text>
        </g>
      )}
      {s.camera1Blur && (
        <g pointerEvents="none">
          <foreignObject x="16" y="110" width="287" height="345">
            <div
              style={{
                width: '100%',
                height: '100%',
                backdropFilter: 'blur(4px)',
                background: '#92a5b516',
              }}
            />
          </foreignObject>
          <rect x="40" y="151" width="237" height="38" rx="5" fill="#081720" stroke="#fbbf24" />
          <text x="158" y="174" textAnchor="middle" fill="#fbbf24" fontSize="12">
            OPTICAL BLUR / REVIEW QUALITY
          </text>
        </g>
      )}
      {s.camera1Occluded && (
        <g>
          <rect x="16" y="110" width="118" height="185" fill="#02070d" opacity=".7" />
          <text x="28" y="143" fill="#fbbf24" fontSize="10">
            OCCLUDED
          </text>
        </g>
      )}
      {s.fog && (
        <g pointerEvents="none">
          <rect x="0" y="110" width="960" height="320" fill={`url(#fog-${id})`} />
          <path
            className="fog-drift"
            d="M-100 150Q130 250 320 180T700 230T1100 170"
            stroke="#bacdd1"
            opacity={layers.enhanced ? '.08' : '.16'}
            strokeWidth="58"
            fill="none"
          />
        </g>
      )}
      {s.time >= 12 && (
        <rect
          width="960"
          height="520"
          fill="#030b22"
          opacity={layers.enhanced ? '.03' : '.16'}
          pointerEvents="none"
        />
      )}
      <rect x="16" y="13" width="448" height="27" rx="5" fill="#081720" />
      <text x="27" y="31" fill="#e2e8f0" fontSize="12" letterSpacing="1">
        SECTOR 04 / SHARED WORLD · 3 COVERAGE REGIONS
      </text>
      <rect x="700" y="13" width="243" height="27" rx="5" fill="#081720" />
      <text x="713" y="31" fill={s.networkOffline ? '#fbbf24' : '#6ee7b7'} fontSize="11">
        {s.networkOffline
          ? `EDGE LOCAL / ${s.queued} RECORDS PENDING`
          : `UPLINK ONLINE / ${s.synced} RECORDS SYNCED`}
      </text>
      <text x="18" y="501" fill="#9bb6b6" fontSize="10">
        N ↑ · SCHEMATIC COORDINATES · CLICK AN ENTITY OR CAMERA TO INSPECT
      </text>
      <text x="942" y="501" textAnchor="end" fill="#67e8f9" fontSize="11">
        {layers.enhanced ? 'ENHANCED VIEW / SCRIPTED' : 'RAW LOW-LIGHT VIEW'}
      </text>
    </svg>
  )
}
