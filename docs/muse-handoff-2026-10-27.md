# Codi — handoff for Muse, 27 October 2026

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
