#!/usr/bin/env python
"""
PRHAAR C5 -- canonical detection taxonomy (spec section 7), single source of truth.

Taxonomy v1.0 (fine classes):
    PERSON, MOTORCYCLE, BICYCLE, CAR, LIGHT_VEHICLE, TRUCK, BUS, TRACTOR, ANIMAL
    + AUTO_RICKSHAW (conditional: spec 7 marks it conditional on dataset support)

Every conversion script imports this module so class indices are identical
across all sources. Do not renumber: indices are baked into written YOLO label
files; changing order invalidates existing labels. Bump the version on change.

NOTE: acquire_openimages.py embeds a frozen copy of the OI mapping (it ran
before this module existed; artifacts already reference its naming). Further
edits there are avoided to keep acquisition determinism. This file is the
authority for CONVERSION and downstream.
"""

from __future__ import annotations

PRHAAR_C5_TAXONOMY_VERSION = "1.0"

# Order matters. AUTO_RICKSHAW appended last (conditional class, spec 7).
CLASSES: list[str] = [
    "PERSON",          # 0
    "MOTORCYCLE",      # 1
    "BICYCLE",         # 2
    "CAR",             # 3
    "LIGHT_VEHICLE",   # 4
    "TRUCK",           # 5
    "BUS",             # 6
    "TRACTOR",         # 7
    "ANIMAL",          # 8
    "AUTO_RICKSHAW",   # 9 (conditional on sufficient data)
]

CLASS_INDEX: dict[str, int] = {c: i for i, c in enumerate(CLASSES)}

# Classes whose inclusion in a training run is conditional / must be declared
# in the experiment log and model card. Kept explicit, never silent.
CONDITIONAL_CLASSES: dict[str, str] = {
    "AUTO_RICKSHAW": "spec 7: only with sufficient data (measured seed 3,504 boxes: Poribohon cng+easybike 2,696 + Kaggle set 808)",
    "TRACTOR": "zero license-clean public sources as of 2026-10-04 (OI lacks it; Poribohon has no tractor class; DataCluster sets blocked)",
}

# Open Images V7 boxable class -> canonical (frozen copy of the acquisition
# script's TARGET_CLASSES; verified identical 2026-10-04).
OI_TO_CANONICAL: dict[str, str] = {
    "Person": "PERSON",
    "Bicycle": "BICYCLE",
    "Car": "CAR",
    "Motorcycle": "MOTORCYCLE",
    "Bus": "BUS",
    "Truck": "TRUCK",
    "Van": "LIGHT_VEHICLE",
    "Cattle": "ANIMAL",
    "Sheep": "ANIMAL",
    "Goat": "ANIMAL",
    "Horse": "ANIMAL",
    "Dog": "ANIMAL",
}

if __name__ == "__main__":
    print(f"PRHAAR C5 taxonomy v{PRHAAR_C5_TAXONOMY_VERSION}")
    for name, idx in CLASS_INDEX.items():
        cond = CONDITIONAL_CLASSES.get(name)
        print(f"  {idx:2d}  {name:<15} {'[conditional] ' + cond if cond else ''}")
