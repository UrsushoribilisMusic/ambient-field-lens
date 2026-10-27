# Codi — drawing-readiness capture, 27 October 2026

## S04: missing pen

At the operator's request, recorded a 12-second video-only take with the pen
already removed, Ross idle and paper/camera left in place. Representative frame
at 9 s was visually reviewed: holder visible and empty, paper block/book visible.
The robot face is unlit; controller HTTP status was reachable and reported no
job or showcase running. No robot movement command was issued.

Private artifacts: `~/Movies/Ambient-Field-Lens/2026-10-27/drawing-readiness/`.
The capture record, camera-profile inventory and review manifest record:

- Scene `S04-pen-missing`; same question, “Can I draw this here?”
- Frame SHA-256: `45d5a4d4a3cc0d220f64d119152bd5d1f049254296097b81c30be101d498ddc9`.
- Clip SHA-256: `a30b330dc38cbcae0097a35c97e9d3341b9ef1b6c5c997e58403ac6280717507`.
- Camera profile `reolink-tripod-896x512-uncalibrated-v1`; intrinsics/distortion
  unknown. Pose bucket `tripod-A-approximate`; inter-session pose continuity is
  not verified. Surface pose `2026-10-27-book-block-unregistered`.
- Human-observed fault: no pen fitted; holder visible. Detector check not run.
  Footprint remains unknown without measured registration and a specified path.
- Daylight differs from yesterday evening, so this is not treated as a perfectly
  controlled single-variable pair with the previous baseline. Capture a refitted
  pen baseline under the current lighting before changing camera angles.

## Controller disagreement

Controller still reports `calibrated: true` and `session_ready: true` with the
pen physically absent. Its session/tool/surface binding is unverified. This is
recorded as a disagreement, not tuned away or accepted as physical readiness.
Refitting the pen can change Z; recalibration must be revisited before drawing.

No SAM request or GPU window was started for this take. Live backend remains
default-deny; viewpoint invariance and real containment validation are untested.

Capture utility now chooses the current local-date directory by default and
allows an explicit `--output-dir`, avoiding yesterday's hard-coded destination.

## S05: pen refitted, before recalibration

Recorded another 12-second take, representative at 9 s. Pen visibly fitted and
extending through the holder toward paper. Operator reports it touches the paper
at a slightly different spot from initial shots. Contact force, exact contact
coordinates and correct Z calibration cannot be established from this image.

Private S05 capture/review records are linked with S04 in today's manifest.
Camera-profile inventory and approximate tripod-A bucket are retained, with
metric continuity unverified. The tool/contact pose is explicitly new. Robot
face is illuminated in S05, unlike S04; this additional change is logged rather
than claiming a perfectly controlled missing/refitted pair.

Pen/holder detector not run. Footprint check remains unknown. No motion,
calibration, SAM or GPU command was issued by this capture. Operator was cued
to run the existing Control Center's Recalibrate flow before drawing, keeping
paper/camera fixed. A calibrated baseline remains pending.
