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
