// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — Event Log deep links (URL ⇄ query)
//
// The Event Log's filter/sort/page state is shareable and reload-safe: it is
// serialized to the /events query string and rehydrated from it. Only values
// that differ from the defaults are written, so a default view keeps a clean
// URL. Nothing here computes correlation, risk or severity.
// ─────────────────────────────────────────────────────────────────────────────

import type { EventLogQuery } from '@/types/eventCorrelation'
import { CORRELATION_STATUSES, DEFAULT_CORRELATION_QUERY, CORRELATION_SOURCES } from '@/types/eventCorrelation'
import type { Connectivity } from '@/types/eventCorrelation'
import type { Severity } from '@/types/risk'

const TIME_RANGES: EventLogQuery['timeRange'][] = ['15m', '1h', 'today', 'all']
const SORTS: EventLogQuery['sort'][] = ['time', 'severity', 'signals', 'cameras', 'status']
const CONNECTIVITY_VALUES: Connectivity[] = ['LIVE', 'DELAYED', 'LAST_SYNCED', 'UNKNOWN']
const SEVERITY_VALUES: Severity[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

function oneOf<T extends string>(value: string | null, allowed: readonly T[]): T | undefined {
  return value !== null && (allowed as readonly string[]).includes(value) ? (value as T) : undefined
}

/** URL search params for the current query; defaults are omitted. */
export function queryToSearchParams(q: EventLogQuery): URLSearchParams {
  const p = new URLSearchParams()
  if (q.search.trim() !== '') p.set('search', q.search)
  if (q.correlation !== 'ALL') p.set('status', q.correlation)
  if (q.severity !== 'ALL') p.set('severity', q.severity)
  if (q.cameraId !== 'ALL') p.set('camera', q.cameraId)
  if (q.sectorId !== 'ALL') p.set('sector', q.sectorId)
  if (q.source !== 'ALL') p.set('source', q.source)
  if (q.connectivity !== 'ALL') p.set('connectivity', q.connectivity)
  if (q.timeRange !== 'all') p.set('range', q.timeRange)
  if (q.sort !== 'time') p.set('sort', q.sort)
  if (q.order !== 'desc') p.set('order', q.order)
  if (q.page > 1) p.set('page', String(q.page))
  if (q.pageSize !== DEFAULT_CORRELATION_QUERY.pageSize) p.set('pageSize', String(q.pageSize))
  return p
}

/** Query patch from a deep link; unrecognized/invalid values are ignored. */
export function queryFromSearchParams(params: URLSearchParams): Partial<EventLogQuery> {
  const patch: Partial<EventLogQuery> = {}
  const search = params.get('search')
  if (search !== null && search.trim() !== '') patch.search = search

  const status = oneOf(params.get('status'), CORRELATION_STATUSES)
  if (status) patch.correlation = status
  const severity = oneOf(params.get('severity'), SEVERITY_VALUES)
  if (severity) patch.severity = severity
  const camera = params.get('camera')
  if (camera) patch.cameraId = camera
  const sector = params.get('sector')
  if (sector) patch.sectorId = sector
  const source = oneOf(params.get('source'), CORRELATION_SOURCES)
  if (source) patch.source = source
  const connectivity = oneOf(params.get('connectivity'), CONNECTIVITY_VALUES)
  if (connectivity) patch.connectivity = connectivity
  const range = oneOf(params.get('range'), TIME_RANGES)
  if (range) patch.timeRange = range
  const sort = oneOf(params.get('sort'), SORTS)
  if (sort) patch.sort = sort
  const order = oneOf(params.get('order'), ['asc', 'desc'] as const)
  if (order) patch.order = order

  const page = Number(params.get('page'))
  if (Number.isInteger(page) && page >= 1) patch.page = page
  const pageSize = Number(params.get('pageSize'))
  if (Number.isInteger(pageSize) && pageSize >= 1 && pageSize <= 100) patch.pageSize = pageSize

  return patch
}
