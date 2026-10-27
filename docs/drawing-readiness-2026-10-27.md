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

## S06/S07: operator calibration and post-calibration baseline

On explicit operator request, recorded 180 seconds of video-only calibration
observation (S06), finalized and probed at 896×512. Sampled frames at 30/90 s
were reviewed; they show the pen fitted and near-static views, not verification
of every calibration step. Operator reports completion. A separate 12-second
post-calibration baseline (S07, representative 9 s) was captured and inspected.

Fresh controller snapshot reports calibrated/session_ready true, no job/showcase,
z_up 6 and tilt_slope 0.02 (previously 0.0325). Saved calibration file also reports
tilt_slope_x 0.00625. This establishes that new calibration values were saved;
it does not establish physical accuracy, a measured camera mapping or trusted
controller-session/tool/surface binding. The post-state snapshot and capture
records are in today's private directory/review manifest. No robot command was
issued by the recording utility. The operator ran the normal calibration flow.

Capture duration now allows up to 600 seconds for explicitly requested process
recordings. No camera-angle change, SAM call, GPU window or gate wiring occurred.
Operator has ruler and pencil/tape available; requested top-sheet dimensions in
millimetres before specifying reference points. Paper-plane registration still
needs a separate link to Ross's drawing coordinates; paper-attached marks alone
must not make the planned robot path follow displaced paper.

## S08: first four red reference marks, visibility limitation

Operator measured 145×205 mm usable sheet, plus 15 mm binding (220 mm total
depth), then reported drawing the first four red A–D crosses at the requested
10 mm inset. Recorded a 5-second original-view take and an additional main-stream
snapshot. The paper is heavily foreshortened; all four red cross centers cannot
be reliably distinguished in either image. No measured image-point
correspondences or physical registration were accepted.

Preserved the sheet/marks and requested only a higher, downward-looking camera
view including all paper corners and the pen holder. Thinner lines would not
address the visibility problem. The new viewpoint must receive its own pose
identity/registration. The main-stream detail has a distinct resolution/profile;
its pixel coordinates must not be reused as substream coordinates without an
explicitly validated mapping. Private inventory records this limitation.

## S09: raised/downward viewpoint B

Operator reports camera raised approximately 9 cm and panned downward. Saved a
5-second substream take and 2880×1616 main-stream still, with distinct profile
metadata and viewpoint bucket `tripod-B-raised-downward`. Three red corner marks
are now distinguishable; the far-side fourth near Ross is not identifiable.
No four-point mapping was accepted. Requested a steeper downward view framing
paper and holder; sheet, robot and red marks are to remain in place.

## S10/S11: further height and sideways visibility correction

S10 records the operator's reported 24 cm height increase. Three crosses remained
clear but the far reference was partly hidden; no four-point mapping accepted.
After a sideways camera adjustment, S11 main-stream still and paper crop show
all four red reference marks, including the far mark beside the binding. This
is adequate visibility to attempt point annotation, not a validated registration.
Requested camera/surface stay fixed and independent measured E–H points be added
at the previously specified positions. Coordinates, fit and held-out validation
remain pending. All snapshots/review metadata remain private; no SAM/GPU calls.
