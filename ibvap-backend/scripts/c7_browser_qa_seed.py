#!/usr/bin/env python
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — Browser QA seed (Task #18, §43/§44/§51)
#
# Seeds a handful of sightings into a RUNNING backend (default :8000) via the
# real internal ingest API so the Vehicle Intelligence UI can be exercised in a
# browser with realistic rows: valid/possible/partial/unreadable reads,
# multi-camera visits of one plate, ranked candidates, and one no-plate case.
#
# The target DB is a COPY of the E2E DB (tests/test_dbs/c7_browser_qa_run.db);
# the E2E evidence DB itself is not touched.
#
# Usage:
#   python scripts/c7_browser_qa_seed.py            # seed http://127.0.0.1:8000
#   python scripts/c7_browser_qa_seed.py --base http://127.0.0.1:8000
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import argparse
import asyncio
import sys

import httpx

HEADER = {"X-Internal-Service": "browser-qa-seed"}

CAM_1 = "CAM-E2E-C7-01"   # existing E2E camera (SGT-C7E2E-0001 lives here)
CAM_2 = "CAM-BQA-02"
CAM_3 = "CAM-BQA-03"


def sighting(
    sighting_id: str,
    observed_at: str,
    *,
    vehicle_class: str,
    vehicle_color: str,
    direction: str,
    plate: dict | None = None,
) -> dict:
    item: dict = {
        "observed_at": observed_at,
        "sighting_id": sighting_id,
        "vehicle_class": vehicle_class,
        "vehicle_color": vehicle_color,
        "vehicle_direction": direction,
    }
    if plate is not None:
        item["plateRead"] = plate
    return item


def plate(
    raw: str,
    display: str,
    confidence: float,
    quality: str,
    format_status: str,
    observed_at: str,
    *,
    normalized: str | None = None,
    candidates: list[dict] | None = None,
) -> dict:
    p: dict = {
        "raw_read": raw,
        "normalized_read": normalized,
        "display_read": display,
        "confidence": confidence,
        "quality": quality,
        "format_status": format_status,
        "observed_at": observed_at,
    }
    if candidates:
        p["candidates"] = candidates
    return p


def cand(rank: int, raw: str, confidence: float, format_status: str,
         normalized: str | None = None) -> dict:
    c: dict = {"rank": rank, "raw_read": raw, "confidence": confidence,
               "format_status": format_status}
    if normalized is not None:
        c["normalized_read"] = normalized
    return c


BATCHES: list[tuple[str, list[dict]]] = [
    # ── CAM-1 (E2E camera): two more visits of the tracked plate ────────────
    (CAM_1, [
        sighting(
            "SGT-BQA-0002", "2026-09-29T00:12:00+00:00",
            vehicle_class="CAR", vehicle_color="WHITE", direction="OUTBOUND",
            plate=plate(
                "PB10C7E2OO1", "PB10C7E2001", 0.88, "HIGH", "VALID_FORMAT",
                "2026-09-29T00:12:00+00:00", normalized="PB10C7E2001",
                candidates=[
                    cand(1, "PB10C7E2OO1", 0.55, "POSSIBLE_FORMAT",
                         normalized="PB10C7E2001"),
                    cand(2, "PB1OC7E2001", 0.32, "POSSIBLE_FORMAT"),
                ],
            ),
        ),
        sighting(
            "SGT-BQA-0003", "2026-09-29T00:47:00+00:00",
            vehicle_class="CAR", vehicle_color="WHITE", direction="INBOUND",
            plate=plate(
                "PB10C7E2001", "PB10C7E2001", 0.91, "HIGH", "VALID_FORMAT",
                "2026-09-29T00:47:00+00:00", normalized="PB10C7E2001",
            ),
        ),
    ]),
    # ── CAM-2: mixed classes and read qualities ─────────────────────────────
    (CAM_2, [
        sighting(
            "SGT-BQA-0101", "2026-09-29T00:20:00+00:00",
            vehicle_class="TRUCK", vehicle_color="RED", direction="INBOUND",
            plate=plate(
                "HR26DK44O1", "HR26DK4401", 0.87, "HIGH", "VALID_FORMAT",
                "2026-09-29T00:20:00+00:00", normalized="HR26DK4401",
            ),
        ),
        sighting(
            "SGT-BQA-0102", "2026-09-29T00:33:00+00:00",
            vehicle_class="CAR", vehicle_color="BLUE", direction="OUTBOUND",
            plate=plate(
                "DL01AB1234", "DL01AB1234", 0.68, "MEDIUM", "POSSIBLE_FORMAT",
                "2026-09-29T00:33:00+00:00", normalized="DL01AB1234",
            ),
        ),
        sighting(
            "SGT-BQA-0103", "2026-09-29T00:41:00+00:00",
            vehicle_class="MOTORCYCLE", vehicle_color="BLACK", direction="INBOUND",
            plate=plate(
                "KA05M", "KA05M", 0.42, "PARTIAL", "NOT_ENOUGH_DATA",
                "2026-09-29T00:41:00+00:00",
            ),
        ),
        sighting(
            "SGT-BQA-0104", "2026-09-29T00:52:00+00:00",
            vehicle_class="CAR", vehicle_color="SILVER", direction="UNKNOWN",
            plate=plate(
                "IIIIIIII", "IIIIIIII", 0.05, "UNREADABLE", "INVALID_FORMAT",
                "2026-09-29T00:52:00+00:00",
            ),
        ),
        sighting(
            "SGT-BQA-0105", "2026-09-29T01:03:00+00:00",
            vehicle_class="BUS", vehicle_color="YELLOW", direction="INBOUND",
            plate=plate(
                "MH12ABOOO9", "MH12AB0009", 0.77, "MEDIUM", "VALID_FORMAT",
                "2026-09-29T01:03:00+00:00", normalized="MH12AB0009",
                candidates=[
                    cand(1, "MH12AB0009", 0.77, "VALID_FORMAT",
                         normalized="MH12AB0009"),
                    cand(2, "MH12AB0090", 0.41, "POSSIBLE_FORMAT"),
                ],
            ),
        ),
    ]),
    # ── CAM-3: cross-camera history + wrong-ranking + no-plate ──────────────
    (CAM_3, [
        sighting(
            "SGT-BQA-0201", "2026-09-29T00:26:00+00:00",
            vehicle_class="CAR", vehicle_color="GREEN", direction="INBOUND",
            plate=plate(
                "GJ05X99OO2", "GJ05X9902", 0.52, "MEDIUM", "VALID_FORMAT",
                "2026-09-29T00:26:00+00:00", normalized="GJ05X9902",
                candidates=[
                    # rank order preserved even though rank 2 has higher raw
                    # confidence (§48 wrong_candidate_ranking case)
                    cand(1, "GJ05X99O02", 0.52, "POSSIBLE_FORMAT"),
                    cand(2, "GJ05X990O2", 0.71, "POSSIBLE_FORMAT"),
                ],
            ),
        ),
        sighting(
            "SGT-BQA-0202", "2026-09-29T00:58:00+00:00",
            vehicle_class="CAR", vehicle_color="BLACK", direction="OUTBOUND",
            plate=plate(
                "PB10C7E2001", "PB10C7E2001", 0.83, "HIGH", "VALID_FORMAT",
                "2026-09-29T00:58:00+00:00", normalized="PB10C7E2001",
            ),
        ),
        sighting(
            "SGT-BQA-0203", "2026-09-29T01:05:00+00:00",
            vehicle_class="VAN", vehicle_color="WHITE", direction="INBOUND",
            plate=None,  # no plate read at all
        ),
    ]),
]


async def main(base: str) -> int:
    failures: list[str] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for camera_id, sightings in BATCHES:
            for s in sightings:
                s["camera_id"] = camera_id
            r = await client.post(
                f"{base}/api/v1/anpr/internal/observe",
                headers=HEADER,
                json={"camera_id": camera_id, "source": "LIVE", "sightings": sightings},
            )
            if r.status_code != 200:
                failures.append(f"{camera_id}: HTTP {r.status_code}: {r.text[:300]}")
                continue
            data = r.json()
            print(f"{camera_id}: created={data.get('created')} "
                  f"duplicates={data.get('duplicates')} "
                  f"errors={data.get('errors')}")
        r = await client.get(f"{base}/api/v1/anpr/summary")
        print("summary:", r.json() if r.status_code == 200 else f"HTTP {r.status_code}")

    if failures:
        for f in failures:
            print("FAIL:", f)
        return 1
    print("SEED_OK")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.base)))
