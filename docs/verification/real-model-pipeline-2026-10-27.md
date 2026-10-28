# Actual Meta scene observations and joined CPU pipeline

Miguel explicitly authorized Meta API calls after clarifying they are separate
from Modal GPU work. Modal remains off. The Reolink paper fixture is frozen;
there is no further physical marker work in this round.

## Implemented

`readiness.pipeline` joins provenance-bound model observations and SAM masks
into six raw checks. Duplicate/mismatched envelopes reject aggregate input.
Multiple legitimate SAM objects remain ambiguous for that role; they do not
erase separate valid presence observations. No highest-score/largest-mask
selection. A current-frame visible not-fitted observation fails fitment even
when there is no pen mask: an empty holder need not produce a pen region.
A positive fitment pass still requires the separately identified pen mask.

Historical component checks are explicitly separate from readiness freshness.
Archive clocks are never refreshed. The replay runner always returns amber,
null step, live-ready false: controller/procedure/footing integrations remain
separate, and `/assist` is unchanged. No product green path was added.

The local manifest runner consumes exact original image/request/receipt/response
artifacts, validates their hashes/context and supports saved SAM streams and
Spark JSON. Corrupt or incomplete envelopes fail without paid repair retries.
Opaque encrypted reasoning output is preserved by response digest, never read
as observation text. Exact non-streaming request options are bound to receipts.

## Actual provider results

Same neutral prompt on every image; no reference labels in provider requests.
All six completed Spark responses pass strict local schema/identity validation.

| Scene | Observable pen/holder presence | Model fitment observation | SAM pen candidates |
| --- | --- | --- | --- |
| S04 missing pen | unknown: pen unresolved, holder visible | not fitted | 0 |
| S27 clear before | pass | fitted | 2, ambiguous |
| S27 covered | unknown: holder unresolved | not observable | 1 |
| S27 clear after | pass | fitted | 2, ambiguous |
| S28 before displacement | pass | fitted | 2, ambiguous |
| S30 paper displaced | pass | fitted | 2, ambiguous |

The missing-pen scene has a negative fitment result, but Spark did **not** label
pen absence as clear: preserve that distinction. The covered scene is blocked
as unknown, not falsely promoted to pass and not relabelled as a correctly
detected occlusion FAIL. The reference/recognizer disagreement is retained.
S30 presence does not imply containment: intended pen/tool can be visible and
fitted while the surface is misplaced. No containment result is inferred.

SAM `graph paper` returned zero matches on six frames; `pen` returned the counts
above. The separate `paper` prompt probe returned eight mask tokens/candidates;
the more specific `sheet of paper under the robot arm` probe returned zero.
These are separate logged experiments, not automatic retry loops. No candidate
was selected to manufacture paper presence. Target association is the next
algorithm problem; moving/redrawing the sheet does not solve it.

All fourteen SAM calls completed HTTP200. Seven Spark calls: first default-
reasoning request exhausted2048tokens (2046reasoning) without JSON; it remains
an incomplete result. A deliberate low-reasoning smoke request completed, then
the remaining five scenes completed with the same revised prompt/options.
One captured snapshot used `captured_at_utc` rather than clip-start metadata;
the runner now validates both clock forms before any paid request. That local
metadata failure sent no request and caused no paid duplicate. An opaque
reasoning-envelope compatibility fix was validated against the saved response
without another provider call.

## Evidence, cost and reproduction

- [Joined six-scene raw pipeline metadata](real-observation-pipeline-2026-10-27.json)
- [Actual reported usage and conservative cost calculation](meta-observation-usage-2026-10-27.json)
- [Prepared label-blind six-frame request plan](model-observation-batch-review-2026-10-27.json)

Raw images, exact requests, responses (including encrypted reasoning), receipts
and executable replay manifests stay private in Movies. The private visual
overview is `~/Movies/Ambient-Field-Lens/2026-10-27/drawing-readiness/model-observation-review.html`.
It references existing photos without duplicating media.

Published rates applied to actual usage yield an estimated **$0.0743445**:
Spark$0.0393445 with conservative uncached input pricing, SAM$0.035 for14stills.
This is an estimate, not an invoice. Pricing source checked27October:
[Meta pricing](https://dev.meta.ai/docs/pricing-rate-limits).
The executor preflights the conservative full-context cost plus existing
research reservations against$20, records attempts before sending, does not
retry automatically, and never imports/starts Modal.

**107 tests pass**, including seven private S03 integrations, mock-only paid
execution boundaries, stale/mismatched evidence, duplicate/ambiguous candidates,
negative fitment without a pen mask, and the existing19backend regressions.
Separate actual six-scene replay completed without adapter errors; historical
readiness stays unknown/amber. No autonomous accuracy or viewpoint-invariance
claim follows from this small batch.

```sh
AFL_S03_DIAGNOSTIC_DIR="$HOME/Movies/Ambient-Field-Lens/2026-10-26/drawing-readiness/sam-diagnostic-01" \
  PYTHONPATH=backend python -m unittest discover -s backend/tests -q
PYTHONPATH=backend python tools/run_observation_pipeline.py \
  --manifest /private/path/to/joined-scene.json --output /tmp/replay.json
```

Provider integration references: [image inputs](https://dev.meta.ai/docs/image-understanding),
[reasoning](https://dev.meta.ai/docs/reasoning),
[Responses schema](https://dev.meta.ai/docs/api-reference/responses/schemas).
No guessed schema-constrained Responses parameter was used; strict schema
validation is local. The full Jacobian/grounding comparison remains pending
and no Modal/GPU window is authorized by these Meta calls.
