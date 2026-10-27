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

## S12: eight marks visible; preliminary nominal mapping rejected

Captured main-stream S12 with all eight red marks distinguishable, camera left at
the successful sideways viewpoint. A preliminary manual annotation used corner
marks A–D for fitting and edge marks E–H for independent validation, with the
nominal ruler positions supplied in the operator instructions. Proposed point
identities/origin are not yet operator-confirmed; manual image localization
uncertainty is approximately 4 px. No coordinates were inferred as Ross robot
coordinates.

Held-out errors E/F/G/H: 5.13 / 18.12 / 4.13 / 19.97 px. The unchanged 2 px bound
rejects this preliminary mapping. This is not an accepted physical calibration
and not evidence of successful marker registration. Private report and point-ID
review image preserve exact annotations and assumptions. Operator was asked to
confirm whether down-measurements start below the binding or at pad top before
any further interpretation; no redraw/camera move requested. No paid/model calls,
GPU window, threshold adjustment or live gate wiring.

### Operator origin clarification and centre refinement

Operator clarified that downward measurements start from the sheet edge opposite
the binding, and noted that the felt-tip marks may be too broad. This reverses
the paper's vertical coordinate convention. A uniform coordinate reflection
cannot by itself change held-out reprojection errors; no accepted robot mapping
was inferred from the clarification.

Refined the image centres offline in fixed manual 37×37 windows using positive
red-minus-green-squared weights (red/magenta mark signal), without a binary
presence detector or fault-label-dependent tuning. An initial red-excess-over-
both-other-channels diagnostic had no signal for A under this lighting; no
result was accepted from that method. The refined held-out errors E/F/G/H are
2.64 / 18.64 / 2.21 / 24.85 px: still rejected by the unchanged 2 px bound.
This does not establish a cause; physical positions, identities, localization,
paper planarity and camera distortion are not independently verified.

Requested actual bottom-edge-to-centre measurements for the two side midpoint
marks (F/H in the proposed annotation, nominal 102.5 mm). Kept sheet/camera fixed;
no redraw or robot motion requested. Private report `S12-refined-centres.json`
retains the new origin convention and estimates. No paid API/GPU calls.

## S13: paper dimensions corrected; ruler view insufficient for scale reading

Operator measured a removed sheet at 208 mm depth, superseding the earlier
205 mm estimate, and confirmed both F/H side marks are 101 mm from the opposite-
binding paper edge. The book protrudes beyond the paper: the reported book-edge
distance is 105 mm, so book and paper edges cannot be interchanged. Preserve
actual mark positions rather than moving them to the nominal specification.

Captured S13 main-stream still with ruler on paper. It is visible, but scale
ticks and zero are not reliably legible in the crop; no new metric mapping was
accepted. Requested a close overhead phone photograph with ruler zero tick at
the actual paper edge and nearby marks included, leaving book/Reolink fixed.
The removed-sheet measurement is operator evidence, not an independently
verified fitted-sheet geometry. Camera/ruler scale plane and all eight actual
mark positions remain unverified; prior rejected fits stay rejected.

## S14: close phone ruler photograph

Inspected operator photo IMG_7107.HEIC; archived original, converted PNG and
orientation-normalized derivative privately with hashes/provenance. This is a
distinct phone camera/viewpoint, not a substitute Reolink calibration image.
Centimetre labels are readable, and the ruler zero lies beyond the opposite-
binding paper edge. Any ruler-derived mark coordinates need that offset; the
book edge is not the reference origin. Thick red cross centres and graph grid
are visible, with upper-middle paper occluded by the holder.

No exact ruler offset, grid spacing, all-eight coordinate set or camera/robot
registration was accepted from visual inspection alone. Operator's measured
208 mm loose-sheet depth and 101 mm F/H positions are preserved as such.
Ruler scale height and phone intrinsics remain unverified. No request to redraw,
no threshold adjustment, paid API, GPU window or motion command.

## S15/S16: first square, timing failure and faint edges

Operator configured the existing 40 mm Square command. The existing Execute
button is at the bottom of Control Center; no UI fix was made. S15 180-second
recording finalized, but operator confirms drawing was almost finished before
the wait-for-cue instruction was seen. Preserve as an incomplete-action take,
not a complete filmed drawing. Actual nominal dimensions were not measured.

S16 main-stream result shows a new square-like outline overlapping earlier ink,
with faint sides; four precise corners cannot be reliably localized. Controller
reports command completed, calibrated/session_ready true, z_up6, tilt0.03125.
Completion does not establish stroke quality. This differs from earlier tilt0.02
and remains in provenance. No causal depth/tilt diagnosis accepted from image.

Operator proposed recalibration/contact correction and redraw. Started S17
process recording before explicitly cueing normal Recalibrate. No agent-selected
depth or robot command. Operator instructed to keep camera/paper fixed, finish
calibration and report back without executing the next square. A redraw needs
a separate recording-ready cue; preserve the faint result as fault evidence.

## S17–S19: contact recalibration and repeat remain unsuccessful

Operator reported finished recalibration. Fresh post-state: z_up3, tilt_y0.035,
calibrated/session_ready true, job/showcase idle. S17 recording finalized. S18
120-second drawing recording was started before an explicit GO, followed by
operator reports “drawing is starting”, then finished but pen too high. Captured
S19 main-stream result and completed controller state. Corners remain unsuitable
for precise registration; no geometry/contact pass is claimed.

