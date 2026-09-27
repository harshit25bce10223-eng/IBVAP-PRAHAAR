// ─────────────────────────────────────────────────────────────────────────────
// SubjectPanel — Human vs Animal (Field Intelligence & Resilience, left 65%).
//
// A restrained forest-surveillance scene (CCTV style, not sci-fi): two detected
// subjects show the operational result — ANIMAL → Non-Threat, HUMAN → Track
// Created. Followed by the reason context for wildlife-heavy terrain.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { FieldReasonContext, SubjectClassification } from '@/types'

interface Props {
  subjects: SubjectClassification[]
  reason: FieldReasonContext
  className?: string
}

export function SubjectPanel({ subjects, reason, className }: Props) {
  const animal = subjects.find(s => s.kind === 'ANIMAL')
  const human = subjects.find(s => s.kind === 'HUMAN')

  return (
    <div className={clsx('flex h-full min-h-0 flex-col rounded-md border border-ssb-border/70 bg-ssb-navy/60 p-3', className)}>
      <div className="flex items-start justify-between gap-2 flex-shrink-0">
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ssb-white">
            Human vs Animal Differentiation
          </h2>
          <p className="text-[9.5px] text-ssb-text-muted mt-0.5">
            Context-aware classification · {reason.title.toLowerCase()}
          </p>
        </div>
        <span className="flex-shrink-0 rounded border border-ssb-border/60 bg-ssb-navy-deep/60 px-1.5 py-0.5 text-[9px] font-mono text-ssb-text-muted">
          CAM-12 · FOREST ZONE
        </span>
      </div>

      {/* Forest surveillance scene */}
      <div className="mt-2 flex-1 min-h-0 rounded border border-ssb-border/60 overflow-hidden bg-ssb-navy-deep">
        <ForestScene animal={animal} human={human} />
      </div>

      {/* Subject results */}
      <div className="mt-2 grid grid-cols-2 gap-2 flex-shrink-0">
        {subjects.map(s => (
          <div
            key={s.kind}
            className={clsx(
              'rounded border px-2 py-1.5',
              s.kind === 'ANIMAL' ? 'border-ssb-green-bright/40' : 'border-ssb-amber-bright/40'
            )}
          >
            <div className="flex items-center justify-between">
              <span className={clsx('text-[10px] font-bold tracking-wider', s.outcomeTone === 'safe' ? 'text-ssb-green-bright' : 'text-ssb-amber-bright')}>
                {s.kind} · {s.confidence}%
              </span>
              <span className="text-[9px] font-mono text-ssb-text-muted">
                {s.outcome}
              </span>
            </div>
            <p className="mt-0.5 text-[9.5px] text-ssb-text-muted/80">{s.note}</p>
          </div>
        ))}
      </div>

      {/* Reason context */}
      <div className="mt-2 flex-shrink-0 rounded border border-ssb-border/60 bg-ssb-navy-deep/50 px-2 py-1.5">
        <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-ssb-text-muted/80">
          Why this matters
        </div>
        <p className="mt-0.5 text-[9.5px] leading-snug text-ssb-text-muted">{reason.problem}</p>
        <div className="mt-1 flex items-center gap-1.5">
          <span className="text-[8.5px] font-semibold uppercase tracking-wider text-ssb-green-bright">प्रहार</span>
          {reason.approachSteps.map((step, i) => (
            <span key={step} className="flex items-center gap-1.5 text-[9px] text-ssb-text">
              {i > 0 && <span className="text-ssb-text-muted/50">→</span>}
              {step}
            </span>
          ))}
        </div>
        <p className="mt-1 text-[8.5px] italic text-ssb-text-muted/60">{reason.disclaimer}</p>
      </div>
    </div>
  )
}

// ─── Forest scene (SVG, restrained CCTV aesthetic) ───────────────────────────

