# C5 — Model License Audit (spec §6)

**Project:** PRHAAR — SSB AI-Powered Border Surveillance & Command Platform
**Component:** C5 — Production Object Detection
**Spec traceability:** §6 (license check before final freeze), §67 execution order step 3
**Date:** 2026-10-03
**Method:** local package-metadata verification on the working machine + upstream license
pages checked on the retrieval date. **Not legal advice.**

> §6 rule honored here: *"do not silently assume that an Ultralytics-based implementation
> is automatically suitable for every final deployment context."* This audit records the
> facts of that context explicitly and carries the licensing decision as an OPEN item —
> it is not resolved silently in either direction.

---

## 1. Candidate model licensing (§6 required fields)

Required record per candidate: *model · software license · model/checkpoint terms ·
commercial-use restrictions · redistribution restrictions · dependency licensing.*

### 1.1 YOLO26s / YOLO26m / YOLO26l (ultralytics implementation)

| Field | Record |
|---|---|
| Model | YOLO26 (COCO-pretrained lineage for transfer-learning init; see §4) |
| Software license | **AGPL-3.0** — locally verified 2026-10-03: `ultralytics-8.4.118.dist-info/METADATA` line `License: AGPL-3.0`; full AGPL v3 text present in `dist-info/licenses/LICENSE`. Model YAML configs themselves carry the header `# Ultralytics 🚀 AGPL-3.0 License` (read from `cfg/models/26/yolo26.yaml`). |
| Model / checkpoint terms | Per Ultralytics licensing page (retrieved 2026-10-03): the Ultralytics license scheme covers **"source, models, weights, SAHI, trackers"** — i.e., checkpoints are inside the same license umbrella, not a separate asset class. Any weights PRHAAR *trains itself* are derivatives/uses of the AGPL software; the enterprise option covers the commercial path. |
| Commercial-use restrictions | AGPL path: commercial use is permitted **only with copyleft compliance**. Proprietary/closed use requires the **Ultralytics Enterprise License**. Additionally — see §2 (Responsible Use Policy) — the law-enforcement / military context of PRHAAR is governed by a separate approval requirement per Ultralytics policy language. |
| Redistribution restrictions | AGPL-3.0 conditions apply (license text + copyright notices retained; source availability for the combined derivative — including network service per §13-style obligation; see §2). |
| Dependency licensing | See §3 — the inference path's only copyleft dependencies are `ultralytics` and `ultralytics-thop`. |

### 1.2 RT-DETR-l via the ultralytics implementation (benchmark candidate)

| Field | Record |
|---|---|
| Model | RT-DETR-l (ultralytics hybrid transformer implementation, HGNetv2 backbone) |
| Software license | **Identical surface to §1.1** — same package, same AGPL-3.0; `cfg/models/rt-detr/rtdetr-l.yaml` carries the AGPL header. Benchmarking under ultralytics carries the same AGPL/Enterprise analysis. |
| Model / checkpoint terms, commercial, redistribution | Same as §1.1. |

### 1.3 RT-DETR — original implementation (license-diverse alternative path)

| Field | Record |
|---|---|
| Model | RT-DETR (official implementation, `lyuwenyu/RT-DETR`) |
| Software license | **Apache-2.0** — verified 2026-10-03 by fetching the repository `LICENSE` file directly (standard Apache-2.0 text; placeholder copyright line, no contrary terms found). |
| Model / checkpoint terms | No separate checkpoint-license document was located in this audit; checkpoints are published from the same repository domain. Recorded as **"covered by repo license unless separate terms found — re-verify at download time"** under the acquisition protocol (Phase 1 audit §4). |
| Commercial-use restrictions | Permissive — no copyleft, no per-seat restriction identified. |
| Redistribution restrictions | Apache-2.0 (retain license and NOTICE). |
| Dependency licensing | Same permissive Python stack (§3) minus the AGPL packages; training/eval tooling is separate from ultralytics (pipeline cost noted — an integration cost, not a license cost). |

**Benchmark implication (recorded, not decided):** the RT-DETR family is the only
candidate with a genuinely permissive implementation path. If the licensing decision
(§5) resolves against AGPL *and* against the Enterprise option, the Apache-2.0
implementation is the fallback — its selection would then depend on measured #32
results (spec §5: no winner before measured evaluation).

## 2. Deployment-context analysis (the explicit non-assumption unit)

PRHAAR context (project facts): SSB border surveillance & command platform;
detection results served over a network API; law-enforcement / government use context;
the C5 detector itself emits **no identity information** (spec §55), but the platform
context is a surveillance context.

Three documented facts bear on the AGPL/Enterprise decision:

1. **AGPL network obligation.** The Ultralytics AGPL terms page (retrieved 2026-10-03)
   describes the network obligation in substance: *"public use of a modified version, on
   a publicly accessible server, gives the public access to the source code."* Implication:
   if PRHAAR ships ultralytics-derived inference inside its served AI boundary, the
   AGPL source-availability obligation needs to be evaluated for that boundary — it is
   not automatically satisfied or waived.

2. **Responsible Use Policy — §4.2 "Enhanced Governance Usage".** The policy (retrieved
   2026-10-03) places military/defense- and law-enforcement-context uses in an
   *approval-required* category, quoted: *"The following use cases are not automatically
   prohibited and instead require review and approval prior to contract... Military and
   defense-related applications; Law enforcement use involving identification or tracking
   of individuals;"* and states: *"This Policy applies to all Ultralytics technology,
   however obtained:"* — meaning the policy is asserted to apply regardless of how the
   technology was acquired (e.g., even via the AGPL path).
   The policy separately addresses *"Surveillance, monitoring or facial recognition used
   for repression or unlawful targeting"* with a qualification — surveillance as such is
   not per se the clause; the qualifier is repression/unlawful targeting. (Section
   heading of that clause was not captured in this audit — re-verify at freeze.)
   **Recorded implication:** PRHAAR's final deployment context is named in the
   approval-required category per Ultralytics' own policy text; this is a real gate on
   the final deployment decision, separate from the AGPL question.

