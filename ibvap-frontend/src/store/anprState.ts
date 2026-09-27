// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — ANPR Store (anprState.ts)
// Follows the trackingState.ts pattern exactly.
// ─────────────────────────────────────────────────────────────────────────────
import { create } from 'zustand'
import { getANPRService } from '@/services/anpr'
import { DEFAULT_ANPR_FILTER } from '@/types/anpr'
import type {
  ANPRSummary,
  ANPRFilter,
  VehicleSighting,
  VehicleHistory,
  VehicleSearchResult,
} from '@/types/anpr'

type LoadState = 'idle' | 'loading' | 'ready' | 'error'

interface ANPRStore {
  serviceMode: 'MOCK' | 'REAL'

  summary: ANPRSummary | null
  summaryState: LoadState
  summaryError: string | null

  sightings: VehicleSighting[]
  sightingsState: LoadState
  sightingsError: string | null
  hasMore: boolean
  nextCursor: string | null

  selectedSightingId: string | null
  selectedSighting: VehicleSighting | null
  selectedSightingState: LoadState

  vehicleHistory: VehicleHistory | null
  vehicleHistoryState: LoadState
  vehicleHistoryError: string | null

  searchResults: VehicleSearchResult[]
  searchState: LoadState
  searchQuery: string

  filter: ANPRFilter

  fetchSummary(): Promise<void>
  fetchSightings(): Promise<void>
  fetchMoreSightings(): Promise<void>
  selectSighting(id: string | null): void
  fetchVehicleHistory(vehicleId: string): Promise<void>
  search(query: string): Promise<void>
  setFilter(patch: Partial<ANPRFilter>): void
  setServiceMode(mode: 'MOCK' | 'REAL'): void
  reset(): void
}

const summaryFlight = new Map<string, Promise<void>>()
const sightingsFlight = new Map<string, Promise<void>>()
const historyFlight = new Map<string, Promise<void>>()
const searchFlight = new Map<string, Promise<void>>()

export const useANPRStore = create<ANPRStore>((set, get) => ({
  serviceMode: 'MOCK',

  summary: null,
  summaryState: 'idle',
  summaryError: null,

  sightings: [],
  sightingsState: 'idle',
  sightingsError: null,
  hasMore: false,
  nextCursor: null,

  selectedSightingId: null,
  selectedSighting: null,
  selectedSightingState: 'idle',

  vehicleHistory: null,
  vehicleHistoryState: 'idle',
  vehicleHistoryError: null,

  searchResults: [],
  searchState: 'idle',
  searchQuery: '',

  filter: { ...DEFAULT_ANPR_FILTER },

  fetchSummary: () => {
    const key = 'summary'
    const existing = summaryFlight.get(key)
    if (existing) return existing
    set({ summaryState: 'loading', summaryError: null })
    const svc = getANPRService(get().serviceMode)
    const task = (async () => {
      try {
        const summary = await svc.getSummary()
        set({ summary, summaryState: 'ready' })
      } catch (err) {
        set({
          summaryState: 'error',
          summaryError: err instanceof Error ? err.message : 'ANPR summary unavailable.',
        })
      } finally {
        summaryFlight.delete(key)
      }
    })()
    summaryFlight.set(key, task)
    return task
  },

  fetchSightings: () => {
    const key = JSON.stringify(get().filter)
    const existing = sightingsFlight.get(key)
    if (existing) return existing
    set({ sightingsState: 'loading', sightingsError: null })
    const svc = getANPRService(get().serviceMode)
    const task = (async () => {
      try {
        const page = await svc.listSightings(get().filter)
        set({ sightings: page.sightings, hasMore: page.hasMore, nextCursor: page.nextCursor, sightingsState: 'ready' })
      } catch (err) {
        set({
          sightingsState: 'error',
          sightingsError: err instanceof Error ? err.message : 'Vehicle sightings unavailable.',
        })
      } finally {
        sightingsFlight.delete(key)
      }
    })()
    sightingsFlight.set(key, task)
    return task
  },

  fetchMoreSightings: () => {
    const { hasMore, nextCursor } = get()
    if (!hasMore || !nextCursor) return Promise.resolve()
    return get().fetchSightings()
  },

  selectSighting: (id) => {
    if (id === null) {
      set({ selectedSightingId: null, selectedSighting: null, selectedSightingState: 'idle' })
      return
    }
    // Try cache first
    const cached = get().sightings.find(s => s.sightingId === id)
    if (cached) {
      set({ selectedSightingId: id, selectedSighting: cached, selectedSightingState: 'ready' })
      return
    }
    set({ selectedSightingId: id, selectedSighting: null, selectedSightingState: 'loading' })
    const svc = getANPRService(get().serviceMode)
    svc.getSighting(id)
      .then(s => set({ selectedSighting: s, selectedSightingState: 'ready' }))
      .catch(() => set({ selectedSightingState: 'error' }))
  },

  fetchVehicleHistory: (vehicleId) => {
    const existing = historyFlight.get(vehicleId)
    if (existing) return existing
    set({ vehicleHistoryState: 'loading', vehicleHistoryError: null, vehicleHistory: null })
    const svc = getANPRService(get().serviceMode)
    const task = (async () => {
      try {
        const history = await svc.getVehicleHistory(vehicleId)
        set({ vehicleHistory: history, vehicleHistoryState: 'ready' })
      } catch (err) {
        set({
          vehicleHistoryState: 'error',
          vehicleHistoryError: err instanceof Error ? err.message : 'Vehicle history unavailable.',
        })
      } finally {
        historyFlight.delete(vehicleId)
      }
    })()
    historyFlight.set(vehicleId, task)
    return task
  },

  search: (query) => {
    const key = query
    const existing = searchFlight.get(key)
    if (existing) return existing
    set({ searchState: 'loading', searchQuery: query, searchResults: [] })
    const svc = getANPRService(get().serviceMode)
    const task = (async () => {
      try {
        const results = await svc.searchPlate(query, get().filter)
        set({ searchResults: results, searchState: 'ready' })
      } catch {
        set({ searchState: 'error' })
      } finally {
        searchFlight.delete(key)
      }
    })()
    searchFlight.set(key, task)
    return task
  },

  setFilter: (patch) => {
    set(s => ({ filter: { ...s.filter, ...patch, cursor: null } }))
  },

  setServiceMode: (mode) => set({ serviceMode: mode }),

  reset: () =>
    set({
      summary: null,
      summaryState: 'idle',
      summaryError: null,
      sightings: [],
      sightingsState: 'idle',
      sightingsError: null,
      hasMore: false,
      nextCursor: null,
      selectedSightingId: null,
      selectedSighting: null,
      selectedSightingState: 'idle',
      vehicleHistory: null,
      vehicleHistoryState: 'idle',
      vehicleHistoryError: null,
      searchResults: [],
      searchState: 'idle',
      searchQuery: '',
      filter: { ...DEFAULT_ANPR_FILTER },
    }),
}))