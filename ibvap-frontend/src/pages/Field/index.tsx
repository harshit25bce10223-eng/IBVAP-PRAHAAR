// ─────────────────────────────────────────────────────────────────────────────
// FieldIntelligence — SAKSHAM · FIELD INTELLIGENCE & RESILIENCE (SIH screenshot 6)
//
// Human/animal differentiation (left 65%) + offline-first resilience (right
// 35%). Communicates: "प्रहार is designed for difficult border environments."
// ─────────────────────────────────────────────────────────────────────────────

import { useFieldResilience } from '@/hooks'
import { SubjectPanel, ResiliencePanel, FieldSkeleton } from '@/components/field'

export function FieldIntelligence() {
  const { data, loadState, refetch } = useFieldResilience()

  if (loadState === 'error' && !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <button
          onClick={() => refetch().catch(() => {})}
          className="text-xs text-ssb-amber-bright underline underline-offset-2"
        >
          Failed to load field intelligence — try again
        </button>
      </div>
    )
  }

  if (!data) {
    return <FieldSkeleton />
  }

  return (
    <div className="h-full flex flex-col gap-3 overflow-y-auto p-4">
      {/* Page identity */}
      <header className="flex items-end justify-between flex-shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <h1 className="text-lg font-semibold tracking-[0.12em] text-ssb-white uppercase">
              SAKSHAM · Field Intelligence &amp; Resilience
            </h1>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#2FD5E0]/10 text-[#2FD5E0] border border-[#2FD5E0]/20 tracking-widest">
              सक्षम
            </span>
          </div>
          <p className="text-[11px] text-ssb-text-muted mt-0.5 tracking-wide">
            Context-Aware Detection · Offline-First Surveillance · Self-Aware Platform
          </p>
        </div>
        <span className="text-[9px] font-mono tracking-[0.2em] text-ssb-text-muted/60 uppercase">
          SSB Field Operations · Border Environments
        </span>
      </header>

      {/* Left 65% Human/Animal · Right 35% Resilence */}
      <div className="flex-1 min-h-0 grid grid-cols-[minmax(0,1.9fr)_minmax(360px,560px)] gap-3">
        <SubjectPanel subjects={data.subjects} reason={data.reason} />
        <ResiliencePanel data={data} />
      </div>
    </div>
  )
}