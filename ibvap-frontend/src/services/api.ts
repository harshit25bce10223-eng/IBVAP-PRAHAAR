// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — API client
//
// Single axios instance for the Risk Engine backend. In dev, Vite proxies
// /api to the FastAPI service (see vite.config.ts). Swap VITE_API_TARGET to
// point at a deployed backend.
// ─────────────────────────────────────────────────────────────────────────────

import axios, { AxiosError } from 'axios'
import type { ApiError } from '@/types'

export interface ApiErrorBody {
  error?: { code?: string; message?: string; field?: string }
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 10_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/** Normalize backend error bodies into a readable typed error. */
export function asApiError(err: unknown): ApiError {
  const ax = err as AxiosError<ApiErrorBody>
  const body = ax?.response?.data
  const code = body?.error?.code ?? 'UNKNOWN'
  const message =
    body?.error?.message ?? ax?.message ?? 'An unexpected error occurred.'
  const field = body?.error?.field
  return {
    code,
    message,
    statusCode: ax?.response?.status ?? 0,
    details: field ? { field: [field] } : undefined,
  }
}

/** Query-string builder for simple `?camera_id=...&limit=...` params. */
export function qs(params: Record<string, string | number | boolean | undefined>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') query.set(key, String(value))
  }
  const str = query.toString()
  return str ? `?${str}` : ''
}