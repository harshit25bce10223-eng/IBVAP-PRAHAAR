// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — Dense Operational Camera Health Table
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useMemo } from 'react'
import {
  ArrowUpDown,
  Search,
  Filter,
  Eye,
  AlertTriangle,
  PauseCircle,
  Clock,
  ShieldAlert,
  ChevronRight,
} from 'lucide-react'
import type { CameraHealth, CameraHealthStatus } from '@/types/cameraHealth'
import type { CameraDetail } from '@/types/camera'
import type { HealthEntryState } from '@/store'
import { CameraHealthBadge } from './CameraHealthBadge'
import { formatAge, formatMetricValue } from './healthFormat'
import { toneForStatus, TONE } from './healthTone'

export interface CameraHealthTableProps {
  cameras: CameraDetail[]
  healthRecords: Record<string, CameraHealth>
  /**
   * Provider state per camera (idle/loading/ready/error/last-known). Used to
   * render honest UNAVAILABLE / last-known presentation instead of implying a
   * camera is fine when its telemetry never arrived (§35 stale/error honesty).
   */
  entryStates?: Record<string, { state: HealthEntryState; error: string | null }>
  selectedFilter: string | null
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string) => void
}

type SortField = 'SEVERITY' | 'ID' | 'LAST_SEEN' | 'FPS' | 'SHARPNESS'

const STATUS_SEVERITY_WEIGHT: Record<CameraHealthStatus, number> = {
  OFFLINE: 10,
  FROZEN: 9,
  STALE: 8,
  DEGRADED: 7,
  MAINTENANCE: 6,
  UNKNOWN: 5,
  ONLINE: 1,
}

