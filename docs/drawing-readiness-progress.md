# Drawing readiness — CPU checkpoint, 26 October 2026

**27 October evening update:** see the [measured v2 and adapter report](verification/adapter-and-measured-v2-2026-10-27.md).
Nine manual readings, fit 1–4 / validation 5–9, fail the unchanged 2 px bar:
RMS 2.054368 px, max 2.954858 px. No robot-frame linkage accepted. Frame-bound
adapters and six-check veto composition are implemented; saved S03 is archival
and stale, never refreshed. The inventory now covers 45 frames, both actual
presence and footprint unknown on all 45. A six-frame SAM batch is prepared
for review only; zero calls. Calibration/procedure adapters remain pending.

**Earlier 27 October update:** the historical checklist below is retained as the night
checkpoint. The [current scene report](verification/scene-batch-2026-10-27.md)
and [capture/fix log](drawing-readiness-2026-10-27.md) supersede its inventory and
test counts. 42 image assets are now ingested with verified hashes, distinct
camera/stream profiles and coarse pose buckets. A separate observable pen/holder
presence function is implemented.29 readiness tests,8 provenance tests and19
backend tests pass (56 total). Human-reference replay is separate from absent
image-model observations; actual presence/footprint outputs remain unknown on
all 42. No real registration, autonomous image check, viewpoint-invariance or
GPU-eligibility pass is claimed.

The green/amber contract was committed first (`972a81f`). The live `/assist`
implementation is unchanged and remains default-deny. No GPU started in this round.

## Implemented and tested

`backend/readiness/checks.py` independently checks current paper evidence, pen
fitment, full raster footprint containment, bound/fresh calibration and exact
approved procedure identity. Unknown stays amber with a named correction.

`backend/readiness/geometry.py` fits a normalized planar homography from at least
four measured correspondences and requires at least four distinct held-out
points. Independent error must be at most 2 px. It binds camera/rig/surface pose,
rejects extrapolation beyond the measured fitting region, expands the footprint
in millimetres, then conservatively rasterizes all touched cells. Paper holes,
offscreen footprints, moved surfaces and unvalidated mappings cannot pass.

These functions consume trusted observations; a boolean claiming registration
or fitment is not an independently authenticated sensor. There is no HTTP input
path for these evidence objects and no live gate integration this round.

CPU validation: **21 readiness/geometry tests and 19 existing backend tests pass**.
The geometry fixtures are synthetic algorithm tests, not physical calibration.

```sh
python -m pip install -r backend/requirements-readiness.txt
PYTHONPATH=backend python -m unittest discover -s backend/tests -p 'test_readiness*.py' -v
```

## Physical captures and operator clarification

Video-only captures and derived frames are private, outside this public repo:
`~/Movies/Ambient-Field-Lens/2026-10-26/drawing-readiness/`.
`review-manifest.json` records frame/clip digests, reviewed observations and gaps.

The operator taped a paper block onto a book to raise drawing Z. The top sheet
is the drawing surface. Moving the book therefore moves the workplane pose;
an approximate return is a new baseline, not a restoration of registration.

| Evidence | Reviewed observation | Limitation |
| --- | --- | --- |
| S00 baseline | Clear pen/paper view, original pose | No measured registration |
| S01b at 15 s | Calendar obscures pen holder and paper | Occlusion is not pen absence |
| S02 live snapshot | Book/paper block shifted right | Pen still above part of paper; not a proven out-of-paper footprint |
| S03 restored baseline | Clear view after approximate return | Treat as new unregistered pose |

The timed S02 take missed the displaced position; the separate live snapshot
retained it. Requested conditions are not automatically treated as labels.
The real paired set is **incomplete**. Pen removal/refitting is deferred until
the operator is ready to recalibrate because it can change tool height.

## One authorized SAM mask diagnostic

One actual request, zero paid retries: HTTP 200, `response.completed`, two masks
decoded with `meta-sam-parser==0.1.0`. A credential lookup failed locally before
that request; no network request/receipt was made on that initial attempt.

The S03 image SHA-256 is
`ec3118828805f3cc30fa4da3fcb5b44de8827b3e2fa8d38fd6b2ea2c6b8a4dc9`.
Manual box prompts identified two regions on the 896×512 frame:

```text
<0f>1<|box;x1=103;y1=343;x2=483;y2=407;w=896;h=512|>,2<|box;x1=242;y1=266;x2=270;y2=361;w=896;h=512|>
```

The request used `model: sam-3.1`, one image/message, `stream: true`, and
`metadata: {mask_encoding: one_bit}` per the documented invocation. It returned
12,971 nonzero pixels for region 1 and 1,642 for region 2. The decoded overlay
was visually checked against paper top/pen. Prompted region semantics are manual:
this confirms transport/decoding, not autonomous recognition or pen fitment.

