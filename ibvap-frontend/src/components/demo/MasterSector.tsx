import { useId } from 'react'
import { ENTITY_ID, INCIDENT_ID, masterClock, type MasterState } from './masterStory'

export function MasterSector({
  state: s,
  enhanced,
  heatmap,
  routes,
  selected,
  onSelect,
}: {
  state: MasterState
  enhanced: boolean
  heatmap: boolean
  routes: boolean
  selected: string
  onSelect: (id: string) => void
}) {
  const id = useId().replace(/:/g, '')
  const zoneColor = s.alert ? '#D62828' : s.crossed ? '#F4B942' : '#809b8a'
  const selectable = (target: string) => ({
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
  })
  return (
    <svg
      viewBox="0 0 960 510"
      className="master-sector"
      role="group"
      aria-label={`Shared border sector at ${masterClock(s.capture)}. ${s.associated ? `Candidate entity ${ENTITY_ID}.` : 'Camera-local observations.'} ${s.cameraOffline ? 'CAM-03 coverage compromised.' : 'Four replay camera regions.'}`}
    >
      <defs>
        <pattern id={`master-grid-${id}`} width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M40 0H0V40" fill="none" stroke="#577162" strokeOpacity=".2" strokeWidth=".7" />
        </pattern>
        <pattern id={`master-fence-${id}`} width="16" height="16" patternUnits="userSpaceOnUse">
          <path d="M0 0L16 16M16 0L0 16" stroke="#a1aa99" strokeOpacity=".45" strokeWidth=".7" />
        </pattern>
        <radialGradient id={`master-heat-${id}`}>
          <stop stopColor="#D62828" stopOpacity=".5" />
          <stop offset="1" stopColor="#D62828" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="960" height="510" fill="#20372d" />
      <path
        d="M0 70L84 119 203 52 292 109 425 34 544 91 672 39 817 115 960 39V0H0Z"
        fill="#2b4435"
      />
      <rect width="960" height="510" fill={`url(#master-grid-${id})`} />
      {Array.from({ length: 20 }, (_, i) => (
        <g key={i} transform={`translate(${35 + i * 47} ${117 + (i % 3) * 27})`}>
          <circle r="15" fill="#344f39" />
          <circle cx="-5" cy="-4" r="9" fill="#3b5940" />
        </g>
      ))}
      <path d="M0 442Q188 413 335 465T642 451T960 427V510H0Z" fill="#263f4a" />
      <path
        d="M0 456Q188 427 335 479T642 465T960 441"
        fill="none"
        stroke="#687d80"
        strokeOpacity=".45"
      />
      <path d="M0 352H240L365 344 618 358H960" fill="none" stroke="#7b8271" strokeWidth="81" />
      <path d="M0 352H240L365 344 618 358H960" fill="none" stroke="#454e4e" strokeWidth="73" />
      <path
        d="M0 352H240L365 344 618 358H960"
        fill="none"
        stroke="#cbcbbb"
        strokeWidth="2"
        strokeDasharray="18 14"
        opacity=".65"
      />
      <path d="M145 508V411H310L430 437H870V365" fill="none" stroke="#56644f" strokeWidth="25" />
      <path
        d="M145 508V411H310L430 437H870V365"
        fill="none"
        stroke="#b0baa8"
        strokeOpacity=".45"
        strokeDasharray="7 8"
      />
      <g transform="translate(141 263)">
        <rect width="62" height="45" fill="#65715f" />
        <path d="M-7 0L31-21 69 0" fill="#889079" />
        <rect x="12" y="9" width="38" height="17" fill="#18312e" />
      </g>
      <text x="131" y="252" fontSize="10" fill="#c5cec3">
        ENTRY CHECKPOINT
      </text>
      <rect x="360" y="165" width="225" height="125" fill="#374533" stroke="#839179" />
      <rect x="360" y="273" width="225" height="17" fill={`url(#master-fence-${id})`} />
      <rect x="433" y="217" width="98" height="36" fill="#65715f" />
      <path d="M423 217L480 192 540 217" fill="#889079" />
      <text x="471" y="184" textAnchor="middle" fontSize="11" fill="#d0d7ca" letterSpacing="1">
        ZONE A / RESTRICTED
      </text>
      <path
        d="M360 165H585V290H360Z"
        fill={zoneColor}
        fillOpacity=".07"
        stroke={zoneColor}
        strokeWidth="2"
        strokeDasharray="7 5"
      />
      <text x="361" y="307" fill={s.alert ? '#f0a6a6' : '#cbd6c9'} fontSize="10">
        {s.alert ? 'EVT-2291 / RECORDED DWELL 3s' : 'PEOPLE-ONLY POLYGON / 3s DWELL'}
      </text>
      <g transform="translate(863 249)">
        <rect width="65" height="50" fill="#65715f" />
        <path d="M-8 0L33-22 72 0" fill="#889079" />
      </g>
      {heatmap && (
        <g>
          <ellipse cx="440" cy="286" rx="157" ry="105" fill={`url(#master-heat-${id})`} />
          <ellipse cx="827" cy="343" rx="118" ry="91" fill={`url(#master-heat-${id})`} />
          <text x="20" y="492" fill="#edbbb8" fontSize="10">
            LAST 7 DAYS / CONTROLLED HISTORICAL FIXTURES
          </text>
        </g>
      )}
      {[
        {
          name: 'CAM-01',
          left: 15,
          width: 545,
          detail: s.freeze ? 'SUSPICIOUS / POSSIBLE FREEZE' : 'ENTRY / TRACK TRK-017',
          bad: s.freeze,
        },
        {
          name: 'CAM-02',
          left: 571,
          width: 201,
          detail: s.associated ? 'TRK-044 / CANDIDATE' : 'PERIMETER / STANDBY',
          bad: false,
        },
        {
          name: 'CAM-03',
          left: 783,
          width: 163,
          detail: s.cameraOffline ? 'COVERAGE COMPROMISED' : 'DEGRADED BASELINE',
          bad: true,
        },
      ].map(cam => (
        <g key={cam.name}>
          <rect
            x={cam.left}
            y="61"
            width={cam.width}
            height="345"
            fill="#0B1F33"
            fillOpacity=".025"
            stroke={cam.bad ? '#F4B942' : '#9cb2a7'}
            strokeOpacity=".5"
            strokeDasharray="5 6"
          />
          <g {...selectable(cam.name)}>
            <rect
              x={cam.left + 8}
              y="69"
              width={cam.width - 16}
              height="42"
              rx="3"
              fill="#0B1F33"
              stroke={selected === cam.name ? '#FFFFFF' : '#647b76'}
            />
            <circle cx={cam.left + 21} cy="83" r="3" fill={cam.bad ? '#F4B942' : '#92bea4'} />
            <text x={cam.left + 32} y="87" fill="#FFFFFF" fontSize="12" fontWeight="bold">
              {cam.name}
            </text>
            <text
              x={cam.left + 18}
              y="103"
              fill={cam.bad ? '#F4B942' : '#b4c7c1'}
              fontSize={cam.width < 180 ? '7' : '9'}
            >
              {cam.detail}
            </text>
          </g>
        </g>
      ))}
      <g {...selectable('CAM-04')}>
        <rect x="18" y="428" width="190" height="34" rx="3" fill="#0B1F33" stroke="#647b76" />
        <circle cx="31" cy="441" r="3" fill="#92bea4" />
        <text x="43" y="446" fill="#FFFFFF" fontSize="11">
          CAM-04 / SERVICE ROAD
        </text>
        <text x="31" y="457" fill="#b4c7c1" fontSize="8">
          ONLINE / REPLAY TEST
        </text>
      </g>
      {routes && (
        <g>
          <path
            d="M145 490V352H868V256"
            fill="none"
            stroke="#D62828"
            strokeWidth="3"
            strokeDasharray="7 5"
          />
          <path
            d="M145 490V411H310L430 437H868V256"
            fill="none"
            stroke="#b2c5ad"
            strokeWidth="3"
            strokeDasharray="7 5"
          />
          <rect x="483" y="418" width="192" height="19" fill="#0B1F33" />
          <text x="493" y="431" fontSize="9" fill="#d0dfcf">
            B / LOWER MODELED EXPOSURE
          </text>
          <rect x="648" y="368" width="115" height="19" fill="#0B1F33" />
          <text x="657" y="381" fontSize="9" fill="#f0b3b3">
            A / DIRECT
          </text>
        </g>
      )}
      {s.tracking && (
        <path
          d="M192 335L252 310"
          fill="none"
          stroke="#d7ded7"
          strokeOpacity=".5"
          strokeWidth="1.5"
          strokeDasharray="3 5"
        />
      )}
      {s.time >= 130 && (
        <path
          d="M252 310L380 296"
          fill="none"
          stroke="#d7ded7"
          strokeOpacity=".5"
          strokeDasharray="3 5"
        />
      )}
      {s.time >= 145 && (
        <path
          d="M380 296L430 282"
          fill="none"
          stroke="#d7ded7"
          strokeOpacity=".5"
          strokeDasharray="3 5"
        />
      )}
      {s.time >= 175 && (
        <path
          d="M430 282L578 210"
          fill="none"
          stroke="#d7ded7"
          strokeOpacity=".5"
          strokeDasharray="3 5"
        />
      )}
      {s.associated && (
        <path
          d="M578 210L612 218"
          fill="none"
          stroke="#F4B942"
          strokeWidth="2"
          strokeDasharray="4 4"
        />
      )}
      {s.vehicle && (
        <g
          {...selectable('V-042')}
          transform={`translate(${Math.min(192, 100 + (s.time - 70) * 9.2)} 355)`}
        >
          <rect x="-34" y="-14" width="68" height="28" rx="5" fill="#e1e0d8" />
          <rect x="-13" y="-10" width="26" height="20" fill="#264451" />
          <rect x="-26" y="-18" width="10" height="4" fill="#111c20" />
          <rect x="17" y="-18" width="10" height="4" fill="#111c20" />
          <rect x="-26" y="14" width="10" height="4" fill="#111c20" />
          <rect x="17" y="14" width="10" height="4" fill="#111c20" />
          <rect x="-43" y="-23" width="86" height="46" fill="none" stroke="#d7e0d5" />
          <rect x="-70" y="27" width="140" height="21" fill="#0B1F33" />
          <text y="41" textAnchor="middle" fill="#FFFFFF" fontSize="9">
            {s.plate ? 'V-042 / MP09AB1234' : 'V-042 / VEHICLE 93%'}
          </text>
        </g>
      )}
      {s.animal && (
        <g
          {...selectable('A-008')}
          transform={`translate(${Math.min(535, 80 + (s.time - 63) * 14)} 240)`}
        >
          <ellipse rx="19" ry="9" fill="#bda67d" />
          <path
            d="M13-3L24-16 33-11M-12 5L-16 17M10 5L14 17"
            fill="none"
            stroke="#bda67d"
            strokeWidth="4"
          />
          <rect x="-30" y="-25" width="64" height="49" fill="none" stroke="#bcc9b6" />
          <text y="-31" textAnchor="middle" fontSize="9" fill="#d9e4d2">
            A-008 / ANIMAL 81% / EXCLUDED
          </text>
        </g>
      )}
      {s.person && s.position && (
        <g
          {...selectable(s.associated ? ENTITY_ID : 'TRK-017')}
          transform={`translate(${s.position.x} ${s.position.y})`}
        >
          <circle cy="-10" r="7" fill="#bda98d" />
          <path d="M-9 0H9L12 19H-12Z" fill="#9b9f81" />
          <path
            d={`M-6 19L${-9 - Math.sin(s.time * 3) * 3} 34M6 19L${9 + Math.sin(s.time * 3) * 3} 34`}
            stroke="#d1d0bd"
            strokeWidth="6"
          />
          <rect
            x="-23"
            y="-25"
            width="46"
            height="65"
            fill="none"
            stroke={s.alert ? '#D62828' : '#FFFFFF'}
            strokeWidth="2"
          />
          <rect x="-80" y="-48" width="160" height="20" fill="#0B1F33" />
          <text y="-34" textAnchor="middle" fill="#FFFFFF" fontSize="9">
            {s.associated
              ? `${ENTITY_ID} / TRK-044 / CANDIDATE`
              : s.tracking
                ? 'TRK-017 / PERSON'
                : 'PERSON / 94% / CANDIDATE'}
          </text>
        </g>
      )}
      {s.gap && (
        <g>
          <rect x="479" y="124" width="285" height="26" fill="#0B1F33" stroke="#F4B942" />
          <text x="621" y="142" textAnchor="middle" fill="#F4B942" fontSize="10">
            OBSERVATION GAP / NO INFERRED IDENTITY
          </text>
        </g>
      )}
      {s.cameraOffline && (
        <g>
          <rect x="783" y="116" width="163" height="290" fill="#0B1F33" opacity=".92" />
          <path
            d="M792 124L937 396M937 124L792 396"
            stroke="#F4B942"
            strokeOpacity=".1"
            strokeWidth="17"
          />
          <text x="865" y="234" textAnchor="middle" fill="#F4B942" fontSize="12">
            COVERAGE LOST
          </text>
          <text x="865" y="254" textAnchor="middle" fill="#bdc7cc" fontSize="8">
            LAST FRAME {masterClock(Math.min(210, s.capture))}
          </text>
          <text x="865" y="271" textAnchor="middle" fill="#bdc7cc" fontSize="8">
            NO FRESH OBSERVATIONS
          </text>
        </g>
      )}
      {s.freeze && (
        <g>
          <rect x="15" y="117" width="545" height="289" fill="#0B1F33" opacity=".7" />
          <rect x="123" y="213" width="329" height="67" fill="#0B1F33" stroke="#F4B942" />
          <text x="287" y="238" textAnchor="middle" fill="#F4B942" fontSize="15">
            FEED TRUST / SUSPICIOUS
          </text>
          <text x="287" y="259" textAnchor="middle" fill="#FFFFFF" fontSize="11">
            Controlled repeated-frame test / detections paused
          </text>
        </g>
      )}
      {!enhanced && (
        <rect width="960" height="510" fill="#000713" opacity=".52" pointerEvents="none" />
      )}
      {s.fog && (
        <g pointerEvents="none">
          <rect
            y="112"
            width="960"
            height="304"
            fill="#bbc5c2"
            opacity={enhanced ? '.08' : '.18'}
          />
          <path
            d="M0 169Q195 259 420 194T960 220"
            fill="none"
            stroke="#c8d0ca"
            strokeWidth="40"
            opacity=".12"
          />
        </g>
      )}
      <rect x="15" y="13" width="509" height="30" fill="#0B1F33" />
      <text x="26" y="32" fill="#FFFFFF" fontSize="12">
        REMOTE SSB BOP / FOREST & HILLY SECTOR / {masterClock(s.capture)} IST
      </text>
      <rect x="719" y="13" width="227" height="30" fill="#0B1F33" />
      <text x="731" y="32" fill={s.networkOffline ? '#F4B942' : '#c8dfcc'} fontSize="10">
        {s.networkOffline ? 'EDGE LOCAL / UPLINK OFFLINE' : 'REPLAY UPLINK / CONNECTED'}
      </text>
      {s.incident && (
        <g {...selectable(INCIDENT_ID)}>
          <rect x="365" y="464" width="310" height="29" fill="#0B1F33" stroke="#D62828" />
          <text x="520" y="483" textAnchor="middle" fill="#FFFFFF" fontSize="11">
            {INCIDENT_ID} / {ENTITY_ID} / ZONE A / REVIEW
          </text>
        </g>
      )}
      <text x="940" y="491" textAnchor="end" fill="#d1dbd4" fontSize="8">
        SYNTHETIC REPLAY / SCHEMATIC COORDINATES
      </text>
    </svg>
  )
}
