# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — C2 Classical CV Camera-Health Benchmark — Expanded v1.1 runner
# (spec §27–§33)
#
# Runs the SAME frozen evaluation logic as run_c2_benchmark.py (imported,
# not modified — §25/§125) over the versioned PRHAAR-C2-v1.1 corpus:
#   - first 180 samples = the frozen v1 corpus, proven byte-identical by the
#     integrity block (rebuild match + prefix match + repair1 reproduction)
#   - samples 181–300 = the §27 expansion classes: quiet scenes / small
#     object motion / low-texture viewpoint / network jitter / clock skew /
#     gradual viewpoint shift / partial obstruction / mixed degradations
#
# Expectations are fixed by construction (§28: engine thresholds are NOT
# tuned on this expanded set). The v1 failure history (180/180
# ENGINE_EXCEPTION) is preserved in the repair report (§50); v1.1 is
# additive evidence, not a replacement.
#
# Note on cv2 RNG: component-level viewpoint evaluation happens for the same
# classes as the frozen harness on the first 180 samples, in the same order,
# so the v1 subset's OpenCV RNG call sequence is identical to the repair1
# run — which the integrity block verifies record-for-record.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BACKEND = Path(r"C:\SIH\ibvap-backend")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BACKEND))

import cv2  # noqa: E402

from run_c2_benchmark import (  # noqa: E402  (frozen harness — read-only import)
    BROKEN_VISUAL_CLASSES, CONFIG, ENGINE_FILES, aggregate, component_tables,
    eval_freeze, eval_image_quality, eval_viewpoint, freeze_noise_sweep,
    run_end_to_end,
)

import gen_c2_corpus as v1  # noqa: E402
from gen_c2_corpus import sha256_file  # noqa: E402
from gen_c2_corpus_v11 import (  # noqa: E402
    CORPUS_VERSION, MANIFEST_PATH, RELEASE_NAME, V1_MANIFEST_PATH,
    V1_MANIFEST_SHA256, build_samples_v11, materialize_frames_v11,
)

RUN_TAG = sys.argv[1] if len(sys.argv) > 1 else "v11run1"
OUT_PATH = HERE / f"c2_v11_benchmark_results_{RUN_TAG}.json"
REPAIR1_PATH = HERE / "c2_benchmark_results_repair1.json"

# Frozen harness policy: component-level viewpoint eval for these classes…
VP_EVAL_CLASSES = ("VIEWPOINT_CHANGED", "ONLINE")
# …plus the two v1.1 classes designed to exercise viewpoint detection/refusal.
# These are all appended after the first 180 samples, so the v1 subset's call
# sequence (and therefore its cv2 RNG state trajectory) is untouched.
VP_EVAL_EXTRA_V11 = ("GRADUAL_VIEWPOINT_SHIFT", "LOW_TEXTURE_VIEWPOINT")

# §31 false-ONLINE sets over the expanded corpus. Every member class must
# expect a non-ONLINE overall state (guarded below) — a class that expects
# ONLINE (e.g. LOW_TEXTURE_VIEWPOINT) can never join a false-ONLINE set.
STRICT_V11_CLASSES = sorted(set(BROKEN_VISUAL_CLASSES) | {
    "PARTIAL_OBSTRUCTION", "MIXED_DEGRADATION",
})
BROAD_V11_CLASSES = sorted(set(STRICT_V11_CLASSES) | {
    "DEGRADED", "VIEWPOINT_CHANGED", "STALE_FEED", "STREAM_DROP_FROZEN",
    "GRADUAL_VIEWPOINT_SHIFT", "NETWORK_JITTER_SEVERE",
})


