import { useEffect, useRef, useState } from 'react'
import { MasterSector } from '../components/demo/MasterSector'
import {
  masterAt,
  masterSteps,
  masterClock,
  replayEvidencePayloads,
  searchMasterEvents,
} from '../components/demo/masterStory'
import { sha256 } from '../components/demo/challengeEngine'
import './masterDemo.css'
type Seal = { original: string; bytes: string; digest: string; computed: string }
export function MasterDemo() {
  const [time, T] = useState(0),
    [playing, P] = useState(false),
    [speed, S] = useState(1),
    [opening, O] = useState(true),
    [enhanced, E] = useState(true),
    [heatmap, H] = useState(false),
    [routes, R] = useState(false),
    [selected, I] = useState(''),
    [query, Q] = useState('X42'),
    [review, V] = useState('Pending review'),
    [role, U] = useState('Officer'),
    [audit, A] = useState<string[]>([]),
    [seals, B] = useState<Seal[]>([]),
    [delivered, D] = useState(0),
    [error, F] = useState(''),
    [faults, J] = useState({ network: false, camera: false, fog: false })
  const hashing = useRef(false),
    run = useRef(0),
    s = masterAt(time, faults),
    step = s.current,
    index = masterSteps.indexOf(step)
  const log = (message: string) =>
    A(a => [`${new Date().toLocaleTimeString()} · ${message}`, ...a].slice(0, 8))
  const seek = (n: number) => {
    if (n < 320) D(0)
    T(n)
    P(false)
    O(false)
    I('')
  }
  useEffect(() => {
    if (!playing || time >= 480) return
    const timer = setInterval(() => T(t => Math.min(480, t + speed)), 1000)
    return () => clearInterval(timer)
  }, [playing, speed, time])
  useEffect(() => {
    if (time < 340 || seals.length || hashing.current) return
    hashing.current = true
    const version = run.current
    Promise.all(
      replayEvidencePayloads(masterAt(340).events).map(async original => {
        const digest = await sha256(original)
        return { original, bytes: original, digest, computed: digest }
      })
    )
      .then(result => {
        if (version === run.current) {
          B(result)
          try {
            localStorage.setItem('prahaar-master-evidence', JSON.stringify(result))
          } catch {
            F('Storage failed; evidence remains in memory.')
          }
        }
      })
      .catch(() => F('Local SHA-256 unavailable.'))
      .finally(() => {
        hashing.current = false
      })
  }, [time, seals.length])
  useEffect(() => {
    if (time < 365 || s.networkOffline) return
    const timer = setInterval(() => D(n => Math.min(10, n + 1)), 500)
    return () => clearInterval(timer)
  }, [time, s.networkOffline])
  const tamper = async (changed: boolean) => {
    if (!seals[0]) return
    const bytes = changed
      ? seals[0].original.replace('PRAHAAR master incident', 'ALTERED incident')
      : seals[0].original
    const computed = await sha256(bytes)
    B(a => a.map((x, i) => (i === 0 ? { ...x, bytes, computed } : x)))
    log(changed ? 'Evidence altered for integrity test' : 'Original evidence restored')
  }
  const restart = () => {
    run.current++
    B([])
    D(0)
    T(60)
    S(4)
    P(true)
    J({ network: false, camera: false, fog: false })
    I('')
    log('Same incident replay restarted')
  }
  const records = s.events
    .filter(
      e =>
        e.id !== 'EVT-2292' &&
        ['vehicle', 'person', 'track', 'behavior', 'zone', 'plate', 'association'].includes(e.type)
    )
    .slice(0, 7)
  useEffect(() => {
    if (time < 320) return
    try {
      localStorage.setItem('prahaar-master-metadata', JSON.stringify(records))
    } catch {
      queueMicrotask(() => F('Metadata storage failed; records remain in memory.'))
    }
  }, [time, records])
  const related = s.events.filter(
      e => !['animal', 'feed', 'health', 'network', 'review'].includes(e.type)
    ),
    results = query.toUpperCase() === 'X42' ? related : searchMasterEvents(s.events, query)
  const selectedEvent = s.events.find(
    e => e.id === selected || e.entity === selected || e.camera === selected
  )
  const card = (title: string, body: React.ReactNode) => (
    <section className="master-card">
      <h3>{title}</h3>
      {body}
    </section>
  )
  const timeline = (events = related) => (
    <div className="master-records">
      {events.map(e => (
        <button key={e.id} onClick={() => I(e.id)}>
          <small>
            {masterClock(e.capture)} · {e.camera}
          </small>
          <strong>{e.id}</strong>
          <span>{e.title}</span>
        </button>
      ))}
    </div>
  )
  const panel = () => {
    switch (step.id) {
      case 'reid':
      case 'why':
      case 'rejected':
        return card(
          'Two tracks → one candidate',
          <>
            <div className="master-pair">
              <div>
                <b>♟</b>
                <strong>CAM-01 / TRK-017</strong>
              </div>
              <span>→ X42 ←</span>
              <div>
                <b>♟</b>
                <strong>CAM-02 / TRK-044</strong>
              </div>
            </div>
            <div className="master-score">
              85%<small>Candidate association · REPLAY TEST</small>
            </div>
            <dl>
              <dt>Appearance</dt>
              <dd>HIGH / scripted similarity</dd>
              <dt>Transition</dt>
              <dd>56 seconds / plausible fixture</dd>
              <dt>Adjacency</dt>
              <dd>180 m / schematic fixture</dd>
              <dt>Identity</dt>
              <dd>Unconfirmed / officer review</dd>
            </dl>
            <p>Rejected fixture: CAM-05 / TRK-081, 4.8 km in 12s = 400 m/s. Excluded from X42.</p>
          </>
        )
      case 'risk':
      case 'risktrail':
        return card(
          'PARAKH / Explainable decision',
          <>
            <div className="master-score">
              {s.risk}
              <small>/100 · HIGH · canonical backend replay</small>
            </div>
            {s.factors.map(f => (
              <div className="master-factor" key={f.code}>
                <span>
                  {f.label}
                  <small>{f.evidence}</small>
                </span>
                <b>+{f.value}</b>
              </div>
            ))}
            <p>
              Candidate association earns no confirmed-identity points. Boundary dwell stays
              context.
            </p>
            <details>
              <summary>Scorer provenance</summary>
              <p>{s.riskSource}</p>
              <p>Checked-in defaults; deployment overrides are not applied here.</p>
            </details>
          </>
        )
      case 'hash':
      case 'evidence':
        return card(
          'PRAMAAN / Live local integrity',
          <>
            <p>INC-1042 · X42 · frozen synthetic record</p>
            {seals.map((x, i) => (
              <div className="master-seal" key={i}>
                <strong>
                  EVD-{5521 + i}{' '}
                  <em className={x.digest === x.computed ? 'ok' : 'bad'}>
                    {x.digest === x.computed ? 'MATCH' : 'MISMATCH'}
                  </em>
                </strong>
                <small>Stored SHA-256</small>
                <code>{x.digest}</code>
                <small>Recomputed bytes</small>
                <code>{x.computed}</code>
              </div>
            ))}
            {!seals.length && <p>Computing actual SHA-256…</p>}
            <button disabled={!seals.length} onClick={() => void tamper(true)}>
              Alter one field
            </button>{' '}
            <button disabled={!seals.length} onClick={() => void tamper(false)}>
              Restore original
            </button>
            <p>Fabric anchor: planned extension. External transactions: 0.</p>
          </>
        )
      case 'offline':
      case 'sync':
        return card(
          'SAKSHAM / Offline continuity',
          <>
            <div className="master-score">
              {s.networkOffline ? 'OFFLINE' : 'CONNECTED'}
              <small>Controlled uplink state</small>
            </div>
            <dl>
              <dt>Metadata fixtures</dt>
              <dd>{records.length} / 7</dd>
              <dt>Actual local hashes</dt>
              <dd>{seals.length} / 3</dd>
              <dt>Replay events delivered</dt>
              <dd>{Math.min(7, delivered)} / 7</dd>
              <dt>Replay payloads delivered</dt>
              <dd>{Math.max(0, delivered - 7)} / 3</dd>
            </dl>
            <p>
              Local simulated delivery; original capture times preserved. Camera coverage does not
              recover when the uplink returns.
            </p>
            {timeline(records.slice(-3))}
          </>
        )
      case 'correlation':
      case 'graph':
      case 'relationship':
      case 'closing':
        return card(
          'SUTRA / One contextual incident',
          <>
            <div className="master-score">
              INC-1042<small>X42 · Zone A · related observations</small>
            </div>
            {timeline(
              related.filter(e =>
                ['vehicle', 'track', 'zone', 'association', 'incident', 'evidence'].includes(e.type)
              )
            )}
            <p>
              Proximity → track continuity → polygon entry → candidate association. Animal stays
              outside the intrusion graph.
            </p>
          </>
        )
      case 'investigation':
      case 'replay':
        return card(
          'Retrieve the connected proof',
          <>
            <label>
              Entity, incident, track or plate
              <input
                value={query}
                onChange={e => Q(e.target.value)}
                placeholder="X42 / INC-1042 / MP09AB1234"
              />
            </label>
            <small>Deterministic fixture search · {results.length} results</small>
            {timeline(results)}
            <button onClick={restart}>Replay Incident</button>{' '}
            <button onClick={() => seek(385)}>Open EVD-5521 integrity</button>
          </>
        )
      case 'review':
        return card(
          'Ambiguous candidate / 61%',
          <>
            <p>CANDIDATE-061 stays separate from X42.</p>
            <strong>{review}</strong>
            <div className="master-actions">
              <button
                onClick={() => {
                  V('Reviewed · remains unconfirmed')
                  log('Secondary candidate reviewed')
                }}
              >
                Review candidate
              </button>
              <button
                onClick={() => {
                  V('Kept separate')
                  log('Candidate kept separate')
                }}
              >
                Keep separate
              </button>
            </div>
          </>
        )
      case 'security':
        return card(
          'Access and audit',
          <>
            <label>
              Replay role{' '}
              <select value={role} onChange={e => U(e.target.value)}>
                <option>Officer</option>
                <option>Observer</option>
              </select>
            </label>
            <button disabled={role !== 'Officer'} onClick={() => log('Officer reviewed evidence')}>
              Review evidence
            </button>
            <p>
              X.509 / TLS: deployment controls, not verified here. Authentication service is a
              repository mock. Role gating is a local replay test.
            </p>
            {audit.map((x, i) => (
              <p key={i}>{x}</p>
            ))}
          </>
        )
      case 'mobile':
      case 'sop':
        return card(
          'Field officer preview',
          <>
            <div className="master-phone">
              <small>SIMULATED FIELD VIEW</small>
              <h2>INC-1042</h2>
              <p>X42 · Zone A · HIGH / {s.risk}</p>
              <p>CAM-01 → candidate CAM-02</p>
              <p>Coverage compromised: CAM-03</p>
              <button onClick={() => log('Local field preview acknowledged incident')}>
                Acknowledge
              </button>
              <button onClick={() => log('Local escalation requested')}>Escalate</button>
            </div>
            <p>SOP is planned. No external notification or dispatch.</p>
            {audit.slice(0, 2).map(x => (
              <p key={x}>{x}</p>
            ))}
          </>
        )
      case 'integration':
        return card(
          'Inspectable C2 envelope',
          <>
            <pre>
              {JSON.stringify(
                {
                  status: 'REPLAY TEST',
                  incident: 'INC-1042',
                  entity: 'X42',
                  risk: s.risk,
                  evidence: 'EVD-5521',
                  candidateIdentity: true,
                },
                null,
                2
              )}
            </pre>
            <p>External receiver not connected. Fabric / MQTT / ONVIF are not demonstrated here.</p>
          </>
        )
      case 'gis':
      case 'heatmap':
      case 'coverage':
      case 'route':
        return card(
          'Same incident / operational picture',
          <>
            <p>X42, INC-1042 and camera boundaries stay in the same sector.</p>
            <button onClick={() => H(x => !x)}>Toggle 7-day fixture heatmap</button>
            <button onClick={() => R(x => !x)}>Toggle illustrative routes</button>
            <dl>
              <dt>Route A</dt>
              <dd>Direct / near active alert</dd>
              <dt>Route B</dt>
              <dd>Longer / lower modeled exposure</dd>
              <dt>Coverage</dt>
              <dd>CAM-03 compromised</dd>
            </dl>
            <p>Controlled history and terrain. Officer chooses; no route is guaranteed safe.</p>
          </>
        )
      case 'anpr':
        return card(
          'C7 / Multi-frame plate context',
          <>
            <div className="master-plate">MP09 AB 1234</div>
            <p>
              V-042 · 6 scripted observations · 91% test vote confidence. Plate context does not
              identify the driver.
            </p>
          </>
        )
      case 'tracking':
      case 'behavior':
      case 'fence':
        return card(
          'One observation develops context',
          <>
            <dl>
              <dt>Track</dt>
              <dd>TRK-017</dd>
              <dt>Boundary dwell signal</dt>
              <dd>{s.behavior ? '52 seconds' : 'Not yet observed'}</dd>
              <dt>Zone A</dt>
              <dd>{s.crossed ? 'Entered' : 'Outside'}</dd>
              <dt>Inside-zone dwell</dt>
              <dd>{s.dwell.toFixed(0)} / 3 seconds</dd>
              <dt>Rule event</dt>
              <dd>{s.alert ? 'EVT-2291 / review' : 'Pending'}</dd>
            </dl>
            <p>
              Movement provides context; the configured people-only polygon rule creates the event.
            </p>
          </>
        )
      case 'trust':
      case 'health':
        return card(
          'Feed trust and coverage',
          <>
            <dl>
              <dt>CAM-01</dt>
              <dd>{s.freeze ? 'SUSPICIOUS / repeated frame' : 'Fresh replay input'}</dd>
              <dt>CAM-03</dt>
              <dd>{s.cameraOffline ? 'OFFLINE / stale' : 'Degraded baseline'}</dd>
              <dt>Health fixture</dt>
              <dd>4.1 FPS / low brightness</dd>
            </dl>
            <p>Camera loss and uplink loss are independent conditions.</p>
          </>
        )
      case 'face':
        return card(
          'Face quality / planned extension',
          <>
            <div className="master-face">MASKED PLACEHOLDER</div>
            <p>No face model or watchlist lookup ran. No personal identity result.</p>
          </>
        )
      case 'audio':
      case 'weather':
      case 'uncertainty':
        return card(
          'Context with visible limitations',
          <>
            <dl>
              <dt>Audio</dt>
              <dd>SIMULATED SENSOR INPUT</dd>
              <dt>Weather</dt>
              <dd>{s.fog ? 'Fog / low visibility' : 'Clear fixture'}</dd>
              <dt>Confidence</dt>
              <dd>{Math.round(s.confidence * 100)}% / fixture</dd>
              <dt>Trust</dt>
              <dd>MEDIUM / controlled test</dd>
            </dl>
            <p>No live microphone or weather sensor connected.</p>
          </>
        )
      default:
        return card(
          step.module,
          <>
            <h2>{step.question}</h2>
            <p>{step.narration}</p>
            <dl>
              <dt>CAM-01</dt>
              <dd>Entry / primary track</dd>
              <dt>CAM-02</dt>
              <dd>Perimeter / handoff</dd>
              <dt>CAM-03</dt>
              <dd>Health challenge</dd>
              <dt>CAM-04</dt>
              <dd>Service road</dd>
            </dl>
            {step.id === 'night' && (
              <button onClick={() => E(x => !x)}>Compare raw / enhanced schematic</button>
            )}
          </>
        )
    }
  }
  return (
    <main className="master-demo">
      {opening && time < 20 && (
        <div className="master-opening">
          <div>
            <small>SSB BORDER INTELLIGENCE / SIH DEMONSTRATION</small>
            <h1>प्रहार | PRAHAAR</h1>
            <h2>
              ONE PLATFORM.
              <br />
              EVERY CAMERA.
            </h2>
            <p>One incident. Every layer of intelligence.</p>
            <blockquote>A camera sees a moment. PRAHAAR connects the story.</blockquote>
            <button onClick={() => seek(20)}>Begin guided story</button>{' '}
            <button
              onClick={() => {
                O(false)
                P(true)
              }}
            >
              Run 8-minute replay
            </button>
            <p>
              <small>
                Synthetic camera replay · actual local integrity · integrations labelled
              </small>
            </p>
            <button
              onClick={() => {
                try {
                  const raw = localStorage.getItem('prahaar-master-evidence')
                  if (!raw) {
                    F('No saved evidence buffer yet.')
                    seek(340)
                    return
                  }
                  const parsed = JSON.parse(raw) as Seal[]
                  if (
                    !Array.isArray(parsed) ||
                    !parsed.every(
                      x => typeof x.original === 'string' && typeof x.digest === 'string'
                    )
                  )
                    throw Error()
                  B(parsed)
                  seek(340)
                } catch {
                  F('Saved evidence could not be restored.')
                  O(false)
                }
              }}
            >
              Resume saved local evidence
            </button>
          </div>
        </div>
      )}
      <header className="master-header">
        <div>
          <small>PRAHAAR / CONNECTED INCIDENT DEMO</small>
          <h1>One incident. Every layer of intelligence.</h1>
        </div>
        <div>
          <strong>{s.incident ? 'INC-1042' : 'INCIDENT BUILDING'}</strong>
          <small>
            {s.associated
              ? 'X42 / CANDIDATE ENTITY'
              : s.tracking
                ? 'TRK-017 / CAMERA TRACK'
                : 'SECTOR OBSERVATION'}
          </small>
        </div>
        <b className="master-status">
          {step.status}
          {step.status === 'LIVE' ? ' · LOCAL ONLY' : ''}
        </b>
      </header>
      <nav className="master-chain">
        Observation → Context → Correlation → Decision → Evidence → Operational picture →
        Investigation
      </nav>
      <div className="master-toolbar">
        <button
          onClick={() => {
            if (time >= 480) {
              T(20)
              P(true)
            } else P(x => !x)
          }}
        >
          {playing && time < 480 ? 'Pause' : 'Play'}
        </button>
        <button disabled={!index} onClick={() => seek(masterSteps[index - 1].at)}>
          Previous
        </button>
        <button
          disabled={index === masterSteps.length - 1}
          onClick={() => seek(masterSteps[index + 1].at)}
        >
          Next
        </button>
        <select
          aria-label="Story chapter"
          value={step.id}
          onChange={e => seek(masterSteps.find(x => x.id === e.target.value)!.at)}
        >
          {masterSteps.map(x => (
            <option key={x.id} value={x.id}>
              {x.module} · {x.title}
            </option>
          ))}
        </select>
        <select aria-label="Replay speed" value={speed} onChange={e => S(Number(e.target.value))}>
          <option value={1}>8-minute / 1×</option>
          <option value={4}>2-minute / 4×</option>
        </select>
        <strong>
          {Math.floor(time / 60)}:{String(Math.floor(time % 60)).padStart(2, '0')} / 8:00
        </strong>
        <input
          aria-label="Replay timeline"
          type="range"
          min="0"
          max="480"
          value={time}
          onChange={e => seek(Number(e.target.value))}
        />
      </div>
      <div className="master-workspace">
        <section className="master-world">
          <div className="master-world-title">
            <div>
              <small>ONE CONTINUOUS SECTOR / FOUR CAMERA REGIONS</small>
              <h2>{step.title}</h2>
            </div>
            <strong>{masterClock(s.capture)} IST</strong>
          </div>
          <MasterSector
            state={s}
            enhanced={enhanced}
            heatmap={heatmap || step.id === 'heatmap'}
            routes={routes || step.id === 'route'}
            selected={selected}
            onSelect={I}
          />
          <div className="master-world-controls">
            <button onClick={() => E(x => !x)}>
              {enhanced ? 'Enhanced schematic' : 'Raw schematic'}
            </button>
            <span>SYNTHETIC REPLAY</span>
            <span>UPLINK: {s.networkOffline ? 'OFFLINE' : 'CONNECTED'}</span>
            <span>CAM-03: {s.cameraOffline ? 'COVERAGE LOST' : 'DEGRADED'}</span>
          </div>
          <div className="master-output">
            <small>THIS LAYER PRODUCES</small>
            <strong>{step.output}</strong>
          </div>
          <div className="master-events">
            <h3>Same incident / capture timeline</h3>
            {s.events.slice(-4).map(e => (
              <button key={e.id} onClick={() => I(e.id)}>
                <time>{masterClock(e.capture)}</time>
                <strong>{e.id}</strong>
                <span>{e.title}</span>
              </button>
            ))}
          </div>
          {selected && (
            <div className="master-inspector">
              <button onClick={() => I('')}>×</button>
              <strong>{selected}</strong>
              <p>
                {selectedEvent
                  ? `${selectedEvent.camera} · ${masterClock(selectedEvent.capture)} · ${selectedEvent.detail}`
                  : 'Schematic scene element; inspect recorded context in the timeline.'}
              </p>
            </div>
          )}
        </section>
        <aside>
          <div className="master-question">
            <small>{step.module}</small>
            <h2>{step.question}</h2>
          </div>
          {panel()}
        </aside>
      </div>
      <footer className="master-footer">
        <div className="master-actions">
          {[
            { at: 190, label: 'Camera handoff' },
            { at: 260, label: 'One incident' },
            { at: 280, label: 'Explain risk' },
            { at: 320, label: 'Network outage' },
            { at: 385, label: 'Verify evidence' },
            { at: 470, label: 'Investigate' },
          ].map(x => (
            <button key={x.at} onClick={() => seek(x.at)}>
              {x.label}
            </button>
          ))}
        </div>
        <details>
          <summary>
            Presenter notes · {index + 1} / {masterSteps.length}
          </summary>
          <p>{step.narration}</p>
        </details>
        <details>
          <summary>Inject tougher conditions</summary>
          {(['network', 'camera', 'fog'] as const).map(key => (
            <button
              key={key}
              aria-pressed={faults[key]}
              onClick={() => {
                J(f => ({ ...f, [key]: !f[key] }))
                log(`${key} fault toggled`)
              }}
            >
              {key}: {faults[key] ? 'injected' : 'story state'}
            </button>
          ))}
        </details>
        {error && <p role="alert">{error}</p>}
        <small>
          REPLAY TEST = controlled fixtures · LIVE LOCAL = browser operation · PLANNED = not
          implemented · no recorded video or external sensors attached
        </small>
      </footer>
    </main>
  )
}
