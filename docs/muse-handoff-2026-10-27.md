# Codi — handoff for Muse, 27 October 2026

## Evening update — supersedes the historical checkpoint below

OPERATOR DIRECTION: Miguel reminds us Reolink is the development test camera,
not the phone capture path, and requests proportional effort. Stop further
physical sheet tweaks/precision chasing on Reolink. Freeze current evidence.
The current native2px validation remains failed, with no green promotion; v2
contract is unchanged pending review. Its application at2880px is3.21times
stricter in image-width terms than at896px and should have been flagged earlier.
Next geometry review should define a physical error budget and explicit camera
profile/resolution, then validate on the intended phone capture path. Reolink
manual-reading diagnostics do not validate or invalidate the phone mapping.
Continue CPU replay/adapter work independently of this unaccepted geometry;
missing footprint registration remains unknown. No new paid calls/GPU, no gate
wiring. No further operator redrawing or recalibration requested for this test.

Miguel also notes the actual drawing tool is a thick felt pen, producing broad
strokes rather than detailed drafting. The proposed physical tolerance review
should use measured stroke width, path clearance from paper edges, camera
registration uncertainty and robot drawing error as separate budget components.
Task success is observable setup readiness and a comfortably contained drawing,
not precision plotting. Stroke width alone is not a validated error bound or a
reason to relabel the current2px failure. No new acceptance number chosen yet.

LATEST RULER FOLLOW-UP: rectangle120×120mm and centre lines60/60mm confirmed;
cross9 approximately78.5/92mm. Frozen rectangle-frame pixels unchanged.
[Latest report](verification/rectangle-ruler-confirmed-result-2026-10-27.md):
errors5–9=1.010/3.062/1.043/1.631/4.954px; RMS2.781517/max4.953930px FAIL2px.
Three validation points pass;6/9 fail. Physical approximation and1–3px manual
reading ambiguity are unquantified. Requested no more sheet changes: next
independently review image centres/measurement precision, not redraw to improve
residuals. All previous hypotheses preserved. Centre10 hidden remains unknown;
robot linkage and live gate still absent. No calls/GPU/motion/tolerance change.

LATEST: Miguel discovers new sheet grid is4mm, not5mm. Grid-count-derived
coordinates now unverified; no automatic80% rescaling. Rectangle/centrelines
captured, native hand readings preserved, centre10 hidden by pen stays unknown.
[Conditional result and clarification](verification/rectangle-centrelines-result-2026-10-27.md):
nominal120/60 layout with9 at80/90 gives RMS3.694776/max7.356228px FAIL2px,
but physical acceptance is UNKNOWN until ruler-only actual coordinates exist.
Requested top span1→2 and left span1→3, no redrawing/motion/calibration. A unit
rescale alone does not repair pixel errors; do not tune or infer coordinates.

Follow-up to clean-sheet result: operator says cross9 actually85–90 (interpreted
x85/y90). Preserved separate physical correction, no changed pixels/corners.
Corrected diagnostic fails: cross9 18.569767px/RMS8.469682px. Confirm cross1
intersection is the measurement origin before more changes; do not tune away
operator measurements or image residuals. Prior clean-sheet80/90 result retained.

Latest: operator replaced sheet with fine crosses using new60mm-midpoint layout.
[Clean-sheet report](verification/clean-cross-sheet-result-2026-10-27.md): new
2880×1616 frame, frozen manual intersections, same1–4/5–9 split and2px bar.
Errors5–9=1.293/3.235/1.061/0.761/5.290px; RMS2.892333px/max5.290237px FAIL.
Actual ruler positions not independently verified by agent; requested mark9
x80/y90 check next, then midpoint6. Pad replacement is a new surface pose,
no old calibration/robot mapping accepted. No GPU/calls/motion or gate change.

After dinner: [new 2880×1616 geometry-only capture](verification/after-dinner-reprojection-2026-10-27.md)
fits all nine marks in frame. Fresh manual centres, same split/bar: RMS5.915379px,
max8.634428px FAIL. No scale transfer from v2. Requested physical centre-distance
verification (mark6 at55mm from mark1 along top row; mark9 x80/y90), not another
camera adjustment or residual-guided annotation. This new frame has no masks;
presence/footprint unknown. Earlier45-frame inventory remains a separate batch.