def check_false_online_sets(manifest: dict) -> None:
    """Guard: no class in a false-ONLINE set may expect ONLINE (§31 sanity)."""
    expected = {row["cls"]: row["expected_state"] for row in manifest["samples"]}
    for name, classes in (("strict_v11", STRICT_V11_CLASSES),
                          ("broad_v11", BROAD_V11_CLASSES)):
        bad = [c for c in classes if expected.get(c) == "ONLINE"]
        if bad:
            raise RuntimeError(
                f"{name} false-ONLINE set contains ONLINE-expected classes: {bad}"
            )


def v1_integrity_checks(manifest_v11: dict) -> dict:
    """Prove the v1 subset of the v1.1 corpus is the frozen v1 corpus.

    (a) recompute the v1 manifest with the frozen generator and require the
        pinned SHA-256 (§26: manifest f251e908…);
    (b) require the on-disk v1 manifest to match that rebuild sample-for-sample;
    (c) require the v1.1 manifest's first 180 sample rows to equal the v1 rows
        exactly (and the v1.1 manifest to pin the v1 SHA-256).
    Any failure here is fatal: v1.1 scoring on a mutated v1 subset would be
    invalid evidence.
    """
    rebuilt = v1.build_manifest()
    rebuild_ok = rebuilt["manifest_sha256"] == V1_MANIFEST_SHA256
    if not rebuild_ok:
        raise RuntimeError(
            f"v1 manifest rebuild mismatch: {rebuilt['manifest_sha256']} != "
            f"{V1_MANIFEST_SHA256}"
        )
    disk = json.loads(V1_MANIFEST_PATH.read_text(encoding="utf-8"))
    disk_ok = (
        disk.get("manifest_sha256") == V1_MANIFEST_SHA256
        and disk.get("n_samples") == 180
        and disk.get("samples") == rebuilt["samples"]
    )
    if not disk_ok:
        raise RuntimeError("on-disk v1 manifest does not match the rebuilt frozen manifest")
    prefix_ok = (
        manifest_v11.get("n_samples") == 300
        and manifest_v11.get("extends_manifest_sha256") == V1_MANIFEST_SHA256
        and manifest_v11.get("samples", [])[:180] == disk["samples"]
    )
    if not prefix_ok:
        raise RuntimeError("v1.1 manifest first 180 rows do not equal the frozen v1 rows")
    return dict(
        v1_manifest_sha256_pinned=V1_MANIFEST_SHA256,
        v1_manifest_rebuild_sha256=rebuilt["manifest_sha256"],
        v1_manifest_rebuild_ok=bool(rebuild_ok),
        v1_manifest_disk_matches_rebuild=bool(disk_ok),
        v11_prefix_equals_v1_rows=bool(prefix_ok),
        v11_n_samples=manifest_v11["n_samples"],
    )


def repair1_subset_match(canonical_records: list[dict]) -> dict:
    """Compare the first 180 canonical records against the repair1 run.

    Same frozen corpus + same frozen harness => the v1 subset must reproduce
    repair1 record-for-record (status_reason is already excluded from the
    canonical output). A mismatch would mean this run is not a faithful
    extension of the repaired pipeline and must be surfaced, never hidden.
    """
    if not REPAIR1_PATH.exists():
        return dict(repair1_file=str(REPAIR1_PATH.name), repair1_available=False,
                    repair1_engine_subset_match=None,
                    repair1_full_record_subset_match=None,
                    repair1_first_mismatch=None)
    ref = json.loads(REPAIR1_PATH.read_text(encoding="utf-8"))
    ref_records = ref["canonical"]["records"]
    n = min(len(ref_records), len(canonical_records), 180)
    engine_ok = 0
    full_ok = 0
    first_mismatch = None
    for i in range(n):
        a, b = canonical_records[i], ref_records[i]
        if a["engine"] == b["engine"]:
            engine_ok += 1
        if a == b:
            full_ok += 1
        elif first_mismatch is None:
            diff_keys = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
            first_mismatch = dict(position=i, sample_id=a.get("sample_id"),
                                  diff_keys=diff_keys)
    return dict(
        repair1_file=str(REPAIR1_PATH.name), repair1_available=True,
        repair1_engine_subset_match=f"{engine_ok}/{n}",
        repair1_full_record_subset_match=f"{full_ok}/{n}",
        repair1_first_mismatch=first_mismatch,
    )


