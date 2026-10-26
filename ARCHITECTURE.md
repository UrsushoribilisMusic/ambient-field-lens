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
