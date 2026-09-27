// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Tracking service contract
//
// Defines the exact interface for track retrieval, feed status, observation
// history, and structural summaries. Real and mock implementations share this
// identical contract so the frontend remains strictly model-agnostic.
// ─────────────────────────────────────────────────────────────────────────────

import type {
  Track,
  TrackingFeed,
  TrackObservation,
  TrackQuery,
  TrackResultPage,
  TrackSummary,
} from '@/types/tracking'

export interface ITrackingService {
  /**
   * Identifies whether the active provider is serving static demo fixtures
   * or communicating with a real backend inference/tracking pipeline (§74, §182).
   */
  readonly source: 'DEMO' | 'REAL'

  /**
   * Fetch a single track by its canonical track ID (TRK-*).
   * Rejects if the track does not exist.
   */
  getTrack(trackId: string): Promise<Track>

  /**
   * Paginated, filtered track list query (§48, §49, §251).
   */
  listTracks(query: TrackQuery): Promise<TrackResultPage>

  /**
   * Convenience lookup for all active/recent tracks on a specific camera.
   */
  listCameraTracks(cameraId: string): Promise<Track[]>

  /**
   * Detailed observation history for a track (ordered chronologically by observedAt).
   * Lazy-loaded on track selection/inspector opening (§194).
   */
  getTrackHistory(trackId: string): Promise<TrackObservation[]>

  /**
   * Camera-level tracking feed (tracks + provider availability).
   */
  getTrackFeed(cameraId: string): Promise<TrackingFeed>

  /**
   * Structural summary for a camera (counts only, no risk/threat scores §185).
   */
  getTrackSummary(cameraId: string): Promise<TrackSummary>

  /**
   * All active tracks across all cameras (for sector overview/dashboard §128).
   */
  getActiveTracks(): Promise<Track[]>
}