3. **PRHAAR's own license position is undeclared.** No `LICENSE`/`COPYING` file was
   found at the repository root or under `ibvap-backend/`, `ibvap-frontend/`, `ml/`
   (search 2026-10-03). AGPL obligations depend on how the combined work is
   distributed/offered; the project should declare its position before the freeze so
   the copyleft analysis has a defined object.

## 3. Dependency licensing — C5 inference path (all verified locally 2026-10-03)

Verification = license field read from installed package metadata or license file on
this machine (not from upstream docs).

| Dependency | Version (installed) | License (local verification) | Impact |
|---|---|---|---|
| **ultralytics** | 8.4.118 | **AGPL-3.0** (METADATA + full LICENSE text) | **Copyleft — the decision item** |
| **ultralytics-thop** | 2.1.6 | **AGPL-3.0** (METADATA) | Copyleft (same umbrella) |
| torch | 2.5.1+cu121 | BSD-3-Clause (METADATA) | Permissive |
| torchvision | 0.20.1+cu121 | BSD (METADATA) | Permissive |
| numpy | 2.4.6 | BSD-3-Clause (license file read) | Permissive |
| opencv-python | 5.0.0.93 | Apache 2.0 (METADATA) | Permissive |
| onnx | 1.22.0 | Apache-2.0 (license file read) | Permissive (export path) |
| onnxruntime | 1.29.0 | MIT (METADATA) | Permissive (export path) |
| pillow | 12.3.0 | PIL/HPND (license file read) | Permissive |
| pandas | 3.0.5 | BSD-3-Clause (METADATA) | Permissive (analysis) |
| scipy | 1.17.1 | BSD-3-Clause (METADATA text) | Permissive (analysis) |
| matplotlib | 3.11.1 | Matplotlib license (PSF-derived) (METADATA) | Permissive (analysis) |
| PyYAML | 6.0.3 | MIT (license file read) | Permissive |
| **tensorrt** | *absent locally* | NVIDIA proprietary SDK terms (EULA) | Only relevant if the TensorRT export path is chosen (#34/#35): per-machine engine build, redistribution restrictions — recorded as a future decision, not audited to conclusion |
| CUDA/cuDNN runtime | via torch cu121 wheels | NVIDIA proprietary EULA (redistributable components within wheels) | Deployment-packaging note for #35/#43 |
| Python | 3.11 | PSF | Permissive |

**Net position:** every dependency on the C5 inference path is permissive **except the
two AGPL packages** (`ultralytics`, `ultralytics-thop`) — they are the sole reason the
licensing decision exists.

## 4. Data lineage note (cross-ref, not duplicated here)

COCO-pretrained checkpoints are used as transfer-learning initialization only
(lineage, not redistribution) — Phase 1 audit `ml/reports/00_license_audit.md` row 1.
Dataset licensing for PRHAAR-C5-DETECTION is governed by that audit's
acquisition-time verification protocol and is finalized in task #30.

## 5. Decision record (carried from Phase 1, deepened here)

**Item:** How does PRHAAR license its final C5 deployment given ultralytics = AGPL-3.0?

| Option | What it requires | Verified facts bearing on it |
|---|---|---|
| (a) AGPL-compliant AI-service boundary | Publish corresponding source for the modified/combined service under AGPL; carry notices | Project currently declares no license (§2.3); network clause applies to a publicly accessible server (§2.1) |
| (b) Ultralytics Enterprise License | Commercial license; removes AGPL disclosure need | License page states coverage of source/models/weights/SAHI/trackers (§1.1); RUP §4.2 approval process additionally applies to the deployment context (§2.2) |
| (c) Apache-2.0 RT-DETR path | Use the original implementation; integration/tooling cost; selection depends on measured #32 results | Apache-2.0 verified (§1.3); spec §5 forbids pre-declaring a winner |
| (d) Defer to freeze | Continue benchmark under ultralytics; resolve before export/integration | Benchmark training/evaluation redistributes nothing; the freeze gate is #34–#36 |

**Status: OPEN.** Per Phase 1 audit §3 and spec §6: **no production-candidate claim for
C5 until this is resolved.** Task #32 (training/benchmark) may proceed under the
ultralytics stack because evaluation does not redistribute the software; the resolution
is required before the §35 integration/export and #36 production-candidate gate.

## 6. Non-claims

- This audit is **not legal advice**; it records verifiable facts and their retrieval
  dates so a qualified decision can be made.
- All upstream-page facts are dated 2026-10-03 and must be **re-verified at the freeze**
  (license pages can change).
- Nothing here claims SSB validation, field certification, or production readiness.
- No model accuracy or suitability claim is made in this document.

## 7. Sources (retrieved 2026-10-03)

- Local machine (authoritative for installed-version facts): package metadata + license
  files under `C:\Users\harsh\AppData\Local\Programs\Python\Python311\Lib\site-packages`
- https://www.ultralytics.com/license — licensing scheme, Enterprise coverage
- https://www.ultralytics.com/legal/agpl-3-0-software-license — AGPL terms summary
- https://www.ultralytics.com/legal/responsible-responsible-use-policy — §4.2 Enhanced
  Governance Usage; "applies to all Ultralytics technology, however obtained"
- https://github.com/lyuwenyu/RT-DETR (raw `LICENSE`) — Apache-2.0 (official RT-DETR)
- Phase 1 audit: `C:\SIH\ml\reports\00_license_audit.md` (dataset licensing + §3 open item)
