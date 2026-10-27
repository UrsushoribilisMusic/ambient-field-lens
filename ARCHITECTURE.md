# Ambient Field Lens — Architecture

Companion to the [README](README.md) (setup, disclosure) and
[drawing-readiness status](docs/drawing-readiness-progress.md) and
[research evidence in PR #2](https://github.com/UrsushoribilisMusic/ambient-field-lens/blob/e577261/docs/recalibration-results.md).
Status markings are load-bearing: **proven** means measured in-repo,
**pending** means hypothesized with a defined validation.

## Product

A safety-gated wearable assistant for machine setup. The operator looks at
the machine through smart glasses (phone camera as oriented mock feed during
development; designed for Ray-Ban Display) and asks task questions like
"Can I draw this here?" The system answers with HUD cards: green means the
step earned it, amber names the fault and its correction.

## The two gates

Green has a fixed definition: **the world checks pass AND the generated
step is grounded AND nothing is missing.** Amber fires on any failure and
says which one. The backend default-denies; thresholds are never tuned to
produce green.

1. **World checks (CPU functions tested; physical validation pending).** Observable, deterministic:
   paper present, pen fitted, drawing footprint inside the paper boundary
   (SAM masks in marker-derived surface coordinates, never raw pixels),
   calibration ready from controller state, current step from the approved
   procedure. The intended wearable implementation derives geometry per frame
   from visible markers. Marker detection/tracking and real camera-to-surface
   registration are not implemented or validated on tonight's captures.
   One fixed viewpoint cannot establish viewpoint invariance. The offline
   homography/containment functions have synthetic CPU tests only.
2. **Footing check (pending validation).** Whether a generated step stands
   on retrieved manual text or on model priors. Internal readout directions
   (contrastive baseline now, full Jacobian comparison next) score
   grounded-vs-improvised generation on paired cases: same question, same
   scene, supporting passage present versus removed. The probe contributes
   a vote once validated; it never decides alone, and missing evidence
   blocks regardless of probe output.

## The flywheel

The intended demo loop is amber, human-confirmed documentation gap, author,
re-ingest, recheck, green. A flag is a candidate gap: ambiguity, out-of-scope
questions or retrieval failure can also produce it. Adding a passage does not
guarantee a grounded result and cannot override a physical fault or missing
evidence. Green still requires both gates to pass. This loop is pending
end-to-end validation. Human-in-the-loop by design.

## Data flow

Target architecture below; the live Phase 1 path still returns amber only.

```
glasses/phone camera → frame + voice query
  → POST /assist {query, image_jpeg_base64}
  → world checks (geometry, state, procedure step from Chroma Ross corpus)
  → footing score on the generated step (validated directions only)
  → verdict: verified (all pass) | verify (named fault + correction)
  → 600×600 HUD card (green / amber)
```

Offline research in unmerged PR #2: `ross-manuals-*` Chroma collection, freshly chunked in-repo
(38 chunks from 10 user-owned docs). Probes: Glimmer 30B prefill
directions from the in-event recalibration. Prior datasets (Canis matrices,
pre-event question sets) are hashed external references only — see README
disclosure; nothing vendored.

## Status

| Claim | State |
| --- | --- |
| Disposition directions separate on Glimmer (OOD AUROC 0.75–1.00) | Proven |
| Confident-minus-uncertain predicts Ross answerability | Refuted (test AUROC 0.57, negative coefficient) |
| Default-deny backend incapable of green steps | Proven (type-level) |
| SAM reachable, accepts frames | Proven |
| SAM mask output on a tripod frame | Proven for one S03 frame: one request, two manually box-prompted masks decoded and visually inspected; not automatic recognition |
| Offline readiness, planar geometry and presence functions | 29 synthetic CPU tests pass; not physical scene validation |
| Scene inventory through 27 October | 45 image assets with verified digests, 3 stream/camera profiles and coarse pose buckets; 8 inventory regressions pass |
| Separate observable pen/holder presence check | Implemented; human-reference replay 27 pass/3 fail/15 unknown. Image-model inputs absent, so actual check output remains unknown on all 45 assets |
| Footprint check over inventoried frames | Executed, unknown on all 45: no accepted physical registration/footprint, paper masks only for S03 diagnostic |
| Measured marker registration | Nine manual v2 readings, corners 1–4 fit / 5–9 validate: RMS2.054px/max2.955px fails2px. Robot linkage remains unknown |
| Observation adapters / composition | Frame-bound provenance and strict archival/live separation; original S03 replay, six checks, presence-fail veto tested. Calibration/procedure adapters pending; no gate wiring |
| Viewpoint invariance | Explicitly untested; multiple uncalibrated views do not prove robustness |
| Paired multi-angle scenes (fault × viewpoint × evidence) | Multiple coarse views captured plus clear/covered/clear S27; complete calibrated fault/evidence grid still pending |
| Grounding direction separates present-vs-removed passages | Pending (CPU analysis on paired set) |
| Full Jacobian vs contrastive comparison | Pending (pre-GPU) |
| Green path on a calibrated subset | Pending (requires all above) |

Tonight's displaced surface is visibly shifted, but geometric containment is
unknown without the requested footprint and registration. The covered holder
cannot satisfy observable presence; that is not proof of physical pen absence.
Raw outputs, reference provenance and unresolved faults are in the
[CPU scene report](docs/verification/scene-batch-2026-10-27.md) and
[machine-readable inventory](docs/verification/scene-batch-2026-10-27.json).
The report is not an image-detector accuracy result. The commanded40×40 mm
physical square was operator-measured45×40 mm, with matching opposite sides;
visual stroke success does not imply metric accuracy. See the
[27 October capture/fix log](docs/drawing-readiness-2026-10-27.md) and
[original checkpoint](docs/drawing-readiness-progress.md).

No new GPU window is authorized until the real paired set is hand-reviewed and
passes its CPU checks. The $20 ceiling remains. The CPU work is isolated on
`codi/drawing-readiness-cpu`, based on current main; it does not require PR #2
to merge. Integration into `/assist` requires a separate review.

## Claims we do not make

No confidence metering (failed proxy, retired). No green by threshold
tuning. No metric registration without markers. No causal steering claims
beyond the lexical proxy already disclosed. A negative result is a result:
both refuted proxies stay documented.

## Backend request path (Phase 1 boundaries)

The clean-room iOS client captures a frame, encodes a JPEG and sends the
existing `query` / `image_jpeg_base64` JSON contract to `POST /assist`. It
renders the four-field verdict response on the HUD. Transport failures
clear the previous HUD verdict (fixed on main); this backend does not
change DAT wiring.

1. `RequestBoundary` permits uncompressed JSON only, enforces a 3 MiB actual-body
   budget (including chunked requests) and a three-second total receive deadline.
2. `AssistRequest` rejects unknown fields, blank/control-character queries,
   queries over 2,000 characters, malformed base64 and invalid/truncated images.
   JPEGs are limited to 2 MiB decoded bytes and 4,194,304 pixels. No image is
   persisted or included in error responses.
3. A missing frame returns amber immediately. Otherwise `AssistService` admits
   at most four calls, with a bounded admission wait and a 2.5-second processing
   deadline. Providers must be asynchronous/nonblocking. Local timeout does not
   claim to cancel external GPU billing; no such provider is configured here.
4. A per-worker circuit opens after three consecutive failures or explicit
   `LowGrounding` results. Thirty seconds later, one half-open probe is allowed.
   Generation-tagged permits prevent late earlier calls from overriding the
   open circuit or the probe. Normal uncalibrated refusals are not failures.
5. The Phase 1 response contract permits only `verify`, null step and zero
   score. It revalidates even preconstructed model objects. Provider detail is
   replaced with application-owned text; neither a green flag nor an instruction
   in the amber detail can bypass the stub. Failures also return an amber
   envelope, with appropriate 4xx/5xx HTTP status and `Cache-Control: no-store`.

## Scope and later work

The breaker is process-local. With several workers, each has its own four-call
budget and breaker; distributed budgets are not implemented. There is no model,
SAM endpoint, Modal deployment, calibration artefact, Chroma client or secret
dependency in the live Phase 1 request path. Separate offline tools capture
private video and perform an explicitly invoked SAM diagnostic; they are not
called by `/assist`. The first-card <3s goal has not been measured
against the planned multimodal/GPU pipeline. Request/processing limits are
bounded failure handling, not an end-to-end latency guarantee.

Phase 3 needs an explicitly reviewed server-owned calibration/evidence contract
before this schema can represent green instructions. A client-provided score,
unvalidated provider text or merely connecting a model cannot enable green.

Conceptual references are the disclosed Flotilla fail-closed validation and
cooldown patterns. This implementation was written in this repository during
the event; no Flotilla code was vendored. No code/data was copied from
`ambient-field-lens-test`, Canis matrices or Sovereign Mind chunkers.
