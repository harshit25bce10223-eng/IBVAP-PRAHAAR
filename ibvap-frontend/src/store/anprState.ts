// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — ANPR Store (anprState.ts)
// Follows the trackingState.ts pattern exactly.
// ─────────────────────────────────────────────────────────────────────────────
import { create } from 'zustand'
import { getANPRService } from '@/services/anpr'
import { DEFAULT_ANPR_FILTER } from '@/types/anpr'
import type {
  ANPRCameraFeed,
  ANPRCameraSummary,
  ANPRProviderHealth,
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

  providerHealth: ANPRProviderHealth | null
  providerHealthState: LoadState
  providerHealthError: string | null

  sightings: VehicleSighting[]
  sightingsState: LoadState
  sightingsError: string | null
  hasMore: boolean
  nextCursor: string | null
  moreState: LoadState
  moreError: string | null

  selectedSightingId: string | null
  selectedSighting: VehicleSighting | null
  selectedSightingState: LoadState

  vehicleHistory: VehicleHistory | null
  vehicleHistoryState: LoadState
  vehicleHistoryError: string | null

  cameraFeed: ANPRCameraFeed | null
  cameraFeedState: LoadState
  cameraFeedError: string | null

  cameraSummary: ANPRCameraSummary | null
  cameraSummaryState: LoadState

  searchResults: VehicleSearchResult[]
  searchState: LoadState
  searchQuery: string

  filter: ANPRFilter

  fetchSummary(): Promise<void>
  fetchProviderHealth(): Promise<void>
  fetchSightings(): Promise<void>
  fetchMoreSightings(): Promise<void>
  selectSighting(id: string | null): void
  fetchVehicleHistory(vehicleId: string): Promise<void>
  fetchCameraFeed(cameraId: string): Promise<void>
  fetchCameraSummary(cameraId: string): Promise<void>
  search(query: string): Promise<void>
  clearSearch(): void
  setFilter(patch: Partial<ANPRFilter>): void
  setServiceMode(mode: 'MOCK' | 'REAL'): void
  reset(): void
}

const summaryFlight = new Map<string, Promise<void>>()
const providerFlight = new Map<string, Promise<void>>()
const sightingsFlight = new Map<string, Promise<void>>()
const moreFlight = new Map<string, Promise<void>>()
const historyFlight = new Map<string, Promise<void>>()
const cameraFeedFlight = new Map<string, Promise<void>>()
const cameraSummaryFlight = new Map<string, Promise<void>>()
const searchFlight = new Map<string, Promise<void>>()

