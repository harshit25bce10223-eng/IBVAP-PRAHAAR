import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { DemoScene } from '@/components/demo/DemoScene'
import { getChapters, chapterForPath, defaultScenario, scenarios, DEMO_DURATION, DEMO_PLATE, demoClock, scenarioAt, type ScenarioId } from '@/components/demo/scenario'
import { useExperienceStore } from '@/store/experienceState'

export function GuidedDemo() {
  const [params, setParams] = useSearchParams()
  const sceneRef = useRef<HTMLDivElement>(null)
  const location = useLocation()
  const caseId: ScenarioId = scenarios.find(s => s.id === params.get('case'))?.id ?? defaultScenario(location.pathname)
  const selectedCase = scenarios.find(s => s.id === caseId)!
  const chapters = useMemo(() => getChapters(caseId), [caseId])
  const setMode = useExperienceStore(s => s.setMode)
  const requested = chapters.find(c => c.id === params.get('chapter')) ?? chapters.find(c => c.id === chapterForPath(location.pathname).id) ?? chapters[0]
  const [time, setTime] = useState<number>(requested?.at ?? 0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const state = scenarioAt(time, caseId)
  const chapterIndex = chapters.findIndex(c => c.id === state.chapter.id)

  useEffect(() => { setTime(requested?.at ?? 0); setPlaying(false) }, [requested])
  useEffect(() => {
    if (!playing || time >= DEMO_DURATION) return
    const timer = window.setTimeout(() => setTime(t => Math.min(DEMO_DURATION, Math.round((t + 0.1) * 10) / 10)), 100 / speed)
    return () => window.clearTimeout(timer)
  }, [playing, time, speed])

  function jump(index: number) {
    const chapter = chapters[Math.max(0, Math.min(chapters.length - 1, index))]
    setParams({ case: caseId, chapter: chapter.id }, { replace: true })
    setTime(chapter.at)
    setPlaying(false)
    sceneRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const record = { simulation: true, disclaimer: 'Illustrated, scripted demonstration. Not real surveillance or production evidence.', scenario: caseId, subject: selectedCase.subject, plate: caseId === 'vehicle' ? DEMO_PLATE : null, scenarioDate: '2026-09-30', timezone: 'Asia/Kolkata', playbackSeconds: time, events: state.events.map(e => ({ ...e, captureTime: demoClock(e.at) })) }

  function exportRecord() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'PRAHAAR-simulation-record.json'; anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <div className="h-full overflow-y-auto bg-[#080e17] p-4 md:p-6">
      <div className="mx-auto max-w-[1500px] space-y-3">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl"><p className="text-xs font-semibold tracking-widest text-cyan-300">PRAHAAR EXPLAINED · 4 SCENARIOS · 10 CAPABILITIES · DEMO ONLY</p><h1 className="mt-2 text-xl font-semibold text-white md:text-2xl">See what happened. Understand why it matters.</h1><p className="mt-2 text-sm leading-relaxed text-slate-300">People, animals, vehicles and camera faults need different decisions. Choose a situation and follow the explanation.</p></div>
        </header>

        <section aria-label="Choose a demo situation" className="grid grid-cols-2 gap-2 xl:grid-cols-4">
          {scenarios.map(s => <button key={s.id} onClick={() => {setParams({case:s.id,chapter:'detection'}, {replace:true});setPlaying(false);setTime(0)}} aria-pressed={caseId === s.id} className={`rounded-lg border p-3 text-left ${caseId === s.id ? 'border-cyan-400 bg-cyan-400/10' : 'border-slate-700 bg-slate-900/50 hover:border-slate-500'}`}><span className="block text-sm font-semibold text-slate-100">{s.title}</span><span className="mt-1 block text-[11px] leading-relaxed text-slate-400">{s.summary}</span></button>)}
        </section>

        <section className="sticky top-0 z-30 rounded-xl border border-slate-700 bg-slate-900/95 p-4 backdrop-blur" aria-label="Demo playback controls">
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={() => { if (time >= DEMO_DURATION) setTime(0); if (!playing || time >= DEMO_DURATION) sceneRef.current?.scrollIntoView({behavior:'smooth',block:'start'}); setPlaying(time >= DEMO_DURATION || !playing) }} className="rounded-lg bg-cyan-300 px-5 py-2.5 text-sm font-bold text-slate-950">{time >= DEMO_DURATION ? 'Replay story' : playing ? 'Pause story' : time === 0 ? '▶ Start guided demo' : '▶ Continue story'}</button>
            <button onClick={() => { setTime(0); setPlaying(false) }} className="rounded-lg border border-slate-600 px-3 py-2 text-sm">Reset</button>
            <label className="flex items-center gap-2 text-sm text-slate-300">Speed<select aria-label="Playback speed" value={speed} onChange={e => setSpeed(Number(e.target.value))} className="rounded bg-slate-800 p-2"><option value={1}>1×</option><option value={2}>2×</option></select></label>
            <span className="ml-auto font-mono text-sm text-cyan-200">Scenario time {demoClock(time)} IST</span>
          </div>
          <label className="mt-4 flex items-center gap-3 text-xs text-slate-400"><span>Replay timeline</span><input aria-label="Scenario timeline" type="range" min={0} max={DEMO_DURATION} step={1} value={time} onChange={e => { setTime(Number(e.target.value)); setPlaying(false) }} className="min-w-0 flex-1 accent-cyan-300" /><span className="w-16 text-right">{time}s / 120s</span></label>
        </section>

        <details className="rounded-lg border border-slate-700 bg-slate-900/50 p-3">
          <summary className="cursor-pointer text-sm text-cyan-200">Chapter {chapterIndex + 1} / 10 · {state.chapter.name} <span className="text-xs text-slate-400">— choose a chapter</span></summary>
          <nav aria-label="Demo chapters" className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-5">
          {chapters.map((c, i) => <button key={c.id} onClick={() => jump(i)} aria-current={c.id === state.chapter.id ? 'step' : undefined} className={`rounded-lg border p-3 text-left transition-colors ${c.id === state.chapter.id ? 'border-cyan-400 bg-cyan-400/10 text-cyan-100' : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-500'}`}><span className="block text-[10px] uppercase tracking-wider">{String(i + 1).padStart(2, '0')} · {c.module}</span><span className="mt-1 block text-xs font-semibold">{c.name}</span></button>)}
          </nav>
        </details>

        <div ref={sceneRef} className="grid scroll-mt-32 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_350px]">
          <div className="min-w-0 space-y-4">
            <DemoScene time={time} scenario={caseId} />
            <section className="rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-5" aria-live="polite">
              <p className="text-xs font-semibold text-cyan-300">CHAPTER {chapterIndex + 1} / 10 · {state.chapter.module}</p>
              <h2 className="mt-2 text-xl font-semibold text-white">{state.chapter.question}</h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-300">{state.chapter.explanation}</p>
              <p className="mt-3 rounded-lg bg-slate-950/60 p-3 text-sm text-cyan-100"><strong>What to watch: </strong>{state.chapter.action}</p>
              <div className="mt-4 flex flex-wrap items-center gap-3"><button disabled={chapterIndex === 0} onClick={() => jump(chapterIndex - 1)} className="rounded border border-slate-600 px-3 py-2 text-xs disabled:opacity-30">Previous chapter</button><button disabled={chapterIndex === 9} onClick={() => jump(chapterIndex + 1)} className="rounded border border-cyan-500/40 px-3 py-2 text-xs text-cyan-200 disabled:opacity-30">Next chapter →</button><Link to={state.chapter.route} onClick={() => setMode('real')} className="ml-auto text-xs text-cyan-300 underline underline-offset-4">Open original workspace →</Link></div>
              <p className="mt-3 text-[11px] text-slate-500">The original workspaces contain their own sample records. This guided story is a separate, synchronized simulation.</p>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
              <h2 className="text-sm font-semibold text-white">{caseId === 'health' ? 'Camera coverage and recovery' : 'One scenario across multiple cameras'}</h2><p className="mt-1 text-xs text-slate-400">Frames are illustrative. Observation timestamps appear only after the corresponding event.</p>
              <div className="mt-3 grid gap-3 md:grid-cols-3">{['CAM-07', 'CAM-08', 'CAM-12'].map(camera => <div key={camera}><DemoScene time={time} camera={camera} scenario={caseId} /><p className="mt-2 text-xs text-slate-400">{caseId === 'health' ? `${camera} · illustrated camera-health view` : state.sightings.find(s => s.camera === camera) ? `${camera} · ${demoClock(state.sightings.find(s => s.camera === camera)!.at)} IST` : `${camera} · no sighting yet`}</p></div>)}</div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
              <h2 className="text-sm font-semibold text-white">Observation map <span className="font-normal text-slate-500">· schematic, not real coordinates</span></h2>
              <div className="mt-4 flex items-center justify-between gap-2">{['CAM-07', 'CAM-08', 'CAM-12'].map((camera, i) => <div key={camera} className="flex flex-1 items-center gap-2"><div className={`min-w-0 flex-1 rounded-lg border p-3 text-center ${state.sightings.some(s => s.camera === camera) ? 'border-cyan-400/50 bg-cyan-400/10' : 'border-slate-700 bg-slate-950'}`}><p className="font-mono text-xs text-cyan-200">{camera}</p><p className="mt-1 text-[10px] text-slate-400">{['Entry checkpoint', 'Restricted perimeter', 'Exit checkpoint'][i]}</p></div>{i < 2 && <span className="text-slate-500" aria-label="Unobserved travel between cameras">┄→</span>}</div>)}</div>
              <p className="mt-3 text-xs text-slate-500">Dashed arrows show sighting order. They do not prove the route taken between cameras.</p>
            </section>
          </div>

          <aside className="space-y-4">
            <section className="rounded-xl border border-slate-700 bg-slate-900 p-4"><p className="text-xs uppercase tracking-wider text-slate-400">{caseId === 'vehicle' ? 'Number-plate reading / ANPR' : caseId === 'health' ? 'Camera reliability' : 'Object classification'}</p><p className="mt-3 rounded border-2 border-slate-300 bg-[#eee9d7] px-4 py-2 text-center font-mono text-xl font-bold text-slate-950">{caseId === 'vehicle' ? time >= 8 ? DEMO_PLATE : 'READ PENDING' : caseId === 'health' ? state.outage ? 'OFFLINE' : time >= 12 && time < 24 ? 'BLURRED' : 'CLEAR IMAGE' : time >= 3 ? caseId.toUpperCase() : 'DETECTION PENDING'}</p><p className="mt-3 text-xs leading-relaxed text-slate-400">{selectedCase.outcome}</p><dl className="mt-4 flex justify-between text-xs"><dt>{caseId === 'health' ? 'Camera-health events' : 'Recorded camera sightings'}</dt><dd className="font-bold text-cyan-300">{caseId === 'health' ? state.events.filter(e => e.kind === 'health').length : `${state.sightings.length} / 3`}</dd></dl></section>
            <section className={`rounded-xl border p-4 ${state.alert ? 'border-rose-400/40 bg-rose-400/10' : 'border-emerald-400/20 bg-emerald-400/5'}`}><p className="text-xs uppercase tracking-wider text-slate-400">Decision and reason</p><h2 className={`mt-2 text-lg font-semibold ${state.alert ? 'text-rose-300' : 'text-emerald-300'}`}>{caseId === 'health' ? state.outage ? 'Coverage gap · no fresh observations' : 'Monitor image quality and connection' : caseId === 'animal' && time >= 42 ? 'Animal excluded by this rule' : state.alert ? 'Restricted-zone dwell exceeded' : state.inside ? 'Inside zone · checking rule' : 'No fence alert yet'}</h2><p className="mt-2 text-xs leading-relaxed text-slate-300">{caseId === 'animal' ? 'This example zone monitors people and vehicles. Animal observations are recorded without an intrusion alert.' : caseId === 'health' ? 'A camera fault needs maintenance review. It does not establish that an intrusion happened.' : state.alert ? 'Entry at 14:32:39 + 3-second threshold = alert at 14:32:42. The alert remains in the record for review.' : 'An object detection alone does not establish a threat. The configured zone rule supplies the alert reason.'}</p>{state.inside && caseId !== 'animal' && <p className="mt-2 font-mono text-sm text-amber-200">Dwell: {(time - 39).toFixed(1)}s / 3s</p>}</section>
            {time >= 84 && <section className="rounded-xl border border-slate-700 bg-slate-900 p-4"><h2 className="text-sm font-semibold">Field report</h2><p className="mt-2 text-amber-200">{time < 87 ? 'Preparing observation…' : time < 92 ? 'Queued offline' : 'Synced · 14:33:32 IST'}</p><p className="mt-2 text-xs text-slate-400">Simulated operator note. No message sent to a real field team.</p></section>}
            {time >= 96 && <section className="rounded-xl border border-slate-700 bg-slate-900 p-4"><h2 className="text-sm font-semibold">Illustrative route comparison</h2><p className="mt-3 text-xs text-slate-400">Route A · shorter · crosses outage area</p><p className="mt-2 text-xs text-cyan-200">Route B · longer · avoids outage area</p><p className="mt-3 text-sm">{caseId === 'animal' ? 'No response route requested for this excluded animal event.' : time >= 101 ? 'Suggestion: Route B · needs operator approval' : 'Comparing route context…'}</p></section>}
            <section className="rounded-xl border border-slate-700 bg-slate-900 p-4"><h2 className="text-sm font-semibold text-white">What has happened so far?</h2><p className="mt-1 text-xs text-slate-400">Capture time · camera · explanation</p><ol className="mt-4 max-h-[420px] space-y-4 overflow-y-auto">{state.events.length === 0 && <li className="text-xs text-slate-400">Press Start guided demo. Events appear as the story progresses.</li>}{[...state.events].reverse().map(event => <li key={event.at} className={`border-l-2 pl-3 ${event.kind === 'alert' ? 'border-rose-400' : 'border-cyan-700'}`}><p className="font-mono text-[11px] text-cyan-300">{demoClock(event.at)} · {event.camera}</p><p className="mt-1 text-sm text-slate-100">{event.title}</p><p className="mt-1 text-xs leading-relaxed text-slate-400">{event.detail}</p></li>)}</ol></section>
            <button disabled={time < 113} onClick={exportRecord} className="w-full rounded-lg border border-cyan-400/40 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-200 disabled:cursor-not-allowed disabled:opacity-40">{time < 113 ? 'Demo export unlocks in chapter 10' : 'Download simulation record ↓'}</button>
            {time >= 113 && <details className="rounded-lg border border-slate-700 p-3"><summary className="cursor-pointer text-sm text-cyan-200">Preview simulation record</summary><pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words text-[11px] text-slate-400">{JSON.stringify(record, null, 2)}</pre></details>}
          </aside>
        </div>
        <section className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
          <h2 className="text-lg font-semibold text-white">Try a different camera situation</h2><p className="mt-1 text-sm text-slate-400">Independent scenario previews: each has its own observations and decision. Choose a card to replay it from the beginning.</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">{scenarios.map(s => <button key={s.id} onClick={() => {setParams({case:s.id,chapter:'detection'}, {replace:true});setTime(0);setPlaying(false)}} className="rounded-lg border border-slate-700 p-3 text-left hover:border-cyan-400"><DemoScene time={s.id === 'health' ? 16 : 42} scenario={s.id} /><span className="mt-3 block font-semibold text-cyan-200">{s.title} →</span><span className="mt-1 block text-xs text-slate-400">{s.outcome}</span></button>)}</div>
        </section>
        <section className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
          <h2 className="text-lg font-semibold text-white">Feature map: what can I try?</h2><p className="mt-1 text-sm text-slate-400">Every implemented module has a guided chapter. Unimplemented sidebar items remain marked SOON.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{chapters.map((c,i) => <button key={c.id} onClick={() => jump(i)} className="rounded-lg border border-slate-700 bg-slate-950/60 p-3 text-left hover:border-cyan-500"><span className="block text-sm font-semibold text-cyan-200">{c.module}</span><span className="mt-1 block text-xs text-slate-400">{c.question}</span><span className="mt-3 block text-xs text-slate-200">Watch chapter {i+1} →</span></button>)}</div>
        </section>
      </div>
    </div>
  )
}