PR3 is now merged on main (`d9fbed4`). Contract v2 and the subsequent adapter /
measured-marker work are in [draft PR4](https://github.com/UrsushoribilisMusic/ambient-field-lens/pull/4),
implementation commit `c216eb6`, still on `codi/drawing-readiness-cpu`.

The [evening report](verification/adapter-and-measured-v2-2026-10-27.md) records
all nine original-pixel manual readings and the declared split. Fit1–4,
validate5–9: errors1.959555/2.443605/1.233750/1.018698/2.954858px,
RMS2.054368px. **FAIL against2px**, no refit or tolerance change; paper-plane
and robot-coordinate geometry are not accepted. Source positions are Miguel's
`markers-2026-10-27.txt`; no nominal S12 coordinates were substituted.

Frame-bound adapters and exact-six-check veto composition are implemented.
86 CPU tests pass, including six real S03 replay integrations. S03 remains
archival/stale, request age205.631s, two masks and no structured presence/fitment.
Inventory45 frames, actual presence/footprint45 unknown. A six-frame paper-mask
batch is prepared only, not approved or executed. No GPU/new paid calls, live
gate changes or robot commands. Calibration/procedure adapters remain separate.

Next film a sharper native nine-mark frame, keep the taped pad fixed, reread
all native centres before calculating residuals, repeat the same split/bar,
then establish robot-frame linkage if it passes. More camera angles alone do
not resolve current geometry or missing input evidence. Proper review pending.

## Historical checkpoint

## Reviewable state

- [Draft PR3](https://github.com/UrsushoribilisMusic/ambient-field-lens/pull/3),
  branch `codi/drawing-readiness-cpu`, worktree
  `~/projects/ambient-field-lens-readiness`. PR2 is still draft/open; this work
  is independent of its merge. Do not conflate branch code with live main.
- [CPU inventory/report](verification/scene-batch-2026-10-27.md):42 image assets,
  verified hashes,3 distinct stream/camera profiles, coarse A–G/phone poses.
  Raw media is private under `~/Movies/Ambient-Field-Lens/{2026-10-26,2026-10-27}/drawing-readiness/`.
- Missing/refitted pen, clear/covered/clear, clipped paper, clear fixed-pen-
  outside-paper, and returned-under-pen references are captured. Some frames
  intentionally have visibility limitations; exact pose continuity is unmeasured.
-56 backend/readiness/provenance tests pass. Human-reference presence logic
  replay27 pass/3 fail/12 unknown is not autonomous detector accuracy. Actual
  presence and metric footprint outputs remain unknown on all42 assets.

## Findings that affect the demo

External Robot Ross basic-shape code ignored saved X tilt. Fix `a2ec499` is
pushed on `feature/macos-control-center` in the separate robot-ross repo;
19 hardware-free tests pass. One square succeeded visually after both the fix
and recalibration, but measures45×40 mm for a40×40 mm command (opposite sides
match). No universal axis correction or isolated causal attribution is justified.
No legacy robot code was copied here.

Nominal/refined marker fits failed the unchanged2 px bound. Paper/book edges
differ, loose-sheet depth is208 mm, operator F/H marks101 mm from the edge
opposite binding, and the ruler zero extends beyond the paper edge. Do not use
nominal marker coordinates or the40 mm command as a validated physical ruler.
The new returned placement does not restore the original calibration pose.

## Suggested coordination

Please independently review PR3 and the raw-output/reference distinction.
The next software work needs a structured image-observation contract/adapter
(pen/holder visibility/presence and paper mask provenance), plus accepted
marker-to-robot geometry. Models supply observations, not verdicts. Coordinate
ownership of that work with Codi rather than duplicate the physical filming.
The exact paid SAM/Spark batch should be prepared for review before additional
calls; the single authorized SAM diagnostic was already used successfully on
S03. Its two manual-box masks establish transport, not automatic recognition.

No GPU until the real paired set passes CPU checks. $20 ceiling holds. Keep the
live backend default-deny; no green wiring or threshold lowering. Grounding/full
Jacobian comparison, controller session/tool/surface binding and exact approved
current corpus-step evidence remain pending. Viewpoint invariance is untested.
