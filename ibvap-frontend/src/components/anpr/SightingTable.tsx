// SightingTable.tsx — Dense operational table
import { useState } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import { Badge } from '@/components/ui'
import { VehicleClassBadge } from './VehicleClassBadge'
import { Link } from 'react-router-dom'
import type { VehicleSighting } from '@/types/anpr'

interface SightingTableProps {
  sightings: VehicleSighting[]
  selectedId?: string | null
  onSelect?: (id: string) => void
}

type SortKey = 'observedAt' | 'confidence' | 'cameraId' | 'vehicleClass' | 'vehicleDirection'

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  } catch { return iso }
}

function confVariant(c: number | null): 'safe' | 'warning' | 'critical' | 'default' {
  if (c === null) return 'default'
  if (c >= 0.8) return 'safe'
  if (c >= 0.5) return 'warning'
  return 'critical'
}

export function SightingTable({ sightings, selectedId, onSelect }: SightingTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('observedAt')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const sorted = [...sightings].sort((a, b) => {
    let av: string | number = a[sortKey] ?? ''
    let bv: string | number = b[sortKey] ?? ''
    if (sortKey === 'confidence') {
      av = a.confidence ?? -1
      bv = b.confidence ?? -1
    }
    if (av < bv) return sortDir === 'asc' ? -1 : 1
    if (av > bv) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  const renderSort = (k: SortKey) => {
    if (k !== sortKey) return null
    return sortDir === 'asc' ? <ChevronUp className="h-3 w-3 inline" /> : <ChevronDown className="h-3 w-3 inline" />
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="min-w-full text-xs font-mono">
        <thead className="border-b border-border">
          <tr>
            <th
              className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500 cursor-pointer hover:text-slate-300 select-none whitespace-nowrap"
              onClick={() => toggleSort('observedAt')}
            >
              Time {renderSort('observedAt')}
            </th>
            <th className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500">Plate Read</th>
            <th
              className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500 cursor-pointer hover:text-slate-300 select-none whitespace-nowrap"
              onClick={() => toggleSort('confidence')}
            >
              Confidence {renderSort('confidence')}
            </th>
            <th
              className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500 cursor-pointer hover:text-slate-300 select-none whitespace-nowrap"
              onClick={() => toggleSort('vehicleClass')}
            >
              Vehicle {renderSort('vehicleClass')}
            </th>
            <th
              className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500 cursor-pointer hover:text-slate-300 select-none whitespace-nowrap"
              onClick={() => toggleSort('cameraId')}
            >
              Camera {renderSort('cameraId')}
            </th>
            <th className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500">Track</th>
            <th
              className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500 cursor-pointer hover:text-slate-300 select-none whitespace-nowrap"
              onClick={() => toggleSort('vehicleDirection')}
            >
              Direction {renderSort('vehicleDirection')}
            </th>
            <th className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500">Quality</th>
            <th className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500">Status</th>
            <th className="px-3 py-2 text-left text-[9px] font-mono uppercase tracking-wider text-slate-500">Evidence</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(s => (
            <tr
              key={s.sightingId}
              onClick={() => onSelect?.(s.sightingId)}
              className={
                'border-b border-border/50 cursor-pointer transition-colors ' +
                (selectedId === s.sightingId ? 'bg-cyan-500/10' : 'hover:bg-white/2')
              }
            >
              <td className="px-3 py-2 text-slate-400 whitespace-nowrap">{fmtTime(s.observedAt)}</td>
              <td className="px-3 py-2">
                {s.plateRead
                  ? <span className="text-ssb-green-bright">{s.plateRead.displayRead}</span>
                  : <span className="text-slate-600 italic">UNREADABLE</span>
                }
              </td>
              <td className="px-3 py-2">
                {s.confidence !== null
                  ? <Badge variant={confVariant(s.confidence)} size="sm">{Math.round(s.confidence * 100)}%</Badge>
                  : <span className="text-slate-600">—</span>
                }
              </td>
              <td className="px-3 py-2"><VehicleClassBadge vehicleClass={s.vehicleClass} /></td>
              <td className="px-3 py-2 text-slate-300">{s.cameraId}</td>
              <td className="px-3 py-2">
                {s.vehicleTrackId
                  ? <Link to={'/track/' + s.vehicleTrackId} className="text-cyan-400 hover:underline">{s.vehicleTrackId}</Link>
                  : <span className="text-slate-600">—</span>
                }
              </td>
              <td className="px-3 py-2 text-slate-400">{s.vehicleDirection}</td>
              <td className="px-3 py-2 text-slate-500">{s.plateRead?.quality?.replace(/_/g, ' ') ?? '—'}</td>
              <td className="px-3 py-2">
                {s.watchlistStatus === 'WATCHLIST_MATCH'
                  ? <Badge variant="critical" dot size="sm">WATCHLIST</Badge>
                  : <span className="text-slate-600">{s.watchlistStatus}</span>
                }
              </td>
              <td className="px-3 py-2">
                {s.evidenceRef
                  ? <Link to="/evidence" className="text-emerald-400 hover:underline">{s.evidenceRef}</Link>
                  : <span className="text-slate-600">—</span>
                }
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}