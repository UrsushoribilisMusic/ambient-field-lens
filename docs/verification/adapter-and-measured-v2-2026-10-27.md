# CPU replay and measured v2 result — 27 October 2026

**Measured paper-plane registration fails the fixed 2 px acceptance bar.**
Maximum held-out error is **2.954858 px**, RMS **2.054368 px**. No readings were
adjusted, no held-out points were added to fitting, and no tolerance was widened.
The result does not establish robot-coordinate registration or GPU eligibility.

## Frozen manual measurement

Source: private `reolink-wide-frame-v2-2026-10-27.jpg`, native 896×512 pixels.
Frame SHA-256: `e652486ba24cfa28bff42725f2f070d52c0cda9aacf7627b5d85ef4a69fd3dda`.
Physical positions come from operator file `markers-2026-10-27.txt`, SHA-256
`c734554d797614b08d23f073c53a4e41e7199e3d65683425c1119dc663c3dc9d`.
The operator reports ruler-verified 5 mm grid spacing and a taped 120×120 mm zone.
Origin is top-left as viewed; x right, y down toward the viewer.

Centres of the green rings were read manually from nearest-neighbour enlarged
crops, converted to original pixels and saved before residual calculation.
Half-pixel notation does not imply subpixel accuracy: blur/thick strokes allow
roughly 1–2 px ambiguity, unquantified. These readings await independent review.
That ambiguity is not permission to adjust a reading to obtain a pass.

| Mark | Paper mm (x, y) | Measured image px (x, y) | Split | Error px |
| --- | --- | --- | --- | --- |
| 1 | 0, 0 | 309, 425.5 | fit | <0.000001 |
| 2 | 120, 0 | 437, 399.5 | fit | <0.000001 |
| 3 | 0, 120 | 355.5, 505 | fit | <0.000001 |
| 4 | 120, 120 | 502.5, 466 | fit | <0.000001 |
| 5 | 55, 120 | 426.5, 488 | validation | 1.959555 |
| 6 | 55, 0 | 373, 413 | validation | 2.443605 |
| 7 | 120, 65 | 468.5, 433 | validation | 1.233750 |
| 8 | 0, 65 | 331, 465 | validation | 1.018698 |
| 9 | 80, 90 | 440, 461 | validation | 2.954858 |

Four exact fit points interpolate; their near-zero error is not validation.
Held-out points 6 and 9 exceed 2 px. Point 5 is close to the limit.
Normalized DLT and the existing acceptance function use the declared split
1–4 / 5–9. [JSON report](v2-reprojection-2026-10-27.json) contains the homography,
all residual components, readings, source hashes and rejection.

Reproduce with private sources available:

```sh
PYTHONPATH=backend python tools/report_measured_registration.py \
  --readings "$HOME/Movies/Ambient-Field-Lens/2026-10-27/drawing-readiness/v2-manual-marker-readings.json" \
  --source-dir "$HOME/Movies/Ambient-Field-Lens/2026-10-27/drawing-readiness" \
  --output /tmp/v2-reprojection.json
```

## Raw scene checks

The inventory now includes **45 frames**, including three operator marker frames.
Only S03 has saved SAM outputs: 12,971 paper pixels and 1,642 pen pixels. They
were decoded again from the original receipt/raw SSE through the new adapter.
No mask is transferred to another frame, stream, camera pose or surface pose.

Actual presence and footprint remain **unknown on all 45 frames**: no structured
pen/holder observations, accepted robot registration or specified bound footprint
are available. Human-reference presence logic is separate: 27 pass / 3 fail /
15 unknown, zero disagreements with existing reference labels. This is not
detector accuracy. Known missing/covered-pen and displaced-surface faults remain
unvalidated by autonomous checks; missing inputs are not successful detections.

S03 archival adaptation preserves original timing. Its frame was
205.630992 seconds old at request time (capture time estimated from clip start
plus representative offset, not a verified sensor clock). Live admission rejects
it; all six evaluations at the original response-completion clock are unknown,
yielding amber. The older timestamp-resetting replay has been replaced with this
archival wrapper. No holder observation or fitment is inferred from pen masks.
The [archival replay metadata](s03-adapter-replay-2026-10-27.json) contains the
six raw results and provenance without source pixels or video.

## Adapter implementation and remaining boundaries

Contract v2 was committed first (`1e1f60b`). Adapters now produce frame-bound
Mask/Observation/Fitment records with provider/response identity, image dimensions
and digest, camera/rig/surface/tool/session, receipt/request/response/prompt
digests, clocks, parsing/role origin and native pixel bounds. Corrupt, mismatched,
ambiguous, stale-live or incomplete evidence is rejected. Archival evidence
cannot be admitted live or have its timestamp refreshed. S03 request digest is
explicitly reconstructed from its saved receipt, not claimed as wire bytes.

Composition requires exactly the six contract checks. Presence FAIL vetoes
fitment PASS, retaining the contradiction in the raw report. Calibration and
procedure adapters remain separate pending units; `/assist` is untouched.

The six-frame [next SAM batch](sam-batch-review-2026-10-27.json) is prepared for
review only: no execution approval, no automatic retries, cost unverified, zero
calls. It requests paper masks, not fitment/presence. The geometry failure must
be considered before approval; these paper masks alone cannot repair registration.

## What to film next

1. Keep the taped pad and robot fixed. First obtain a sharper native still with
   all nine marked centres visible and a margin below mark 3; it is near the
   current frame edge. Use light/focus and a higher-resolution camera profile
   if available. Record the exact profile and reread native pixels; do not scale
   the current annotations into another stream. Independently verify centres
   and physical positions, particularly marks 6 and 9. These are possible error
   sources, not a diagnosis that blur alone caused the failure.
2. Freeze new readings and repeat the same independent 1–4 / 5–9 split and
   2 px bar. Do not use validation residuals to optimize marker readings.
3. After the paper-plane mapping passes, measure its relationship to the fixed
   robot drawing frame and the intended path/margin. Paper moving must not move
   the commanded footprint. Then extend the fault set with masks/observations
   tied to those exact frames and poses; more angles alone do not fill this gap.

Viewpoint invariance remains untested. No paid calls, GPU use, robot movement,
threshold lowering or live gate wiring occurred. The $20 ceiling remains.

## Validation

**86 tests pass**, including six integration tests replaying the actual private
S03 envelope, strict identity/staleness failures, the presence/fitment veto,
fixed-split held-out rejection, and the existing 19 backend regressions. Without
private S03 artifacts those six integration tests skip explicitly; the reported
local run supplied them and had zero skips. Real registration remains failed
despite passing implementation tests.

```sh
AFL_S03_DIAGNOSTIC_DIR="$HOME/Movies/Ambient-Field-Lens/2026-10-26/drawing-readiness/sam-diagnostic-01" \
  PYTHONPATH=backend python -m unittest discover -s backend/tests -q
```