Inspected the external Robot Ross implementation and found that basic-shape
travel/draw moves ignore saved X tilt while applying Y. Corrected there as
`a2ec499` on `feature/macos-control-center`; 19 hardware-free tests pass. At the
current X slope0.01, 40 mm X travel lacked 0.4 mm relative correction. This is
a definite software defect, not proof of the sole cause of the failed drawing.
No Robot Ross code was copied into this clean-room hackathon repo, and no arm
command was sent to validate the fix. Operator calibration/order files preserved.

Clarified that Z_UP is travel clearance, not drawing pressure; changing6 to3
does not fix an incorrectly established initial contact point. Supervised
physical verification after that contact check remains pending. No GPU or
paid API calls; experimental backend remains default-deny.

## S20–S22: successful supervised square after fix and recalibration

Operator completed another normal calibration; fresh state reports z_up2,
tilt_y0.0325, ready true, job/showcase idle. The saved operator calibration also
has tilt_x0.00375. S20 process clip finalized. S21 drawing recording started
before an explicit GO; operator then reported drawing in progress and completion
with “worked beautifully”. S21 finalized at 120 s (896×512). Initial/late sampled
frame reviews show tip/state changes and completed outline; exact individual
stroke boundaries have not been annotated.

S22 main-stream result shows a closed square with much clearer sides, consistent
with operator feedback; controller reports completed and idle. This supports
one successful supervised trial after both external Robot Ross X/Y tilt fix
`a2ec499` and recalibration. It does not isolate which change resolved contact.
Prior HELLO ink overlaps the square. Side lengths have not been measured, and
no precise robot-camera mapping, viewpoint invariance or gate pass is claimed.

All raw/result clips, original images, provenance and calibration snapshots are
private in today's capture directory. Next: measure two adjacent square sides
without moving the book, then extend viewpoint captures of the same fixed
setup. GPU eligibility remains false; no paid/model calls or live gate wiring.

### Dimensional check: 45×40 mm reported, not a metric pass

Operator measured the post-fix square as width45, height40 and explicitly
confirmed millimetres (initial message said cm). Nominal command is40×40 mm:
reported width error+5 mm/+12.5%, height0. These are operator ruler measurements,
not independently verified photo coordinates. Actual robot-axis identity of
the named width has not been verified.

Read-only source inspection confirms Control Center passes the selected shape
size, the wrapper does not enlarge40 mm, and basic-shape code requests relative
X40/Y40/-X40/-Y40 after selecting metric mode. No application width multiplier
was found. This does not identify a firmware/mechanical cause. Requested the
remaining two opposite-edge measurements before interpreting stretch/skew or
ambiguous ink corners. No new drawing, calibration or firmware change issued.
Visual stroke success remains separate from the failed dimensional check;
do not use this square as an assumed40 mm metric calibration reference.

Operator subsequently confirmed the opposite sides match:45/45 mm and40/40 mm,
and describes the result as a rectangle. This is four operator edge measurements
on one drawing, not repeatability across sizes/positions or independent angle
measurement. Treat45×40 mm as this drawing's measured physical dimensions;
do not infer a universal axis correction. Saved S23 main-stream baseline before
the next camera-angle change. Robot, paper and book are to stay fixed while
extending viewpoint captures; metric registration remains pending.

## S24: next sideways viewpoint, near paper edge clipped

Captured new main-stream viewpoint after operator's lateral camera move. Pen
holder and rectangle are clear, but near paper edge/lower red marks are cut off
at frame bottom. Preserve this as an incomplete-visibility case, not a passing
full-paper/containment example. Requested camera remain at the new position and
tilt down slightly to include sheet, all marks and holder; robot/book unchanged.
Actual camera displacement and physical setup continuity remain unmeasured.

## S25–S27: usable backed-away view and matched occlusion sequence

At the camera's tilt limit, operator backed it away. S25 shows the full sheet
and pen holder; retained as viewpointF. S26's45-second window missed the intended
occlusion in reviewed samples, so it is not marked a successful fault take.

Added operator-stop recording support: capture writes a private PID receipt,
and `stop_capture.py` verifies the exact ffmpeg process/clip identity before
SIGINT to finalize the file. Capture accepts that explicitly requested stop only
after a valid-duration probe and extracts a representative frame within actual
duration. It never sends a robot command or prints credential-bearing argv.

S27 used the longer window and finalized at111.7 seconds on operator completion.
Human-reviewed same-clip reference frames: clear30 s, calendar-covered80 s,
clear100 s. Full holder/pen occlusion visible at75/80/85/90 s, clear again95 s.
The calendar also hides much of the paper: log both tool and paper visibility
changes, not a pure tool-only manipulation. Exact transitions are only bracketed
by sampled times. Frames/hashes and private timing contact sheet are retained.

This confirms a captured visibility pair, not an automated presence/containment
check pass. Metric mapping and all-scene CPU/model evaluation remain pending.
The896×512 substream samples have a distinct profile from2880×1616 main-stream
images. No coordinate interchange, paid API, GPU, motion or backend gate wiring.
