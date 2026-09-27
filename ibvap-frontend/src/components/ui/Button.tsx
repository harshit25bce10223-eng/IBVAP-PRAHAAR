import { clsx } from 'clsx'
import type { ButtonHTMLAttributes } from 'react'
import { Loader2 } from 'lucide-react'

type Variant = 'primary' | 'ghost' | 'danger' | 'outline' | 'success'
type Size    = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const variantStyles: Record<Variant, string> = {
  primary: 'bg-cyan-500 hover:bg-cyan-400 text-[#080a0f] font-semibold shadow-[0_0_12px_-2px_rgba(34,211,238,0.4)] hover:shadow-[0_0_16px_-2px_rgba(34,211,238,0.6)]',
  ghost:   'bg-transparent hover:bg-white/5 text-slate-300 hover:text-white border border-transparent hover:border-white/10',
  danger:  'bg-red-600/90 hover:bg-red-500 text-white shadow-[0_0_12px_-2px_rgba(239,68,68,0.4)]',
  outline: 'bg-transparent border border-[#1e2d40] hover:border-cyan-500/50 text-slate-300 hover:text-cyan-400',
  success: 'bg-emerald-600 hover:bg-emerald-500 text-white',
}

const sizeStyles: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-4 py-2   text-sm gap-2',
  lg: 'px-6 py-3   text-base gap-2.5',
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      disabled={disabled || isLoading}
      className={clsx(
        'inline-flex items-center justify-center rounded-md font-medium',
        'transition-all duration-150 outline-none',
        'focus-visible:ring-2 focus-visible:ring-cyan-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-[#080a0f]',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...rest}
    >
      {isLoading ? (
        <Loader2 size={size === 'sm' ? 14 : 16} className="animate-spin" />
      ) : leftIcon ? (
        leftIcon
      ) : null}
      {children}
      {!isLoading && rightIcon}
    </button>
  )
}
