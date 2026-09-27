// ─────────────────────────────────────────────────────────────────────────────
// Shell service entrypoint — used by the shell store.
//
// Local-dev implementation backed by MockShellService (प्रहार prototype state).
// Swap the singleton for a RealShellService without touching callers.
// ─────────────────────────────────────────────────────────────────────────────

import { MockShellService } from './MockShellService'

export const shellService = new MockShellService()