export const useANPRStore = create<ANPRStore>((set, get) => ({
  serviceMode: 'MOCK',

  summary: null,
  summaryState: 'idle',
  summaryError: null,

  providerHealth: null,
  providerHealthState: 'idle',
  providerHealthError: null,

  sightings: [],
  sightingsState: 'idle',
  sightingsError: null,
  hasMore: false,
  nextCursor: null,
  moreState: 'idle',
  moreError: null,

  selectedSightingId: null,
  selectedSighting: null,
  selectedSightingState: 'idle',

  vehicleHistory: null,
  vehicleHistoryState: 'idle',
  vehicleHistoryError: null,

  cameraFeed: null,
  cameraFeedState: 'idle',
  cameraFeedError: null,

  cameraSummary: null,
  cameraSummaryState: 'idle',

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

  fetchProviderHealth: () => {
    const key = 'provider'
    const existing = providerFlight.get(key)
    if (existing) return existing
    set({ providerHealthState: 'loading', providerHealthError: null })
    const svc = getANPRService(get().serviceMode)
    const task = (async () => {
      try {
        const providerHealth = await svc.getProviderHealth()
        set({ providerHealth, providerHealthState: 'ready' })
      } catch (err) {
        set({
          providerHealthState: 'error',
          providerHealthError:
            err instanceof Error ? err.message : 'ANPR provider status unavailable.',
        })
      } finally {
        providerFlight.delete(key)
      }
    })()
    providerFlight.set(key, task)
    return task
  },

  fetchSightings: () => {
    const key = JSON.stringify(get().filter)
    const existing = sightingsFlight.get(key)
    if (existing) return existing
    set({ sightingsState: 'loading', sightingsError: null, moreState: 'idle', moreError: null })
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

  /**
   * Cursor pagination: fetch the NEXT page with the stored cursor and APPEND
   * it. The previous implementation re-ran fetchSightings(), which reset the
   * cursor and REPLACED the list with page 1 — "Load more" never advanced.
   */
  fetchMoreSightings: () => {
    const { hasMore, nextCursor, moreState, sightingsState } = get()
    if (!hasMore || !nextCursor) return Promise.resolve()
    if (moreState === 'loading' || sightingsState === 'loading') return Promise.resolve()
    const key = nextCursor
    const existing = moreFlight.get(key)
    if (existing) return existing
    const cursor = nextCursor
    set({ moreState: 'loading', moreError: null })
    const svc = getANPRService(get().serviceMode)
    const task = (async () => {
      try {
        const page = await svc.listSightings({ ...get().filter, cursor })
        set(s => {
          const known = new Set(s.sightings.map(x => x.sightingId))
          const appended = page.sightings.filter(x => !known.has(x.sightingId))
          return {
            sightings: [...s.sightings, ...appended],
            hasMore: page.hasMore,
            nextCursor: page.nextCursor,
            moreState: 'ready',
          }
        })
      } catch (err) {
        set({
          moreState: 'error',
          moreError: err instanceof Error ? err.message : 'Could not load more sightings.',
        })
      } finally {
        moreFlight.delete(key)
      }
    })()
    moreFlight.set(key, task)
    return task
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
      .then(s => {
        if (get().selectedSightingId === id) {
          set({ selectedSighting: s, selectedSightingState: 'ready' })
        }
      })
      .catch(() => {
        if (get().selectedSightingId === id) {
          set({ selectedSightingState: 'error' })
        }
      })
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

  fetchCameraFeed: (cameraId) => {
    const existing = cameraFeedFlight.get(cameraId)
    if (existing) return existing
    set({ cameraFeedState: 'loading', cameraFeedError: null, cameraFeed: null })
    const svc = getANPRService(get().serviceMode)
    const task = (async () => {
      try {
        const cameraFeed = await svc.getCameraFeed(cameraId)
        set({ cameraFeed, cameraFeedState: 'ready' })
      } catch (err) {
        set({
          cameraFeedState: 'error',
          cameraFeedError: err instanceof Error ? err.message : 'Camera ANPR feed unavailable.',
        })
      } finally {
        cameraFeedFlight.delete(cameraId)
      }
    })()
    cameraFeedFlight.set(cameraId, task)
    return task
  },

  fetchCameraSummary: (cameraId) => {
    const existing = cameraSummaryFlight.get(cameraId)
    if (existing) return existing
    set({ cameraSummaryState: 'loading', cameraSummary: null })
    const svc = getANPRService(get().serviceMode)
    const task = (async () => {
      try {
        const cameraSummary = await svc.getCameraSummary(cameraId)
        set({ cameraSummary, cameraSummaryState: 'ready' })
      } catch {
        set({ cameraSummaryState: 'error' })
      } finally {
        cameraSummaryFlight.delete(cameraId)
      }
    })()
    cameraSummaryFlight.set(cameraId, task)
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

  clearSearch: () => set({ searchResults: [], searchState: 'idle', searchQuery: '' }),

  setFilter: (patch) => {
    set(s => ({ filter: { ...s.filter, ...patch, cursor: null } }))
  },

  setServiceMode: (mode) => {
    // §30 — switching provider mode must clear provider-specific data so REAL
    // mode never shows demo data (and vice versa).
    set({
      serviceMode: mode,
      summary: null,
      summaryState: 'idle',
      summaryError: null,
      providerHealth: null,
      providerHealthState: 'idle',
      providerHealthError: null,
      sightings: [],
      sightingsState: 'idle',
      sightingsError: null,
      hasMore: false,
      nextCursor: null,
      moreState: 'idle',
      moreError: null,
      selectedSightingId: null,
      selectedSighting: null,
      selectedSightingState: 'idle',
      cameraFeed: null,
      cameraFeedState: 'idle',
      cameraFeedError: null,
      cameraSummary: null,
      cameraSummaryState: 'idle',
      searchResults: [],
      searchState: 'idle',
      searchQuery: '',
    })
  },

  reset: () =>
    set({
      summary: null,
      summaryState: 'idle',
      summaryError: null,
      providerHealth: null,
      providerHealthState: 'idle',
      providerHealthError: null,
      sightings: [],
      sightingsState: 'idle',
      sightingsError: null,
      hasMore: false,
      nextCursor: null,
      moreState: 'idle',
      moreError: null,
      selectedSightingId: null,
      selectedSighting: null,
      selectedSightingState: 'idle',
      vehicleHistory: null,
      vehicleHistoryState: 'idle',
      vehicleHistoryError: null,
      cameraFeed: null,
      cameraFeedState: 'idle',
      cameraFeedError: null,
      cameraSummary: null,
      cameraSummaryState: 'idle',
      searchResults: [],
      searchState: 'idle',
      searchQuery: '',
      filter: { ...DEFAULT_ANPR_FILTER },
    }),
}))
