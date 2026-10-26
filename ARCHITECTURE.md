# Ambient Field Lens — Architecture

Companion to the [README](README.md) (setup, disclosure) and
[docs/recalibration-results.md](docs/recalibration-results.md) (evidence).
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

1. **World checks (proven pattern, in build).** Observable, deterministic:
   paper present, pen fitted, drawing footprint inside the paper boundary
   (SAM masks in marker-derived surface coordinates, never raw pixels),
   calibration ready from controller state, current step from the approved
   procedure. Geometry runs per frame from visible markers, so it holds
   from any viewpoint on a moving wearer.
2. **Footing check (pending validation).** Whether a generated step stands
   on retrieved manual text or on model priors. Internal readout directions
   (contrastive baseline now, full Jacobian comparison next) score
   grounded-vs-improvised generation on paired cases: same question, same
   scene, supporting passage present versus removed. The probe contributes
   a vote once validated; it never decides alone, and missing evidence
   blocks regardless of probe output.

## The flywheel

Every ungrounded flag is a documentation gap with a name. Author the
missing passage, re-ingest, and the same question passes grounded. The
demo loop is amber, author, green — each green earned twice. Flags are
candidates: ambiguous or out-of-scope questions also read ungrounded, so a
human promotes flags to missing pages. Human-in-the-loop by design.

## Data flow

```
glasses/phone camera → frame + voice query
  → POST /assist {query, image_jpeg_base64}
  → world checks (geometry, state, procedure step from Chroma Ross corpus)
  → footing score on the generated step (validated directions only)
  → verdict: verified (all pass) | verify (named fault + correction)
  → 600×600 HUD card (green / amber)
```

Retrieval: `ross-manuals-*` Chroma collection, freshly chunked in-repo
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
| SAM mask output end-to-end on tripod frames | Pending (one authorized diagnostic) |
| Paired multi-angle scenes (fault × viewpoint × evidence) | Pending (filming) |
| Grounding direction separates present-vs-removed passages | Pending (CPU analysis on paired set) |
| Full Jacobian vs contrastive comparison | Pending (pre-GPU) |
| Green path on a calibrated subset | Pending (requires all above) |

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
dependency in this implementation. The first-card <3s goal has not been measured
against the planned multimodal/GPU pipeline. Request/processing limits are
bounded failure handling, not an end-to-end latency guarantee.

Phase 3 needs an explicitly reviewed server-owned calibration/evidence contract
before this schema can represent green instructions. A client-provided score,
unvalidated provider text or merely connecting a model cannot enable green.

Conceptual references are the disclosed Flotilla fail-closed validation and
cooldown patterns. This implementation was written in this repository during
the event; no Flotilla code was vendored. No code/data was copied from
`ambient-field-lens-test`, Canis matrices or Sovereign Mind chunkers.
