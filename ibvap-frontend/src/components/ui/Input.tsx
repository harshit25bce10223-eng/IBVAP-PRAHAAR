import { clsx } from 'clsx'
import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, leftIcon, rightIcon, className, id, ...rest }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leftIcon && (
            <span className="absolute left-3 text-slate-500 pointer-events-none">
              {leftIcon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              'w-full rounded-md bg-[#0d1117] border text-sm text-slate-100 placeholder-slate-600',
              'py-2.5 outline-none transition-all duration-150',
              'focus:border-cyan-500/70 focus:ring-2 focus:ring-cyan-500/20',
              leftIcon  ? 'pl-9'  : 'pl-3',
              rightIcon ? 'pr-9'  : 'pr-3',
              error
                ? 'border-red-500/70 focus:border-red-500 focus:ring-red-500/20'
                : 'border-[#1e2d40] hover:border-[#2a3f58]',
              className
            )}
            {...rest}
          />
          {rightIcon && (
            <span className="absolute right-3 text-slate-500">
              {rightIcon}
            </span>
          )}
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      </div>
    )
  }
)
Input.displayName = 'Input'