def macro_metrics(aggregates: dict) -> dict:
    per_state = aggregates["per_state"]
    if not per_state:
        return dict(precision=None, recall=None, f1=None)
    return dict(
        precision=round(float(np.mean([v["precision"] for v in per_state.values()])), 4),
        recall=round(float(np.mean([v["recall"] for v in per_state.values()])), 4),
        f1=aggregates["macro_f1"],
    )


def false_online_rates(records: list[dict]) -> dict:
    def block(classes) -> dict:
        rows = [r for r in records if r["cls"] in classes]
        online = [r for r in rows if r["engine"]["overall_status"] == "ONLINE"]
        per_class = {}
        for c in sorted(classes):
            c_rows = [r for r in rows if r["cls"] == c]
            c_online = [r for r in c_rows if r["engine"]["overall_status"] == "ONLINE"]
            per_class[c] = dict(
                n=len(c_rows), online=len(c_online),
                online_rate=round(len(c_online) / len(c_rows), 4) if c_rows else None,
            )
        return dict(
            classes=sorted(classes),
            false_online=f"{len(online)}/{len(rows)}",
            false_online_rate=round(len(online) / len(rows), 4) if rows else None,
            per_class=per_class,
        )

    return dict(strict_v11=block(STRICT_V11_CLASSES),
                broad_v11=block(BROAD_V11_CLASSES))


