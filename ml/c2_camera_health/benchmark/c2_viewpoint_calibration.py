# -*- coding: utf-8 -*-
"""C2 F5 calibration sweep evidence — ViewpointDetector (scale_factor x min_features).

Runs the REAL production ViewpointDetector (app/domain/camera_health/viewpoint.py,
repaired: ratio-test matcher, similarity RANSAC, frame-width-normalized score)
against the frozen reopen corpus:

  - reference init rate (ONLINE n=24 / VIEWPOINT_CHANGED n=15)
  - VIEWPOINT_CHANGED confirmed detection recall (component-level
    shift_detected, OpenCV RNG pinned per sample exactly like the benchmark
    component evaluation eval_viewpoint does)
  - ONLINE false-shift rate (component-level + engine gate score>=0.3 and
    confidence>=0.5)
  - per-sample detail at the chosen operating point
  - confidence-gate trade-off table (evaluates the engine's trust bar)
  - analyze() latency percentiles

Not part of the benchmark harness; selection evidence for spec section 12-14.
Output: c2_viewpoint_calibration.json next to this script.
"""
import importlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\SIH\ibvap-backend")

import numpy as np  # noqa: E402
import cv2  # noqa: E402

gen = importlib.import_module("gen_c2_corpus")
from app.domain.camera_health.viewpoint import ViewpointDetector  # noqa: E402

manifest = json.loads(gen.MANIFEST_PATH.read_text(encoding="utf-8"))
samples = gen.build_samples()
for s, row in zip(samples, manifest["samples"]):
    s.telemetry = row["telemetry"]

ONLINE = [s for s in samples if s.cls == "ONLINE"]
VP = [s for s in samples if s.cls == "VIEWPOINT_CHANGED"]
FRAMES = {s.sample_id: gen.materialize_frames(s) for s in ONLINE + VP}

SCORE_THR = 0.3
CONF_THR = 0.5


def run_sample(s, scale, min_features):
    frames = FRAMES[s.sample_id]
    det = ViewpointDetector(scale_factor=scale, min_features=min_features)
    cv2.setRNGSeed(int(s.seed))
    ref_ok = det.set_reference(frames[0])
    last = None
    lat = []
    for i in range(1, len(frames)):
        cv2.setRNGSeed(int(s.seed) + i)
        t0 = time.perf_counter()
        last = det.analyze(frames[i])
        lat.append((time.perf_counter() - t0) * 1000)
    return det, ref_ok, last, lat


def run_combo(scale, min_features):
    lat = []
    detail = {"ONLINE": {}, "VIEWPOINT_CHANGED": {}}
    for tag, items in (("ONLINE", ONLINE), ("VIEWPOINT_CHANGED", VP)):
        for s in items:
            det, ref_ok, last, l = run_sample(s, scale, min_features)
            lat.extend(l)
            detail[tag][s.sample_id] = dict(
                ref_ok=bool(ref_ok),
                ref_features=int(det.reference_feature_count),
                confirmed=bool(last.shift_detected) if last else None,
                score=round(float(last.shift_score), 4) if last else None,
                confidence=round(float(last.confidence or 0.0), 4) if last else None,
                reason=last.reason if last else None,
            )
    la = np.array(lat)

    def counts(tag):
        rows = detail[tag].values()
        return dict(
            init=sum(1 for r in rows if r["ref_ok"]),
            confirmed=sum(1 for r in rows if r["confirmed"]),
            score_only=sum(1 for r in rows
                           if r["score"] is not None and r["score"] >= SCORE_THR),
            engine_gate=sum(1 for r in rows if r["score"] is not None
                            and r["score"] >= SCORE_THR
                            and r["confidence"] >= CONF_THR),
            n=len(detail[tag]),
        )

    return dict(
        scale_factor=scale, min_features=min_features,
        online=counts("ONLINE"), viewpoint=counts("VIEWPOINT_CHANGED"),
        latency_ms=dict(p50=round(float(np.percentile(la, 50)), 2),
                        p95=round(float(np.percentile(la, 95)), 2),
                        max=round(float(la.max()), 2)),
        detail=detail,
    )


results = []
for scale, mf in ((0.75, 30), (1.0, 15), (1.0, 30), (1.0, 60), (1.0, 100)):
    row = run_combo(scale, mf)
    results.append(row)
    o, v = row["online"], row["viewpoint"]
    print(f"scale={scale:4.2f} mf={mf:3d} | init ON {o['init']}/{o['n']} VP {v['init']}/{v['n']} "
          f"| VP confirmed {v['confirmed']}/{v['n']} score {v['score_only']}/{v['n']} gate {v['engine_gate']}/{v['n']} "
          f"| ON confirmed {o['confirmed']}/{o['n']} score {o['score_only']}/{o['n']} gate {o['engine_gate']}/{o['n']} "
          f"| lat p50={row['latency_ms']['p50']} p95={row['latency_ms']['p95']}")

# Per-sample detail + confidence-gate trade-off at the chosen operating point
best = next(r for r in results if r["scale_factor"] == 1.0 and r["min_features"] == 30)
print("\n--- per-sample detail @ scale=1.0 mf=30 ---")
for tag in ("VIEWPOINT_CHANGED", "ONLINE"):
    for sid, r in sorted(best["detail"][tag].items()):
        print(f"  {tag[:3]} {sid}: ref_ok={int(r['ref_ok'])} feat={r['ref_features']:3d} "
              f"conf={r['confirmed']!s:5s} score={r['score']} confi={r['confidence']} | {r['reason']}")

print("\n--- confidence-gate trade-off (score>=0.3 AND confidence>=X) @ 1.0/30 ---")
gate_rows = []
for conf_x in (0.3, 0.4, 0.5, 0.6):
    v = sum(1 for r in best["detail"]["VIEWPOINT_CHANGED"].values()
            if r["score"] is not None and r["score"] >= SCORE_THR and r["confidence"] >= conf_x)
    o = sum(1 for r in best["detail"]["ONLINE"].values()
            if r["score"] is not None and r["score"] >= SCORE_THR and r["confidence"] >= conf_x)
    gate_rows.append(dict(conf_threshold=conf_x, vp_flags=v, online_flags=o))
    print(f"  conf>={conf_x}: VP flagged {v}/15 | ONLINE flagged {o}/24")

out = Path(HERE / "c2_viewpoint_calibration.json")
out.write_text(json.dumps(dict(
    corpus_manifest_sha256=manifest["manifest_sha256"],
    combos=[{k: v for k, v in r.items() if k != "detail"} for r in results],
    chosen=dict(scale_factor=1.0, min_features=30),
    per_sample_at_chosen=best["detail"],
    confidence_gate_tradeoff=gate_rows,
), indent=2), encoding="utf-8")
print(f"\nwrote {out}")
