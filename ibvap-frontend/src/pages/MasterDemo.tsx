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
import { simpleStory } from '../components/demo/simpleStory'
import { useDemoNarration } from '../components/demo/useDemoNarration'
import { narrationScript } from '../components/demo/narrationScript'
import { advanceReplay, DEFAULT_REPLAY_SPEED } from '../components/demo/rapidReplay'
type Seal = { original: string; bytes: string; digest: string; computed: string }
export function MasterDemo() {
  const [time, T] = useState(0),
    [playing, P] = useState(true),
    [speed, S] = useState(DEFAULT_REPLAY_SPEED),
    [opening, O] = useState(false),
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
    [sealIndex, chooseSeal] = useState(0),
    [recordPage, choosePage] = useState(0),
    [showNotes, notes] = useState(false),
    [showFaults, faultPanel] = useState(false),
    [faults, J] = useState({ network: false, camera: false, fog: false })
  const hashing = useRef(false),
    run = useRef(0),
    s = masterAt(time, faults),
    step = simpleStory(s.current),
    index = masterSteps.indexOf(s.current)
  const narration = useDemoNarration(narrationScript[step.id], step.id, playing && time < 480)
  const log = (message: string) =>
    A(a => [`${new Date().toLocaleTimeString()} · ${message}`, ...a].slice(0, 8))
  const seek = (n: number) => {
    if (n < 320) D(0)
    T(n)
    P(false)
    O(false)
    I('')
    choosePage(0)
  }
  useEffect(() => {
    if (!playing) return
    let frame = 0
    let previous = performance.now()
    const tick = (now: number) => {
      if (now - previous >= 80) {
        const elapsed = Math.min((now - previous) / 1000, 0.25)
        previous = now
        T(t => {
          const boundary = masterSteps.find(chapter => chapter.at > t)?.at ?? 480
          const next = Math.min(advanceReplay(t, speed * elapsed), boundary)
          if (
            narration.enabled &&
            narration.speaking.current &&
            (next === 480 || masterAt(next).current.id !== masterAt(t).current.id)
          )
            return t
          return next
        })
      }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing, speed, narration.enabled, narration.speaking])
  const hashReady = time >= 340
  const deliveryReady = time >= 365
  useEffect(() => {
    if (!hashReady || seals.length || hashing.current) return
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
  }, [hashReady, seals.length])
  useEffect(() => {
    if (!deliveryReady || s.networkOffline) return
    const timer = setInterval(() => D(n => Math.min(10, n + 1)), 500)
    return () => clearInterval(timer)
  }, [deliveryReady, s.networkOffline])
  const tamper = async (changed: boolean) => {
    if (!seals[sealIndex]) return
    const bytes = changed
      ? seals[sealIndex].original.replace('PRAHAAR master incident', 'ALTERED incident')
      : seals[sealIndex].original
    const computed = await sha256(bytes)
    B(a => a.map((x, i) => (i === sealIndex ? { ...x, bytes, computed } : x)))
    log(changed ? 'Evidence altered for integrity test' : 'Original evidence restored')
  }
  const restart = () => {
    run.current++
    B([])
    D(0)
    T(60)
    S(DEFAULT_REPLAY_SPEED)
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
  const metadataVersion = records.map(record => record.id).join('|')
  useEffect(() => {
    if (time < 320) return
    try {
      localStorage.setItem('prahaar-master-metadata', JSON.stringify(records))
    } catch {
      queueMicrotask(() => F('Metadata storage failed; records remain in memory.'))
    }
    // Persist only when the record set changes or offline buffering starts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [time >= 320, metadataVersion])
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
      {events.slice(recordPage * 3, recordPage * 3 + 3).map(e => (
        <button key={e.id} onClick={() => I(e.id)}>
          <small>
            {masterClock(e.capture)} · {e.camera}
          </small>
          <strong>{e.id}</strong>
          <span>{e.title}</span>
        </button>
      ))}
      {events.length > 3 && (
        <div className="master-record-pages">
          <button disabled={recordPage === 0} onClick={() => choosePage(p => p - 1)}>
            ←
          </button>
          <small>
            {recordPage + 1} / {Math.ceil(events.length / 3)}
          </small>
          <button
            disabled={(recordPage + 1) * 3 >= events.length}
            onClick={() => choosePage(p => p + 1)}
          >
            →
          </button>
        </div>
      )}
    </div>
  )
  const panel = () => {
    switch (step.id) {
      case 'departure':
      case 'transfer':
      case 'followcars':
        return card(
          'Person and both cars',
          <>
            <div className="master-vehicle-chain">
              <button onClick={() => I('V-042')}>
                Car 1 <strong>V-042</strong>
                <small>MP09AB1234</small>
              </button>
              <span>→</span>
              <button onClick={() => I('X42')}>
                Person <strong>X42</strong>
                <small>{s.journey.boarded ? 'Inside Car 2' : 'Walking / camera track'}</small>
              </button>
              <span>→</span>
              <button disabled={!s.journey.secondVisible} onClick={() => I('V-077')}>
                Car 2 <strong>V-077</strong>
                <small>DL08CD5678</small>
              </button>
            </div>
            <dl>
              <dt>Car 1</dt>
              <dd>{s.time >= 170 ? 'Following Path B' : 'At checkpoint'}</dd>
              <dt>Person</dt>
              <dd>{s.journey.boarded ? 'Linked to Car 2' : 'Tracked separately'}</dd>
              <dt>Car 2</dt>
              <dd>
                {s.journey.secondMoving
                  ? 'Moving with X42'
                  : s.journey.boarded
                    ? 'Person gets inside'
                    : s.journey.secondVisible
                      ? 'Approaching'
                      : 'Not seen yet'}
              </dd>
            </dl>
            <p>
              After boarding, X42’s position comes from the car link. It is not a fresh camera
              detection of a person.
            </p>
          </>
        )
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
            <div className="master-actions">
              {seals.map((_, i) => (
                <button key={i} aria-pressed={sealIndex === i} onClick={() => chooseSeal(i)}>
                  Evidence {i + 1}
                </button>
              ))}
            </div>
            {seals.slice(sealIndex, sealIndex + 1).map((x, i) => (
              <div className="master-seal" key={i}>
                <strong>
                  EVD-{5521 + sealIndex}{' '}
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
            <small>Every saved test record keeps its original camera time.</small>
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
                [
                  'vehicle',
                  'vehicle-move',
                  'boarding',
                  'track',
                  'zone',
                  'association',
                  'incident',
                  'evidence',
                ].includes(e.type)
              )
            )}
            <p>
              Proximity → track continuity → polygon entry → candidate association. Animal stays
              outside the intrusion graph.
            </p>
            {time >= 223 && (
              <p>
                <strong>Attack exercise:</strong> officer review required.{' '}
                {time >= 452 ? 'Security response acknowledged.' : 'Post protection alert active.'}{' '}
                Car 1: {s.journey.firstStopped ? 'held at Path B gate' : 'approaching Path B gate'}.
                Car 2:{' '}
                {s.journey.secondStopped
                  ? 'held at eastern post barrier'
                  : 'approaching eastern post'}
                . No confirmed arrest or identity claim.
              </p>
            )}
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
                onChange={e => {
                  Q(e.target.value)
                  choosePage(0)
                }}
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
            {time >= 223 && (
              <p>
                <strong>Attack exercise / officer review:</strong> gunfire report near the eastern
                security post. Protect the post; follow both vehicles to their marked holding
                points. A sound does not confirm a terrorist identity.
              </p>
            )}
          </>
        )
      default:
        return card(
          step.module,
          <>
            <h2>{step.question}</h2>
            <p>{narrationScript[step.id]}</p>
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
    <section className="master-demo" aria-label="Connected incident demo">
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
          <h1>One person. Two cars. One connected story.</h1>
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
        See → Follow → Connect → Explain → Save proof → Find it again
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
              {simpleStory(x).title}
            </option>
          ))}
        </select>
        <select aria-label="Replay speed" value={speed} onChange={e => S(Number(e.target.value))}>
          <option value={1}>Slow / 1×</option>
          <option value={3}>Detailed / 3×</option>
          <option value={4}>Default / 4× · Full detail</option>
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
          <div className="master-camera-wall" aria-label="Four camera replay views">
            {[
              { id: 'CAM-01', view: '15 116 545 290', label: 'Entry / person exits Car 1' },
              {
                id: 'CAM-02',
                view: '570 116 201 290',
                label: s.journey.boarded ? 'Person linked to Car 2' : 'Person moves to Car 2',
              },
              {
                id: 'CAM-03',
                view: '783 116 163 290',
                label: s.cameraOffline ? 'Offline / blind area' : 'Camera health',
              },
              {
                id: 'CAM-04',
                view: '145 330 640 150',
                label: s.time >= 170 ? 'Car 1 / Path B' : 'Service road',
              },
            ].map(cam => (
              <button
                key={cam.id}
                className="master-camera-tile"
                aria-label={`Inspect ${cam.id} camera preview`}
                onClick={() => I(cam.id)}
              >
                <strong>
                  {cam.id}
                  <small>{cam.id === 'CAM-03' && s.cameraOffline ? 'OFFLINE' : 'REPLAY'}</small>
                </strong>
                <MasterSector
                  state={s}
                  enhanced={enhanced}
                  heatmap={false}
                  routes={false}
                  selected=""
                  onSelect={() => {}}
                  viewport={cam.view}
                />
                <span>{cam.label}</span>
              </button>
            ))}
          </div>
          <div className="master-world-controls">
            <button onClick={() => E(x => !x)}>
              {enhanced ? 'Enhanced schematic' : 'Raw schematic'}
            </button>
            <span>SYNTHETIC REPLAY</span>
            <span>UPLINK: {s.networkOffline ? 'OFFLINE' : 'CONNECTED'}</span>
            <span>CAM-03: {s.cameraOffline ? 'COVERAGE LOST' : 'DEGRADED'}</span>
          </div>
          <div className="master-output">
            <small>WHAT HAPPENS</small>
            <strong>{step.output}</strong>
          </div>
          <div className="master-events">
            {s.events.slice(-1).map(e => (
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
                {selected === 'V-042'
                  ? `Car 1 · MP09AB1234 · ${s.time >= 170 ? 'Path B' : 'Checkpoint'} · linked to X42 by the earlier exit observation.`
                  : selected === 'V-077'
                    ? `Car 2 · DL08CD5678 · ${s.journey.boarded ? 'X42 inside; position inferred from this car' : 'Approaching X42'}.`
                    : selected === 'X42' && s.journey.boarded
                      ? 'X42 exited V-042, crossed Zone A, then boarded V-077. Person position is inferred from Car 2; no fresh person detection is claimed.'
                      : selectedEvent
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
          {showNotes
            ? card(
                'Simple explanation',
                <>
                  <p>{narrationScript[step.id]}</p>
                  <details>
                    <summary>Full presenter notes</summary>
                    <p>{narrationScript[step.id]}</p>
                  </details>
                </>
              )
            : showFaults
              ? card(
                  'Try a tougher situation',
                  <>
                    <p>Toggle a test failure. Camera and internet failures stay separate.</p>
                    {(['network', 'camera', 'fog'] as const).map(key => (
                      <button
                        key={key}
                        aria-pressed={faults[key]}
                        onClick={() => J(f => ({ ...f, [key]: !f[key] }))}
                      >
                        {key === 'network' ? 'Internet' : key === 'camera' ? 'Camera 3' : 'Fog'}:{' '}
                        {faults[key] ? 'test ON' : 'normal story'}
                      </button>
                    ))}
                  </>
                )
              : panel()}
        </aside>
      </div>
      <footer className="master-footer">
        <div className="master-actions">
          {[
            { at: 190, label: 'Camera handoff' },
            { at: 170, label: 'Car 1 / Path B' },
            { at: 205, label: 'Change cars' },
            { at: 213, label: 'Follow both cars' },
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
        <div className="master-tools">
          <button
            aria-pressed={showNotes}
            onClick={() => {
              notes(x => !x)
              faultPanel(false)
            }}
          >
            Explain this step
          </button>
          <button
            aria-pressed={showFaults}
            onClick={() => {
              faultPanel(x => !x)
              notes(false)
            }}
          >
            Try failures
          </button>
          <button
            disabled={!narration.supported}
            aria-pressed={narration.enabled}
            onClick={narration.toggle}
          >
            Voice: {narration.enabled ? 'On' : 'Off'}
          </button>
          <button disabled={!narration.supported} onClick={narration.speak}>
            Read this step
          </button>
          <select
            aria-label="Narrator voice"
            value={narration.voiceName}
            onChange={e => narration.setVoiceName(e.target.value)}
          >
            <option value="">Browser voice</option>
            {narration.voices.map(v => (
              <option key={v.name} value={v.name}>
                {v.name}
              </option>
            ))}
          </select>
          <span
            role="status"
            title="Full explanations at every chapter. Simulation runs at 4× and waits for narration to finish before moving to the next chapter. Tap Read this step if audio is blocked."
          >
            {narration.status}
          </span>
        </div>
        {error && <p role="alert">{error}</p>}
        <small>
          REPLAY TEST = controlled fixtures · LIVE LOCAL = browser operation · PLANNED = not
          implemented · no recorded video or external sensors attached
        </small>
      </footer>
    </section>
  )
}
