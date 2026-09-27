import { clsx } from 'clsx'
import type { CameraHealthStatus } from '@/types/cameraHealth'
import { TONE, toneForStatus } from './healthTone'

/**
 * Status dot — visual reinforcement ONLY. Always paired with adjacent status
 * text (or an aria-label when used standalone in dense markers).
 */
export function CameraHealthDot({
  status,
  cameraId,
  label,
  className,
}: {
  status: CameraHealthStatus
  /** Camera id for the screen-reader label, e.g. 'CAM-12'. */
  cameraId?: string
  /** Extra context, e.g. 'marker'. Falls back to 'status'. */
  label?: string
  className?: string
}) {
  const tone = TONE[toneForStatus(status)]
  return (
    <span
      role="img"
      aria-label={cameraId ? `Camera ${cameraId} status: ${status.toLowerCase()}` : `Status: ${status.toLowerCase()}${label ? ` (${label})` : ''}`}
      className={clsx('inline-block h-1.5 w-1.5 rounded-full', tone.dot, className)}
    />
  )
}
