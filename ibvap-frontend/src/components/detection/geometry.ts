// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — detection overlay geometry (pure math)
//
// Normalized image-space boxes ([0,1], top-left origin) are mapped into the
// shared camera-feed viewBox so overlays stay pixel-aligned across resize,
// letterboxing and aspect-ratio changes. The feed itself always renders into
// the normalized viewBox (FEED_VIEWBOX); this module handles the two common
// container situations:
//
//   contain (letterbox/fit) — the whole frame is visible, bars added
//   cover   (crop/fullscreen) — the frame fills the container, edges cropped
//
// All functions are pure so geometry can be unit-tested (§83/§189) without a
// DOM. No 1080p/pixel assumptions are made; sizes are opaque units.
// ─────────────────────────────────────────────────────────────────────────────

import type { DetectionBBox } from '@/types/detection'
import { FEED_VIEWBOX } from '@/components/camera/feedViewport'

export interface Size {
  width: number
  height: number
}

export interface Box {
  x: number
  y: number
  width: number
  height: number
}

export interface FitResult {
  /** Scale factor applied to the source to match the container under the fit. */
  scale: number
  /** X offset (letterbox bars / crop origin) in container units. */
  offsetX: number
  /** Y offset (letterbox bars / crop origin) in container units. */
  offsetY: number
}

/**
 * "contain" (letterbox) fit: the entire source is visible, centered.
 * Returns the scale, the left offset and the top offset in container units.
 */
export function fitContain(container: Size, source: Size): FitResult {
  const scale = Math.min(container.width / source.width, container.height / source.height)
  const renderedWidth = source.width * scale
  const renderedHeight = source.height * scale
  return {
    scale,
    offsetX: (container.width - renderedWidth) / 2,
    offsetY: (container.height - renderedHeight) / 2,
  }
}

/**
 * "cover" (crop / fullscreen) fit: the source fills the container, cropping
 * the overflow is handled by the caller (offset marks the visible origin).
 */
export function fitCover(container: Size, source: Size): FitResult {
  const scale = Math.max(container.width / source.width, container.height / source.height)
  const renderedWidth = source.width * scale
  const renderedHeight = source.height * scale
  return {
    scale,
    offsetX: (container.width - renderedWidth) / 2,
    offsetY: (container.height - renderedHeight) / 2,
  }
}

/** Normalized box → viewBox pixel box (point-free, no viewport needed). */
export function bboxToVB(box: DetectionBBox | null): Box | null {
  if (!box) return null
  return {
    x: box.x * FEED_VIEWBOX.width,
    y: box.y * FEED_VIEWBOX.height,
    width: box.width * FEED_VIEWBOX.width,
    height: box.height * FEED_VIEWBOX.height,
  }
}

/**
 * Normalized box → container pixels under a letterbox/crop fit.
 * Keeps the box aligned to the frame even when the container is not 16:9.
 */
export function bboxToContainer(box: DetectionBBox | null, container: Size, fit: 'contain' | 'cover'): Box | null {
  if (!box) return null
  const source: Size = { width: FEED_VIEWBOX.width, height: FEED_VIEWBOX.height }
  const { scale, offsetX, offsetY } = fit === 'contain' ? fitContain(container, source) : fitCover(container, source)
  return {
    x: box.x * source.width * scale + offsetX,
    y: box.y * source.height * scale + offsetY,
    width: box.width * source.width * scale,
    height: box.height * source.height * scale,
  }
}