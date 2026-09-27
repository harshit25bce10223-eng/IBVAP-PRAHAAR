import { Badge } from '@/components/ui'
import type { CameraHealthStatus } from '@/types/cameraHealth'
import { TONE, toneForStatus } from './healthTone'
import { CameraHealthDot } from './CameraHealthDot'

/**
 * One reusable status presentation: dot + text, never color alone.
 * Consumed by wall tiles, mini panel, rail header and twin markers.
 */
export function CameraHealthBadge({
  status,
  cameraId,
}: {
  status: CameraHealthStatus
  cameraId?: string
}) {
  const tone = TONE[toneForStatus(status)]
  return (
    <Badge variant={tone.badge} dot={false}>
      <CameraHealthDot status={status} cameraId={cameraId} />
      <span>{status}</span>
    </Badge>
  )
}