Raw SSE, parsed mask rasters, overlay, receipt and offline readiness report are
private in `sam-diagnostic-01/` under the capture directory. The replay returns
**amber**: no fitment evidence, real registration, bound calibration or approved
current corpus step supplied. It does not treat the saved controller flag as
current calibration. Replaying saved events incurs no API call.

References: [request format](https://dev.meta.ai/docs/sam/segmenting),
[output grammar](https://dev.meta.ai/docs/sam/reading-segmentation),
[official parser](https://dev.meta.ai/docs/sam/client-libraries).

## Remaining before a GPU comparison

1. Measure drawing-plane correspondences in Ross coordinates, including four
   independent validation points; define the actual drawing footprint/margin.
   Paper-attached points must not cause the intended robot path to move with
   displaced paper. Track workplane pose explicitly after moving the book.
2. Complete tool/calibration/evidence paired cases, hand-review labels and verify
   CPU outcomes on the actual scenes. Current visibility/position captures alone
   do not satisfy this requirement.
3. Obtain fresh controller session/tool/surface binding and the exact approved
   current procedure evidence from the Ross corpus. No guessed approval flags.
4. Only after the real paired set passes, compare observable checks, task-specific
   grounding and the full Jacobian method on those same cases within the $20 cap.

GPU eligibility remains **false**. The failed confidence threshold stays failed.
No prior dataset, Canis matrices or Sovereign Mind chunker code was vendored.

## Overnight handoff: requested work versus actual completion

This is the first **single-view paired batch**, not the complete paired
validation set. No all-scene pass/fail evaluation has been completed.

| Requested deliverable | Actual status |
| --- | --- |
| Save captures, hashes and exact changes | Done: four reviewed representative frames, including a standalone displaced snapshot |
| Ingest camera profile and pose bucket per image | Pending: camera ID exists, but no complete per-image camera-profile/pose-bucket schema has been ingested |
| Pure footprint-inside-paper function with tests | Done on synthetic inputs; actual marker-derived surface coordinates missing |
| Pure pen/holder presence function with tests | Partial: current module checks a pen mask and separate fitment evidence; independent holder-presence check still needed |
| Run both checks on every tonight scene | Not done: only S03 has actual SAM masks and an offline replay |
| Compare raw outputs with each staged fault | Pending; do not replace missing measurements with intended labels |
| Viewpoint invariance explicitly untested | Confirmed: one fixed Reolink viewpoint, no angle-robustness result |
| Default-deny, no gate wiring, no new GPU | Preserved; $20 ceiling unchanged |

### Scene inventory for tomorrow's filming

Known camera facts: Reolink saved source `Robot_Main_Cam`, camera ID
`ross-reolink-tripod`, 896×512 video, fixed tripod viewpoint. Intrinsics,
distortion, measured marker coordinates and a metric surface profile are not
established. These facts are an inventory, not a calibrated camera profile.

| Frame | Viewpoint | Surface-pose description | Exactly what varies | Raw check coverage |
| --- | --- | --- | --- | --- |
| S00 baseline | Fixed tripod A | Original book/paper-block pose | Clear reference view | No SAM paper/pen/holder batch outputs |
| S01b at 15 s | Fixed tripod A | Not metrically verified | Calendar obscures pen/holder and much of paper | No detector run; observable presence expected not to pass |
| S02 live snapshot | Fixed tripod A | Book and taped block shifted right | Work-surface position; not a camera-angle change | No marker mapping/footprint; containment unknown |
| S03 restored baseline | Fixed tripod A | Approximate return, distinct unregistered pose | Surface returned approximately; no exact pose assumption | Manual-box SAM masks decoded; paper passes offline, fitment/footprint/calibration/procedure unknown |

Tomorrow should extend this batch with new viewpoints, missing-pen cases,
measured markers and the same explicitly specified drawing footprint, rather
than recapture these visibility/position conditions without those additions.
Pen removal/refitting changes height and requires calibration to be revisited.

### Expected faults and disagreements

- Covered pen/holder must fail **observable presence** because the evidence is
  occluded. Physical absence and unknown visibility remain separate facts.
- A displaced surface is intended to fail footprint containment, but displacement
  alone is not sufficient evidence. The snapshot still puts the pen above part
  of the paper; no drawing path/footprint or marker mapping has been supplied.
  Record this as **unknown / unmet validation prerequisite**, not a measured
  containment failure or a successful fault detection.
- No detection threshold has been tuned to obtain the expected labels. The
  fixed registration error bound in synthetic geometry tests is not a tuned
  model confidence threshold and is not a measured physical calibration.

PR #2 remains unmerged at this checkpoint. This work uses a fresh branch off
main with Muse's architecture changes merged in, and does not depend on PR #2.
The updated product requires world checks **and** supported generated steps;
passing the five offline setup checks alone does not implement the footing gate.
