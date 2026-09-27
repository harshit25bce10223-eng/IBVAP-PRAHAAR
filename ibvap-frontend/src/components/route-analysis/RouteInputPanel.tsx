// ─────────────────────────────────────────────────────────────────────────────
// RouteInputPanel — Start/Destination inputs + Analyze action (USP 5).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { Search, MapPin, ChevronDown, RefreshCw, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import type { RouteLocation, OperationalContext, RouteTimeWindow } from '@/types'

interface Props {
  origin: RouteLocation | null
  destination: RouteLocation | null
  operationalContext: OperationalContext
  timeWindow: RouteTimeWindow
  phase: 'input' | 'analyzing' | 'results' | 'simulating'
  onOriginChange: (loc: RouteLocation) => void
  onDestinationChange: (loc: RouteLocation) => void
  onContextChange: (ctx: OperationalContext) => void
  onTimeWindowChange: (window: RouteTimeWindow) => void
  onAnalyze: () => void
  onSimulate: () => void
  onReset: () => void
  availableLocations: RouteLocation[]
}

const ORIGIN_OPTIONS = ['BOP-ALPHA', 'BOP-BRAVO', 'BOP-CHARLIE', 'FWD-BASE', 'LOG-HUB']
const DEST_OPTIONS = ['CHK-ALPHA', 'CHK-BRAVO', 'CHK-CHARLIE', 'CHK-DELTA', 'FWD-BASE']

function SelectInput({
  label,
  value,
  options,
  onChange,
  icon: Icon,
  placeholder,
  disabled,
  className,
}: {
  label: string
  value: RouteLocation | null
  options: RouteLocation[]
  onChange: (loc: RouteLocation) => void
  icon: React.ComponentType<any>
  placeholder: string
  disabled?: boolean
  className?: string
}) {
  return (
    <div className={clsx('flex-1 min-w-0', className)}>
      <label className="block text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mb-1">
        {label}
      </label>
      <div className="relative">
        <Icon className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ssb-text-muted/60" size={14} aria-hidden="true" />
        <select
          value={value?.id ?? ''}
          onChange={e => {
            const found = options.find(o => o.id === e.target.value)
            if (found) onChange(found)
          }}
          disabled={disabled}
          className={clsx(
            'w-full h-9 pl-8 pr-8 text-sm font-medium bg-ssb-navy/80 border border-ssb-border/70 rounded text-ssb-white',
            'focus:outline-none focus:ring-1 focus:ring-ssb-green-bright/50 focus:border-ssb-green-bright/50',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'appearance-none cursor-pointer'
          )}
        >
          <option value="" disabled>{placeholder}</option>
          {options.map(opt => (
            <option key={opt.id} value={opt.id}>{opt.label}</option>
          ))}
        </select>
        <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ssb-text-muted/60 pointer-events-none" size={12} />
      </div>
    </div>
  )
}

