// VehicleClassBadge.tsx — Vehicle class with icon
import { Car, Truck, Bus, Bike, Tractor } from 'lucide-react'
import { clsx } from 'clsx'
import type { VehicleClass } from '@/types/anpr'

interface VehicleClassBadgeProps {
  vehicleClass: VehicleClass
  className?: string
}

type IconAndLabel = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  icon: React.ComponentType<any>
  label: string
}

const CLASS_MAP: Record<VehicleClass, IconAndLabel> = {
  PERSONAL_CAR:  { icon: Car, label: 'Car' },
  SUV:           { icon: Car, label: 'SUV' },
  TRUCK:         { icon: Truck, label: 'Truck' },
  BUS:           { icon: Bus, label: 'Bus' },
  VAN:           { icon: Car, label: 'Van' },
  MOTORCYCLE:    { icon: Bike, label: 'Motorcycle' },
  SCOOTER:       { icon: Bike, label: 'Scooter' },
  TRACTOR:       { icon: Tractor, label: 'Tractor' },
  THREE_WHEELER: { icon: Car, label: '3-Wheeler' },
  UTILITY:       { icon: Truck, label: 'Utility' },
  OTHER:         { icon: Car, label: 'Other' },
  UNKNOWN:       { icon: Car, label: 'Unknown' },
}

import type { ReactNode } from 'react'

export function VehicleClassBadge({ vehicleClass, className }: VehicleClassBadgeProps): ReactNode {
  const { icon: Icon, label } = CLASS_MAP[vehicleClass] ?? CLASS_MAP.UNKNOWN
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 text-xs font-mono text-slate-300',
      className
    )}>
      <Icon className="h-3.5 w-3.5 text-cyan-400" />
      {label}
    </span>
  )
}