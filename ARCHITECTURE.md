# Ambient Field Lens — Architecture (as built)

Companion to the [README](README.md). Status markings are load-bearing:
**proven** means measured in-repo or on camera, **pending** means hypothesized
with a defined validation.

## Product

A safety-gated wearable assistant for machine setup. The operator frames the
machine with the phone (standing in for glasses; designed for Ray-Ban
Display, no Display hardware on the team) and asks task questions like "Can I
draw this here?" The system answers amber cards with evidence and corrections.
Green has a fixed definition — world checks pass AND the step is grounded AND
nothing is missing — and no path in the system can emit it today.

## The live path (proven on camera)

```
phone capture → POST /assist → window/token admission → Ross retrieval
→ SAM paper candidates → Glimmer prefill readout → amber denial w/ evidence
```

- `backend/live_backend.py`: composition. Reuses `contracts` (verdict is
  type-level `Literal['verify']`, score pinned 0.0) and the circuit breaker
  untouched; does not reuse the stub `AssistService`.
- Admission is finite: 600 s windows, 4 single-use token calls, claim-first,
  pop-atomic, never refilled, single container, single-flight semaphore, slot
  held until timed-out workers drain, no new paid stage after abandonment.
- Fail-closed: any provider failure, missing/expired/spent/replaced window,
  or timeout returns an amber denial — never a step, never provider text.
- Prefix contract (`docs/live-assist-wiring.md`): detail strings carry
  `Live check (amber)` / `WORLD CHECK FAILED` / `NOT COVERED` prefixes the
  phone parses into WORLD / COV chips. Only real failures earn color.
- Coverage is a threshold on top-chunk retrieval distance
  (`COVERAGE_DISTANCE_MAX`, None until the Q1 labelling freezes it). The
  provider raises on empty, so emptiness never reaches composition.

## The two gates (as filmed)

- WORLD: paper mask found or not (autonomous SAM candidates; ambiguous by
  design, never presence/fitment/approval by themselves).
- COVERAGE: manual passage close enough or not (validated cutoff pending;
  until then covered-but-uncalibrated).

## What the receipt proves (narration-locked)

Which exact frame, question, passage, and masks went into an answer — each
bound by hash. Never when the photo was taken: a photograph from yesterday
passes every check on the card.

## Explicitly not built

- Green steps, red blocks, machine instructions, capture-clock binding
  (wire carries no sensor timestamp), validated geometry (markers and
  measurements pending), pen contact (presence wired provider-side, not live).
- Weight readouts in the verdict. Four negative results: contrastive probe
  test AUROC 0.575; Jacobian lens 0.861 vs plain 0.889 (no advantage);
  trajectory retired (no added value); live prefill −0.018 supported vs
  −0.015 absurd (no separation). Groundedness is a system property here.

## Spend model

Windows cost nothing to open. Per framed call: ~15–90 s Modal GPU/CPU
(grant) + one Meta SAM decode (billing card, fractions of a cent).
Baseten credits cover the offline wording lane only. Ledger: GPU attempts
with exact scores in `close_window`; Modal dashboard is final on charges.


## Offline teacher-forced trajectory comparison

`backend/recal/trajectory_window.py` captures all candidate-token residuals in
one causal pass per frozen record. Pure CPU analysis selects predefined points
and layers using validation only. Results and the true pre-candidate control
are in `docs/verification/trajectory-comparison-2026-10-28.md`: both score1.000
on this tiny test, so extra trajectory scoring adds no demonstrated value.
This remains an offline research unit, not a live generation or /assist adapter.


## Frozen-label wording robustness

`backend/recal/expanded_window.py` is a separate offline experiment, not a live
readiness adapter. It inherits only exact candidate/context/frame combinations
from Miguel's frozen label review and keeps novel wording separate from old
controls. Fixed layers and fit-only estimators score actual pre-candidate inputs.
Results: hidden AUROC1.000, norm/head lens0.970486 on24 new wording pairs; still
only two independent held-out topics, no grounding or Jacobian-advantage claim.
See `docs/verification/heldout-wording-results-2026-10-28.md`.


## Image-only pair authoring and human review

`tools/prepare_visual_pair_review.py` derives native crops and provenance from
archived footage, without filming, model/provider requests or new predictions.
`tools/render_visual_pair_review.py` makes the local independent-label form.
`backend/recal/visual_review.py` rejects missing/unknown/manual-answerable
pairs, changed digests and capture-family fold leakage. No scoring or GPU path
is implemented here; even validated human labels only enable later planning.
The supplied image-space footprint is a separate reference target, not accepted
robot registration. See `docs/visual-grounding-pair-protocol-2026-10-28.md`.

## Hosted wording generation (offline authoring)

[Generation routing](docs/generation-routing.md) defaults pair phrasings, step
text and review copy to Baseten `meta-models/muse-spark-open-1026`, with explicit
Meta overflow. Runtime vault credentials, private exact receipts and a shared
per-call hosted-API ledger; missing usage is unknown, not zero. This authoring
tool does not change frozen labels, scoring, SAM, `/assist` or GPU windows. SAM
stays on Meta; probes and all internal-state readouts stay on Modal Glimmer.

## Live demo providers (28 October integration)

`backend/providers/` supplies deployed Ross Chroma retrieval, Meta SAM current-frame
mask decoding, and Modal Glimmer frozen layer27 true-prefill scoring. Calls carry
frame/context/source hashes and private receipts; GPU admission is window-bound,
max1 worker, scale-to-zero, with grant reservations. Signed containment clearance
uses measured mm errors and reading uncertainty rather than an inherited2px cutoff.
The real displaced-paper phone control is still required before shipment. Muse
owns the reviewed `/assist` admission contract and iOS integration; provider raw
scores alone never authorize a step. [Interfaces, proof and remaining integration
requirements](docs/live-provider-handoff.md).

## Observable refusals and controller binding — 29 October

[Runtime handoff](docs/observable-checks-handoff.md): Spark pen presence is a
separate, provenance-bound check (not contact or mechanical fitment). Measured
geometry requires fixed coplanar workspace markers and independently measured
robot linkage; moving-paper marks cannot anchor a fixed robot footprint.
Corrections are numeric geometry or exact retrieved passages only. Controller
file/flag/log/process snapshots remain unverified without tool/surface/session
binding; Mac-side collection and authenticated CPU transport are distinct from
container state. All current responses remain amber with no step. The
[RED extension](docs/proposals/red-controller-contract.md) is a proposal only.
No validated weight signal currently supplies a permission gate; raw Glimmer
scores are diagnostic. No new score rounds or GPU windows in this work.

## Versioned documentation repair (Codi, merged as PR #16)

The CPU-only export bridge in `providers/corpus_repair.py` stages one exact,
human-reviewed SM wiki passage into a new fingerprint-named collection in a
separate DB. The original 38-record collection and report remain unchanged.
`providers/corpus-pins.json` binds explicit name/count/full fingerprint/report
and full text+metadata+vector digest. Retrieval rejects anything outside that
reviewed registry; IAM-only `select_corpus` validates before atomic activation
or rollback. No threshold/verdict/green changes. A new 39-record pin cannot be
reviewed or activated until Miguel's actual passage exists. See
[repair filming and rollback handoff](docs/documentation-repair-handoff.md).
