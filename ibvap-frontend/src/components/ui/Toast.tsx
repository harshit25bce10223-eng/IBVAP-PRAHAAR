import { clsx } from 'clsx'
import { createPortal } from 'react-dom'
import { useUIStore } from '@/store'
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react'
import type { ToastSeverity } from '@/store'

const ICONS: Record<ToastSeverity, React.ReactNode> = {
  success: <CheckCircle2 size={16} className="text-emerald-400 flex-shrink-0" />,
  error:   <AlertCircle  size={16} className="text-red-400    flex-shrink-0" />,
  warning: <AlertTriangle size={16} className="text-amber-400  flex-shrink-0" />,
  info:    <Info          size={16} className="text-blue-400   flex-shrink-0" />,
}

const BORDER: Record<ToastSeverity, string> = {
  success: 'border-emerald-500/30',
  error:   'border-red-500/40',
  warning: 'border-amber-500/30',
  info:    'border-blue-500/30',
}

export function ToastContainer() {
  const { toasts, removeToast } = useUIStore()

  if (!toasts.length) return null

  return createPortal(
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80 max-w-full">
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={clsx(
            'flex items-start gap-3 rounded-lg border bg-[#141b24] px-4 py-3',
            'shadow-2xl animate-[fadeInRight_0.2s_ease-out]',
            BORDER[toast.severity]
          )}
        >
          {ICONS[toast.severity]}
          <p className="flex-1 text-sm text-slate-200 leading-snug">{toast.message}</p>
          <button
            onClick={() => removeToast(toast.id)}
            className="text-slate-600 hover:text-slate-300 transition-colors flex-shrink-0"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>,
    document.body
  )
}