export function CameraHealthTable({
  cameras,
  healthRecords,
  entryStates = {},
  selectedFilter,
  selectedCameraId,
  onSelectCamera,
}: CameraHealthTableProps) {
  const [nowMs] = useState(() => Date.now())
  const [searchQuery, setSearchQuery] = useState('')
  const [sectorFilter, setSectorFilter] = useState<string>('ALL')
  const [sortField, setSortField] = useState<SortField>('SEVERITY')
  const [sortAsc, setSortAsc] = useState(false)

  // Extract unique sectors
  const sectors = useMemo(() => {
    const set = new Set<string>()
    for (const c of cameras) {
      if (c.sectorProfile) set.add(c.sectorProfile)
    }
    return Array.from(set).sort()
  }, [cameras])

  // Filter & sort
  const rows = useMemo(() => {
    return cameras
      .filter(cam => {
        const health = healthRecords[cam.id]
        const status = health?.status ?? 'UNKNOWN'
        const coverage = health?.operationalImpact?.coverage ?? 'UNKNOWN'

        // 1. Operational Filter
        if (selectedFilter) {
          if (selectedFilter === 'COVERAGE_COMPROMISED') {
            if (coverage !== 'COMPROMISED') return false
          } else if (status !== selectedFilter) {
            return false
          }
        }

        // 2. Sector Filter
        if (sectorFilter !== 'ALL' && cam.sectorProfile !== sectorFilter) {
          return false
        }

        // 3. Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase()
          const matchId = cam.id.toLowerCase().includes(q)
          const matchLabel = cam.label.toLowerCase().includes(q)
          const matchSector = cam.sectorProfile?.toLowerCase().includes(q) ?? false
          const matchReason = health?.statusReason?.toLowerCase().includes(q) ?? false
          if (!matchId && !matchLabel && !matchSector && !matchReason) return false
        }

        return true
      })
      .sort((a, b) => {
        const hA = healthRecords[a.id]
        const hB = healthRecords[b.id]

        let cmp = 0
        if (sortField === 'SEVERITY') {
          const wA = STATUS_SEVERITY_WEIGHT[hA?.status ?? 'UNKNOWN'] ?? 0
          const wB = STATUS_SEVERITY_WEIGHT[hB?.status ?? 'UNKNOWN'] ?? 0
          cmp = wB - wA
        } else if (sortField === 'ID') {
          cmp = a.id.localeCompare(b.id)
        } else if (sortField === 'LAST_SEEN') {
          const tA = hA?.lastUpdated ? new Date(hA.lastUpdated).getTime() : 0
          const tB = hB?.lastUpdated ? new Date(hB.lastUpdated).getTime() : 0
          cmp = tA - tB
        } else if (sortField === 'FPS') {
          const fpsA = hA?.stream?.fps ?? -1
          const fpsB = hB?.stream?.fps ?? -1
          cmp = fpsA - fpsB
        } else if (sortField === 'SHARPNESS') {
          const shA = (hA?.image?.metrics.find(m => m.metric === 'sharpness')?.value as number) ?? -1
          const shB = (hB?.image?.metrics.find(m => m.metric === 'sharpness')?.value as number) ?? -1
          cmp = shA - shB
        }

        return sortAsc ? -cmp : cmp
      })
  }, [cameras, healthRecords, selectedFilter, sectorFilter, searchQuery, sortField, sortAsc])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc)
    } else {
      setSortField(field)
      setSortAsc(false)
    }
  }

  return (
    <div className="flex flex-col rounded-xl border border-white/[0.08] bg-surface overflow-hidden">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 border-b border-white/[0.06] bg-[#0A0D14]">
        <div className="flex items-center gap-2 flex-1 min-w-[240px]">
          <div className="relative flex-1 max-w-sm">
            <Search
              size={13}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              type="text"
              placeholder="Search camera ID, name, sector..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-md border border-white/10 bg-bg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400/50"
            />
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter size={12} className="text-slate-500" />
            <select
              value={sectorFilter}
              onChange={e => setSectorFilter(e.target.value)}
              className="rounded-md border border-white/10 bg-bg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-400/50"
            >
              <option value="ALL">All Sectors ({cameras.length})</option>
              {sectors.map(sec => (
                <option key={sec} value={sec}>
                  {sec}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span>Sort:</span>
          <button
            type="button"
            onClick={() => toggleSort('SEVERITY')}
            className={`px-2 py-1 rounded border text-[11px] font-mono flex items-center gap-1 ${
              sortField === 'SEVERITY'
                ? 'border-cyan-500/40 text-cyan-400 bg-cyan-950/20'
                : 'border-white/10 text-slate-400 hover:text-slate-200'
            }`}
          >
            Severity <ArrowUpDown size={10} />
          </button>
          <button
            type="button"
            onClick={() => toggleSort('LAST_SEEN')}
            className={`px-2 py-1 rounded border text-[11px] font-mono flex items-center gap-1 ${
              sortField === 'LAST_SEEN'
                ? 'border-cyan-500/40 text-cyan-400 bg-cyan-950/20'
                : 'border-white/10 text-slate-400 hover:text-slate-200'
            }`}
          >
            Last Seen <ArrowUpDown size={10} />
          </button>
          <button
            type="button"
            onClick={() => toggleSort('FPS')}
            className={`px-2 py-1 rounded border text-[11px] font-mono flex items-center gap-1 ${
              sortField === 'FPS'
                ? 'border-cyan-500/40 text-cyan-400 bg-cyan-950/20'
                : 'border-white/10 text-slate-400 hover:text-slate-200'
            }`}
          >
            FPS <ArrowUpDown size={10} />
          </button>
        </div>
      </div>

      {/* Dense Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[12px] border-collapse">
          <thead>
            <tr className="border-b border-white/[0.06] bg-[#0A0D14]/60 text-slate-400 font-mono text-[10px] uppercase tracking-wider">
              <th className="py-2.5 px-3">Camera</th>
              <th className="py-2.5 px-3">Sector & Profile</th>
              <th className="py-2.5 px-3">Health State</th>
              <th className="py-2.5 px-3">Last Telemetry</th>
              <th className="py-2.5 px-3">FPS</th>
              <th className="py-2.5 px-3">Sharpness</th>
              <th className="py-2.5 px-3">Viewpoint</th>
              <th className="py-2.5 px-3">Freeze</th>
              <th className="py-2.5 px-3">Coverage Impact</th>
              <th className="py-2.5 px-3">Issue Reason</th>
              <th className="py-2.5 px-2 text-right"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={11} className="py-8 text-center text-slate-500">
                  No cameras match the current filter selection.
                </td>
              </tr>
            ) : (
              rows.map(cam => {
                const health = healthRecords[cam.id]
                const rowEntry = entryStates[cam.id]
                const status = health?.status ?? 'UNKNOWN'
                const coverage = health?.operationalImpact?.coverage ?? 'UNKNOWN'
                const isSelected = selectedCameraId === cam.id

                const sharpnessMetric = health?.image?.metrics.find(m => m.metric === 'sharpness')
                const isViewpointShift = health?.viewpoint?.shiftDetected ?? false
                const isFrozen = health?.stream?.state === 'FROZEN'

                return (
                  <tr
                    key={cam.id}
                    onClick={() => onSelectCamera(cam.id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-cyan-950/30 hover:bg-cyan-950/40'
                        : 'hover:bg-white/[0.03]'
                    }`}
                  >
                    {/* Camera ID & Label */}
                    <td className="py-2.5 px-3">
                      <div className="font-mono font-semibold text-slate-100">{cam.id}</div>
                      <div className="text-[11px] text-slate-400 truncate max-w-[130px]">
                        {cam.label}
                      </div>
                    </td>

                    {/* Sector */}
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400 truncate max-w-[160px]">
                      {cam.sectorProfile ?? 'N/A'}
                    </td>

                    {/* State Badge — no data must not masquerade as a device state (§35) */}
                    <td className="py-2.5 px-3">
                      {health ? (
                        <CameraHealthBadge status={status} cameraId={cam.id} />
                      ) : rowEntry?.state === 'error' ? (
                        <span
                          title={rowEntry.error ?? 'Telemetry could not be retrieved'}
                          className="inline-flex items-center gap-1 font-mono text-[11px] font-semibold text-amber-400"
                        >
                          <AlertTriangle size={11} /> UNAVAILABLE
                        </span>
                      ) : (
                        <span className="font-mono text-[11px] text-slate-500">NO DATA</span>
                      )}
                    </td>

                    {/* Last Telemetry — a cached record is explicitly last-known */}
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      {health?.lastUpdated ? (
                        <>
                          {formatAge(health.lastUpdated, nowMs)}
                          {rowEntry?.state === 'last-known' && (
                            <span
                              title={rowEntry.error ?? 'Refresh failed — showing last known telemetry'}
                              className="ml-1 text-amber-400"
                            >
                              · last-known
                            </span>
                          )}
                        </>
                      ) : (
                        'N/A'
                      )}
                    </td>

                    {/* FPS */}
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-300">
                      {health?.stream?.fps !== null && health?.stream?.fps !== undefined
                        ? `${health.stream.fps} / ${health.stream.expectedFps ?? 25}`
                        : 'N/A'}
                    </td>

                    {/* Sharpness */}
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {sharpnessMetric?.value !== null && sharpnessMetric?.value !== undefined ? (
                        <span
                          className={
                            sharpnessMetric.status === 'GOOD'
                              ? 'text-prhaar-good'
                              : 'text-prhaar-degraded'
                          }
                        >
                          {formatMetricValue(sharpnessMetric.value, 'ratio')}
                        </span>
                      ) : (
                        <span className="text-slate-600">N/A</span>
                      )}
                    </td>

                    {/* Viewpoint — claim STABLE only when the API reported it */}
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {!health ? (
                        <span className="text-slate-600">—</span>
                      ) : isViewpointShift || health.viewpoint.status === 'SEVERE_SHIFT' ? (
                        <span className="inline-flex items-center gap-1 text-prhaar-degraded font-semibold">
                          <AlertTriangle size={11} /> SHIFT
                        </span>
                      ) : health.viewpoint.status === 'STABLE' ? (
                        <span className="text-slate-500">STABLE</span>
                      ) : (
                        <span
                          className="text-slate-600"
                          title={`Viewpoint ${health.viewpoint.status}`}
                        >
                          —
                        </span>
                      )}
                    </td>

                    {/* Freeze — LIVE only when the stream actually reports CONNECTED */}
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {!health ? (
                        <span className="text-slate-600">—</span>
                      ) : isFrozen ? (
                        <span className="inline-flex items-center gap-1 text-cyan-400 font-semibold">
                          <PauseCircle size={11} /> FROZEN
                        </span>
                      ) : health.stream.state === 'CONNECTED' ? (
                        <span className="text-slate-500">LIVE</span>
                      ) : (
                        <span
                          className="text-slate-600"
                          title={`Stream ${health.stream.state}`}
                        >
                          {health.stream.state}
                        </span>
                      )}
                    </td>

                    {/* Coverage Impact — NORMAL only when actually reported */}
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {!health ? (
                        <span className="text-slate-600">—</span>
                      ) : coverage === 'COMPROMISED' ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 font-semibold">
                          COMPROMISED
                        </span>
                      ) : coverage === 'DEGRADED' ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400">
                          DEGRADED
                        </span>
                      ) : coverage === 'NORMAL' ? (
                        <span className="text-prhaar-good">NORMAL</span>
                      ) : (
                        <span className="text-slate-600" title="Coverage impact not reported">
                          —
                        </span>
                      )}
                    </td>

                    {/* Reason — never imply nominal when telemetry never arrived */}
                    <td
                      className="py-2.5 px-3 text-[11px] text-slate-400 truncate max-w-[200px]"
                      title={!health && rowEntry?.error ? rowEntry.error : undefined}
                    >
                      {health ? (
                        health.statusReason ?? '—'
                      ) : rowEntry?.state === 'error' ? (
                        <span className="text-amber-400/90">Telemetry unavailable</span>
                      ) : (
                        <span className="text-slate-500">Awaiting telemetry…</span>
                      )}
                    </td>

                    {/* Arrow */}
                    <td className="py-2.5 px-2 text-right text-slate-600">
                      <ChevronRight size={14} />
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
