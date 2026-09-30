import { Link } from 'react-router-dom'
import { useExperienceStore } from '@/store/experienceState'

export function ExperienceModeBar() {
  const { mode, setMode } = useExperienceStore()
  return <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-slate-700 bg-[#101d2d] px-4 py-2">
    <div className="flex items-center gap-3"><div className="flex rounded-lg border border-slate-600 p-0.5" role="group" aria-label="Portal experience mode">
      <button type="button" aria-pressed={mode === 'demo'} onClick={() => setMode('demo')} className={`rounded-md px-4 py-1.5 text-xs font-semibold ${mode === 'demo' ? 'bg-cyan-300 text-slate-950' : 'text-slate-300 hover:bg-slate-800'}`}>Demo</button>
      <button type="button" aria-pressed={mode === 'real'} onClick={() => setMode('real')} className={`rounded-md px-4 py-1.5 text-xs font-semibold ${mode === 'real' ? 'bg-slate-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>Real workspace</button>
    </div><p className="text-[11px] text-slate-400">{mode === 'demo' ? 'Guided simulation · fictional data · no live actions' : 'Original screens · existing data-source settings apply'}</p></div>
    <Link to="/demo" onClick={() => setMode('demo')} className="text-xs font-semibold text-cyan-300">Start here: understand PRAHAAR →</Link>
  </div>
}
