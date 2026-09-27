// ─────────────────────────────────────────────────────────────────────────────
// useCorrelation — Service → Store → Component boundary (Component 4)
//
// Surfaces consume correlation state exclusively through these hooks. Each
// hook owns its request lifecycle (start → loading → success/error) and
// swallows post-unmount rejections. No fetch happens on every render.
// ─────────────────────────────────────────────────────────────────────────────

import { useCallback, useEffect } from 'react'
import { useCorrelationStore, relationsFor } from '@/store/correlationState'

/**
 * Event/Incident Log — query state, paged list lifecycle, expand/collapse.
 * One request per query key; filter/sort/page changes re-fetch.
 */
export function useEventLog() {
  const query = useCorrelationStore(s => s.query)
  const page = useCorrelationStore(s => s.page)
  const listState = useCorrelationStore(s => s.listState)
  const listError = useCorrelationStore(s => s.listError)
  const expandedIds = useCorrelationStore(s => s.expandedIds)
  const setQuery = useCorrelationStore(s => s.setQuery)
  const fetchList = useCorrelationStore(s => s.fetchList)
  const toggleExpanded = useCorrelationStore(s => s.toggleExpanded)
  const resetList = useCorrelationStore(s => s.resetList)

  useEffect(() => {
    let cancelled = false
    fetchList().catch(() => {
      if (cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [fetchList, query])

  const retry = useCallback(() => fetchList(), [fetchList])

  return { query, page, listState, listError, expandedIds, setQuery, retry, toggleExpanded, resetList }
}

/** Dashboard live Event Log — the six most recent groups (§59/§161). */
export function useRecentCorrelations(limit = 6) {
  const recent = useCorrelationStore(s => s.recent)
  const recentState = useCorrelationStore(s => s.recentState)
  const recentError = useCorrelationStore(s => s.recentError)
  const fetchRecent = useCorrelationStore(s => s.fetchRecent)

  useEffect(() => {
    let cancelled = false
    fetchRecent(limit).catch(() => {
      if (cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [fetchRecent, limit])

  const retry = useCallback(() => fetchRecent(limit), [fetchRecent, limit])

  return { recent, recentState, recentError, retry }
}

/**
 * Incident / Event detail — full group + lazy relationship inspection.
 * Links pass the correlationId, which is the canonical group key.
 */
export function useCorrelationDetail(correlationId: string | undefined) {
  const selectedId = useCorrelationStore(s => s.selectedId)
  const detailState = useCorrelationStore(s => s.detailState)
  const detailError = useCorrelationStore(s => s.detailError)
  const group = useCorrelationStore(s => (correlationId ? s.groups[correlationId] ?? null : null))
  const relationships = useCorrelationStore(s => (correlationId ? s.relationships[correlationId] : undefined))
  const relationshipState = useCorrelationStore(s => (correlationId ? s.relationshipStates[correlationId] : undefined))
  const fetchGroup = useCorrelationStore(s => s.fetchGroup)
  const fetchRelationships = useCorrelationStore(s => s.fetchRelationships)

  useEffect(() => {
    if (!correlationId) return
    let cancelled = false
    fetchGroup(correlationId).catch(() => {
      if (cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [correlationId, fetchGroup])

  const relationshipsForGroup = group ? relationsFor(group, relationships ? { [group.correlationId]: relationships } : {}, relationshipState) : []

  const reviewRelationships = useCallback(() => {
    if (correlationId) fetchRelationships(correlationId).catch(() => {})
  }, [correlationId, fetchRelationships])

  return {
    group,
    detailState,
    detailError,
    selectedId,
    relationships: relationshipsForGroup,
    relationshipState,
    reviewRelationships,
  }
}

/** Single Camera related-events context (§164). Lightweight group list only. */
export function useCameraCorrelation(cameraId: string) {
  const context = useCorrelationStore(s => s.cameraContext[cameraId])
  const fetchCameraContext = useCorrelationStore(s => s.fetchCameraContext)

  useEffect(() => {
    if (!cameraId) return
    let cancelled = false
    fetchCameraContext(cameraId).catch(() => {
      if (cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [cameraId, fetchCameraContext])

  const retry = useCallback(() => fetchCameraContext(cameraId, 4), [cameraId, fetchCameraContext])

  return {
    groups: context?.groups ?? [],
    state: context?.state ?? 'idle',
    error: context?.error ?? null,
    retry,
  }
}