function ForestScene({ animal, human }: { animal?: SubjectClassification; human?: SubjectClassification }) {
  return (
    <svg viewBox="0 0 800 460" className="w-full h-full" preserveAspectRatio="xMidYMid slice" aria-label="Forest surveillance scene">
      <defs>
        <linearGradient id="fsSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#12273C" />
          <stop offset="100%" stopColor="#0B1F33" />
        </linearGradient>
        <linearGradient id="fsGround" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#0C2B2B" />
          <stop offset="100%" stopColor="#0A2420" />
        </linearGradient>
      </defs>

      <rect width="800" height="460" fill="url(#fsSky)" />

      {/* Distant hills */}
      <path d="M0,210 L120,150 L240,205 L360,140 L480,210 L600,160 L720,205 L800,150 L800,300 L0,300 Z" fill="#0D2A35" fillOpacity="0.7" />

      {/* Treeline silhouettes */}
      {Array.from({ length: 26 }).map((_, i) => (
        <path
          key={i}
          d={`M${i * 32 - 8},195 q8,-34 16,0 z`}
          fill="#0B2118"
          opacity={0.85}
        />
      ))}
      {Array.from({ length: 30 }).map((_, i) => (
        <path
          key={`b${i}`}
          d={`M${i * 28 - 10},225 q9,-42 18,0 z`}
          fill="#081A12"
          opacity={0.9}
        />
      ))}

      {/* Ground */}
      <rect y="238" width="800" height="222" fill="url(#fsGround)" />

      {/* Perimeter fence (mid-ground) */}
      <line x1="0" y1="300" x2="800" y2="300" stroke="#FFFFFF" strokeOpacity={0.18} strokeWidth={1} />
      {Array.from({ length: 18 }).map((_, i) => (
        <line key={`p${i}`} x1={60 + i * 42} y1={292} x2={60 + i * 42} y2={308} stroke="#FFFFFF" strokeOpacity={0.16} strokeWidth={1.2} />
      ))}

      {/* Ground vegetation */}
      <path d="M0,395 q40,-18 80,0 q40,-16 80,0 q40,-18 80,0 q40,-16 80,0 q40,-18 80,0 q40,-16 80,0 q40,-18 80,0 q40,-16 80,0 q40,-18 80,0 q40,-16 80,0 q40,-16 80,0 M0,422 q50,-14 100,0 q50,-12 100,0 q50,-14 100,0 q50,-12 100,0 q50,-14 100,0 q50,-12 100,0 q50,-14 100,0 q50,-12 100,0" fill="none" stroke="#0E3A28" strokeWidth={1.4} strokeOpacity={0.7} />

      {/* Detection box — ANIMAL */}
      {animal && (
        <g>
          <rect x={150} y={210} width={190} height={128} fill="none" stroke="#35B884" strokeWidth={1.6} strokeDasharray="5 3" />
          <rect x={150} y={210} width={18} height={4} fill="#35B884" transform="translate(0 -1)" />
          <AnimalSilhouette x={248} y={338} />
          <rect x={150} y={188} width={98} height={16} fill="#071527" stroke="#35B884" strokeWidth={1} />
          <text x={199} y={199} textAnchor="middle" fill="#35B884" fontSize="9" fontFamily="monospace" fontWeight="600" letterSpacing="0.5">
            ANIMAL · 96%
          </text>
        </g>
      )}

      {/* Detection box — HUMAN */}
      {human && (
        <g>
          <rect x={490} y={260} width={170} height={92} fill="none" stroke="#F8C35C" strokeWidth={1.6} strokeDasharray="5 3" />
          <HumanSilhouette x={578} y={352} />
          <rect x={490} y={238} width={88} height={16} fill="#071527" stroke="#F8C35C" strokeWidth={1} />
          <text x={534} y={249} textAnchor="middle" fill="#F8C35C" fontSize="9" fontFamily="monospace" fontWeight="600" letterSpacing="0.5">
            HUMAN · 94%
          </text>
        </g>
      )}

      {/* CCTV HUD */}
      <text x={10} y={64} fill="#FFFFFF" fillOpacity={0.55} fontSize="11" fontFamily="monospace" letterSpacing="1">
        CAM-12 · 22:48:52 · FRAME
      </text>
      <circle cx={24} cy={82} r={3} fill="#D62828" />
      <text x={34} y={85} fill="#FFFFFF" fillOpacity={0.6} fontSize="10" fontFamily="monospace">
        REC
      </text>
      <text x={790} y={64} textAnchor="end" fill="#FFFFFF" fillOpacity={0.5} fontSize="10" fontFamily="monospace">
        FOREST ZONE
      </text>
      <line x1={400} y1={0} x2={400} y2={460} stroke="#FFFFFF" strokeOpacity={0.05} strokeWidth={1} />
      <line x1={0} y1={230} x2={800} y2={230} stroke="#FFFFFF" strokeOpacity={0.05} strokeWidth={1} />
    </svg>
  )
}

function AnimalSilhouette({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`} fill="#1B3040">
      {/* hind leg */}
      <path d="M-16,0 L-15,-17 L-12,-17 L-12,0 Z" />
      <path d="M-7,0 L-6,-16 L-3,-16 L-4,0 Z" />
      {/* front legs */}
      <path d="M8,0 L8,-16 L11,-16 L11,0 Z" />
      <path d="M17,0 L16,-12 L19,-12 L19,0 Z" />
      {/* body */}
      <ellipse cx="1" cy="-24" rx="17" ry="8" />
      {/* hind quarter + neck + head */}
      <path d="M-16,-26 q-6,-8 -18,-10 l0,-2 q4,-3 10,-2 q12,4 14,12 z" />
      <path d="M2,-31 q6,-10 16,-12 q-8,2 -10,10 q-2,4 -4,4 z" />
    </g>
  )
}

function HumanSilhouette({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`} fill="#1B3040">
      <circle cx="0" cy="-38" r="5.5" />
      <path d="M-8,-31 L8,-31 L9,-8 L-9,-8 Z" />
    </g>
  )
}