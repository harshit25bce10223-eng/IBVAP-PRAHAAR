import { useEffect, useState } from 'react'

const duration = 20

export function VirtualFenceDemo() {
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [showZones, setShowZones] = useState(true)
  const [scenario, setScenario] = useState<'crossing' | 'safe'>('crossing')
  const inside = scenario === 'crossing' && time >= 8 && time <= 16
  const dwell = inside ? Math.max(0, time - 8) : 0
  const breached = inside && dwell >= 3
  const x = 100 + time * 35
  const y = scenario === 'crossing' ? 250 : 385
  const color = breached ? '#fb7185' : inside ? '#fbbf24' : '#34d399'

  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => setTime(t => {
      const next = Math.min(duration, Math.round((t + 0.1) * 10) / 10)
      if (next >= duration) window.clearInterval(timer)
      return next
    }), 100)
    return () => window.clearInterval(timer)
  }, [playing])

  const events = scenario === 'crossing'
    ? [
        { at: 0, text: 'Sample target detected outside the fence.' },
        { at: 8, text: 'Target entered the restricted zone. Dwell timer started.' },
        { at: 11, text: 'Demo alert: 3-second dwell threshold exceeded.' },
        { at: 16.1, text: 'Target exited the zone. Active alert cleared.' },
      ]
    : [{ at: 0, text: 'Sample target follows the safe path outside the zone.' }]

  function reset() {
    setPlaying(false)
    setTime(0)
  }

  return (
    <main className="h-full overflow-y-auto bg-ssb-navy-deep p-4 md:p-6 text-slate-200">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-mono tracking-widest text-cyan-400">PARAKH / INTERACTIVE DEMO</p>
            <h1 className="mt-2 text-2xl font-semibold">Virtual Fence Playground</h1>
            <p className="mt-2 text-sm text-slate-400">Explore how zone entry and dwell time trigger an intrusion alert.</p>
          </div>
          <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs text-amber-300">SIMULATED DATA · DEMO ONLY</span>
        </header>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
          <section className="overflow-hidden rounded-xl border border-slate-700 bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-700 px-4 py-3 text-xs">
              <span className="font-mono text-slate-400">SAMPLE PERIMETER · TOP VIEW</span>
              <span style={{ color }}>{time >= duration ? 'COMPLETED' : playing ? 'PLAYING' : 'PAUSED'}</span>
            </div>
            <svg viewBox="0 0 900 450" className="w-full" role="img" aria-label={`Simulated target at ${time.toFixed(1)} seconds. ${breached ? 'Intrusion alert' : inside ? 'Inside fence' : 'Outside fence'}`}>
              <defs>
                <pattern id="demo-grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M 30 0 L 0 0 0 30" fill="none" stroke="#233247" strokeWidth="1" /></pattern>
              </defs>
              <rect width="900" height="450" fill="#0b1423" />
              <rect width="900" height="450" fill="url(#demo-grid)" />
              <path d="M0 355H900" stroke="#334155" strokeWidth="45" />
              <path d="M0 355H900" stroke="#64748b" strokeWidth="2" strokeDasharray="16 16" />
              <text x="30" y="335" fill="#94a3b8" fontSize="12">PERIMETER ACCESS ROAD</text>
              {showZones && <g>
                <rect x="380" y="100" width="280" height="210" rx="4" fill={breached ? '#fb71851a' : '#fbbf2412'} stroke={inside ? color : '#fbbf24'} strokeWidth="2" strokeDasharray="8 5" />
                <text x="400" y="130" fill="#fbbf24" fontSize="13">RESTRICTED ZONE</text>
                <text x="400" y="150" fill="#94a3b8" fontSize="11">Dwell threshold: 3 seconds</text>
              </g>}
              <path d={`M100 ${y}H800`} stroke="#64748b" strokeWidth="2" strokeDasharray="5 8" />
              <path d={`M100 ${y}H${x}`} stroke={color} strokeWidth="2" />
              <circle cx={x} cy={y} r="20" fill={color} opacity="0.12" />
              <circle cx={x} cy={y} r="8" fill={color} />
              <rect x={x - 15} y={y - 20} width="30" height="40" fill="none" stroke={color} />
              <text x={x} y={y - 30} textAnchor="middle" fill={color} fontSize="12">DEMO TARGET</text>
              <text x="30" y="425" fill="#64748b" fontSize="12">Illustrated simulation · No live camera connection</text>
            </svg>
            <div className="space-y-3 border-t border-slate-700 p-4">
              <label className="flex items-center gap-3 text-xs text-slate-400">
                <span>Timeline</span>
                <input aria-label="Demo timeline in seconds" type="range" min="0" max={duration} step="0.1" value={time} onChange={e => { setPlaying(false); setTime(Number(e.target.value)) }} className="min-w-0 flex-1 accent-cyan-400" />
                <span className="w-20 font-mono">{time.toFixed(1)} / 20s</span>
              </label>
              <div className="flex flex-wrap items-center gap-3">
                <button onClick={() => { if (time >= duration) { setTime(0); setPlaying(false) } else setPlaying(!playing) }} className="rounded-md bg-cyan-400 px-5 py-2 text-sm font-semibold text-slate-950">{time >= duration ? 'Restart' : playing ? 'Pause' : 'Play demo'}</button>
                <button onClick={reset} className="rounded-md border border-slate-600 px-4 py-2 text-sm hover:bg-slate-800">Reset</button>
                <label className="ml-auto flex items-center gap-2 text-sm"><input type="checkbox" checked={showZones} onChange={e => setShowZones(e.target.checked)} className="accent-cyan-400" />Show fence</label>
              </div>
            </div>
          </section>

          <aside className="space-y-4">
            <section className="rounded-xl border border-slate-700 bg-slate-900 p-4">
              <label htmlFor="fence-scenario" className="text-sm font-semibold">Choose a scenario</label>
              <select id="fence-scenario" value={scenario} onChange={e => { reset(); setScenario(e.target.value as 'crossing' | 'safe') }} className="mt-3 w-full rounded-md border border-slate-600 bg-slate-950 p-2 text-sm">
                <option value="crossing">Restricted zone crossing</option>
                <option value="safe">Safe passage</option>
              </select>
              <p className="mt-3 text-xs leading-relaxed text-slate-400">Press Play or scrub the timeline. An alert appears after the target spends 3 seconds inside the fence.</p>
            </section>
            <section className="rounded-xl border border-slate-700 bg-slate-900 p-4">
              <h2 className="text-xs font-mono uppercase text-slate-400">Demo status</h2>
              <p className="mt-3 text-lg font-semibold" style={{ color }} role="status">{breached ? 'Intrusion alert' : inside ? 'Zone entry detected' : 'Outside restricted zone'}</p>
              <p className="mt-2 text-sm text-slate-400">Dwell time: <span className="font-mono text-white">{dwell.toFixed(1)}s / 3s</span></p>
              <p className="mt-3 text-xs text-slate-500">Simulated alerts stay in this demo.</p>
            </section>
            <section className="rounded-xl border border-slate-700 bg-slate-900 p-4">
              <h2 className="text-sm font-semibold">Demo event timeline</h2>
              <ol className="mt-4 space-y-4">
                {events.filter(event => time >= event.at).map(event => <li key={event.at} className="border-l-2 border-cyan-400/40 pl-3 text-xs leading-relaxed text-slate-300"><span className="block font-mono text-cyan-400">{event.at.toFixed(1)}s</span>{event.text}</li>)}
              </ol>
            </section>
          </aside>
        </div>
      </div>
    </main>
  )
}