export function RouteInputPanel({
  origin,
  destination,
  operationalContext,
  timeWindow,
  phase,
  onOriginChange,
  onDestinationChange,
  onContextChange,
  onTimeWindowChange,
  onAnalyze,
  onSimulate,
  onReset,
  availableLocations,
}: Props) {
  const isAnalyzing = phase === 'analyzing'
  const hasResults = phase === 'results' || phase === 'simulating'

  const originOptions = availableLocations.filter(l => ORIGIN_OPTIONS.includes(l.id))
  const destOptions = availableLocations.filter(l => DEST_OPTIONS.includes(l.id))

  return (
    <div className="flex flex-col gap-3 rounded-md border border-ssb-border/70 bg-ssb-navy/60 px-4 py-3 flex-shrink-0">
      {/* Start / Destination / Context row */}
      <div className="flex items-end gap-3 flex-wrap">
        <SelectInput
          label="FROM"
          value={origin}
          options={originOptions}
          onChange={onOriginChange}
          icon={MapPin}
          placeholder="Select origin..."
          disabled={hasResults}
        />
        <span className="flex items-center text-ssb-text-muted/50 mx-1" aria-hidden="true">
          <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M12 5v14M19 12H5" strokeLinecap="round" />
          </svg>
        </span>
        <SelectInput
          label="TO"
          value={destination}
          options={destOptions}
          onChange={onDestinationChange}
          icon={MapPin}
          placeholder="Select destination..."
          disabled={hasResults}
        />

        {/* Operational Context */}
        <div className="flex-1 min-w-[160px] max-w-[200px]">
          <label className="block text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mb-1">
            OPERATIONAL CONTEXT
          </label>
          <div className="relative">
            <select
              value={operationalContext}
              onChange={e => onContextChange(e.target.value as OperationalContext)}
              disabled={hasResults}
              className={clsx(
                'w-full h-9 pl-3 pr-8 text-sm font-medium bg-ssb-navy/80 border border-ssb-border/70 rounded text-ssb-white',
                'focus:outline-none focus:ring-1 focus:ring-ssb-green-bright/50 focus:border-ssb-green-bright/50',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'appearance-none cursor-pointer'
              )}
            >
              {['Patrol', 'Movement', 'Logistics', 'Inspection', 'Other'].map(ctx => (
                <option key={ctx} value={ctx}>{ctx}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ssb-text-muted/60 pointer-events-none" size={12} />
          </div>
        </div>

        {/* Time Window */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mr-1">
            Window
          </span>
          {(['LIVE', '24H', '7D', '30D'] as RouteTimeWindow[]).map(w => (
            <button
              key={w}
              type="button"
              onClick={() => onTimeWindowChange(w)}
              disabled={!hasResults}
              aria-pressed={timeWindow === w}
              className={clsx(
                'rounded px-2 py-1 text-[10px] font-mono font-semibold transition-colors border cursor-pointer',
                'disabled:opacity-40 disabled:cursor-not-allowed',
                timeWindow === w
                  ? 'bg-ssb-amber/20 border-ssb-amber-bright/60 text-ssb-amber-bright'
                  : 'border-ssb-border/60 text-ssb-text-muted hover:text-ssb-white'
              )}
            >
              {w}
            </button>
          ))}
        </div>
      </div>

      {/* Action row */}
      <div className="flex items-center justify-between gap-3 pt-1 border-t border-ssb-border/40">
        <div className="flex items-center gap-3 flex-wrap">
          {/* Analyze / Simulate / Reset buttons */}
          {!hasResults ? (
            <button
              type="button"
              onClick={onAnalyze}
              disabled={!origin || !destination || isAnalyzing}
              className={clsx(
                'flex items-center gap-2 rounded px-4 py-2 text-sm font-semibold tracking-[0.08em] uppercase transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'bg-ssb-green border-ssb-green-bright/50 text-ssb-white hover:bg-ssb-green-bright/90',
                'focus:outline-none focus:ring-2 focus:ring-ssb-green-bright/40'
              )}
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="animate-spin" size={14} aria-hidden="true" />
                  ANALYZING...
                </>
              ) : (
                <>
                  <Search size={14} aria-hidden="true" />
                  ANALYZE ROUTES
                </>
              )}
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={onSimulate}
                disabled={phase === 'simulating'}
                className={clsx(
                  'flex items-center gap-2 rounded px-3 py-2 text-sm font-medium transition-colors',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  'bg-ssb-amber/20 border-ssb-amber-bright/50 text-ssb-amber-bright hover:bg-ssb-amber/30',
                  'focus:outline-none focus:ring-2 focus:ring-ssb-amber-bright/40'
                )}
              >
                <AlertCircle size={13} aria-hidden="true" />
                SIMULATE INCIDENT
              </button>
              <button
                type="button"
                onClick={onReset}
                className={clsx(
                  'flex items-center gap-2 rounded px-3 py-2 text-sm font-medium transition-colors',
                  'bg-ssb-navy/80 border-ssb-border/60 text-ssb-text-muted hover:text-ssb-white hover:border-ssb-text-muted/50',
                  'focus:outline-none focus:ring-2 focus:ring-ssb-text-muted/40'
                )}
              >
                <RefreshCw size={13} aria-hidden="true" />
                NEW ANALYSIS
              </button>
            </>
          )}
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {phase === 'results' && (
            <span className="flex items-center gap-1 rounded px-2 py-1 text-[10px] font-semibold bg-ssb-green/20 border-ssb-green-bright/50 text-ssb-green-bright">
              <CheckCircle size={10} aria-hidden="true" />
              ROUTE ANALYSIS COMPLETE
            </span>
          )}
          {phase === 'simulating' && (
            <span className="flex items-center gap-1 rounded px-2 py-1 text-[10px] font-semibold bg-ssb-amber/20 border-ssb-amber-bright/50 text-ssb-amber-bright">
              <Loader2 className="animate-spin" size={10} aria-hidden="true" />
              SIMULATING...
            </span>
          )}
        </div>
      </div>
    </div>
  )
}