def main():
    t0 = time.time()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    samples = build_samples_v11()
    if len(samples) != len(manifest["samples"]):
        raise RuntimeError(
            f"sample/manifest length mismatch: {len(samples)} vs {len(manifest['samples'])}"
        )
    for s, row in zip(samples, manifest["samples"]):
        s.telemetry = row["telemetry"]

    check_false_online_sets(manifest)
    v1_int = v1_integrity_checks(manifest)

    module_hashes = {f: sha256_file(BACKEND / f) for f in ENGINE_FILES}
    run_utc_ts = datetime.now(timezone.utc).replace(tzinfo=None)

    records = []
    for s in samples:
        base_ts = datetime.now(timezone.utc).replace(tzinfo=None)
        frames = materialize_frames_v11(s)
        rec = dict(
            sample_id=s.sample_id, cls=s.cls, subvariant=s.subvariant,
            expected_state=s.expected_state, seed=s.seed,
            n_frames=len(frames),
        )
        if frames:
            rec["iq"] = eval_image_quality(frames)
            rec["freeze"] = eval_freeze(frames, s.seed, base_ts)
            if s.cls in VP_EVAL_CLASSES or s.cls in VP_EVAL_EXTRA_V11:
                try:
                    rec["viewpoint"] = eval_viewpoint(frames, s.seed)
                except Exception as exc:  # surface, never abort the whole run
                    rec["viewpoint_error"] = f"{type(exc).__name__}: {exc}"
        rec["engine"] = run_end_to_end(s, frames, base_ts)
        records.append(rec)

    sweep = freeze_noise_sweep()
    aggregates = aggregate(records)
    comp = component_tables(records)
    macro = macro_metrics(aggregates)
    fo_v11 = false_online_rates(records)

    canonical_records = [
        {**r, "engine": {k: v for k, v in r["engine"].items() if k != "status_reason"}}
        for r in records
    ]

    v1_int.update(repair1_subset_match(canonical_records))

    canonical = dict(
        corpus_manifest_sha256=manifest["manifest_sha256"],
        config={k: v for k, v in CONFIG.__dict__.items()},
        module_hashes=module_hashes,
        cv2_version=cv2.__version__,
        numpy_version=np.__version__,
        records=canonical_records,
        freeze_noise_sweep=sweep,
    )
    text = json.dumps(canonical, indent=2, sort_keys=True, default=str)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    n_exc = sum(1 for r in records if r["engine"]["overall_status"] == "ENGINE_EXCEPTION")

    out = dict(
        benchmark="PRHAAR-C2-CAMERA-HEALTH-CLASSICAL-BENCH",
        version=CORPUS_VERSION,
        release=RELEASE_NAME,
        run_tag=RUN_TAG,
        run_utc=run_utc_ts.isoformat(),
        wall_seconds=round(time.time() - t0, 3),
        spec_compliance=dict(
            s27="expanded corpus (PRHAAR-C2-v1.1) added only after the original "
                "180-sample benchmark passed on the repaired engine; versioned manifest maintained",
            s28="expectations fixed by construction; engine thresholds NOT tuned on this expanded set",
            s29="per-class + per-state precision/recall/F1, macro precision/recall/F1, "
                "false-ONLINE rates included",
            s50="the v1 180/180 failure history is preserved (C2_CAMERA_HEALTH_REPAIR_REPORT.md); "
                "v1.1 is additive evidence, not a replacement",
            s67="classical CV benchmark performed first; no neural camera-health model trained",
            s125="no locked component modified; harness + corpus generator only",
            cv2_rng="pinned per sample via cv2.setRNGSeed for RANSAC reproducibility",
        ),
        v1_integrity=v1_int,
        n_samples=len(records),
        n_engine_exceptions=n_exc,
        canonical_results_sha256=digest,
        macro=macro,
        false_online_v11=fo_v11,
        aggregates=aggregates,
        component_tables=comp,
        canonical=canonical,
    )
    raw = json.dumps(out, indent=2, sort_keys=True, default=str).encode("utf-8")
    OUT_PATH.write_bytes(raw)

    agg = aggregates
    print(f"release={RELEASE_NAME} samples={len(records)} wall={out['wall_seconds']}s")
    print(f"manifest_sha256={manifest['manifest_sha256']}")
    print(f"results_sha256={digest}")
    print(f"engine_exceptions={n_exc}")
    print(f"macro precision={macro['precision']} recall={macro['recall']} f1={macro['f1']}")
    print(f"v1_integrity: rebuild_ok={v1_int['v1_manifest_rebuild_ok']} "
          f"disk=rebuilt:{v1_int['v1_manifest_disk_matches_rebuild']} "
          f"v11_prefix=v1:{v1_int['v11_prefix_equals_v1_rows']} "
          f"repair1_engine={v1_int['repair1_engine_subset_match']} "
          f"repair1_full={v1_int['repair1_full_record_subset_match']}")
    for name in ("strict_v11", "broad_v11"):
        b = fo_v11[name]
        print(f"false_online {name}={b['false_online']} ({b['false_online_rate']})")
    print("per-state (precision/recall/f1/support):")
    for st in sorted(agg["per_state"]):
        v = agg["per_state"][st]
        print(f"  {st:10s} p={v['precision']:.4f} r={v['recall']:.4f} "
              f"f1={v['f1']:.4f} n={v['support']}")
    print("per-class:")
    for c in sorted(agg["per_class"]):
        pc = agg["per_class"][c]
        print(f"  {c:24s} n={pc['n']:3d} expected={pc['expected_state']:9s} "
              f"recall={pc['recall_vs_expected']:.2f} online_rate={pc['online_rate']:.2f}")
    print(f"wrote {OUT_PATH.name}")

    if v1_int.get("repair1_available") and v1_int["repair1_full_record_subset_match"] != "180/180":
        raise RuntimeError(
            "v1 subset does not reproduce repair1 record-for-record "
            f"(full={v1_int['repair1_full_record_subset_match']}, "
            f"engine={v1_int['repair1_engine_subset_match']}, "
            f"first_mismatch={v1_int.get('repair1_first_mismatch')}) — "
            "v1.1 results are not a faithful extension of the repaired pipeline"
        )


if __name__ == "__main__":
    main()
