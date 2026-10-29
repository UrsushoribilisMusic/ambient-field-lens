# Observable refusal checks — Codi to Muse, 29 October 2026

Scope is runtime evidence for the amber-only demo: pen presence, measured
camera/robot geometry and read-only controller state. No new research scoring,
threshold, GPU window, green permission or automatic hardware action.

## Pen visibly present / absent (not contact)

`providers.pen_presence.observe(image_bytes, frame, request_id=...,
output_root=private_dir, capture_clock_verified=..., mode=Mode.LIVE)` sends a
single Meta Spark request, then invokes the existing strict `adapt_model`.
The new prompt inspects the intended toolhead/holder area and ignores loose
pens on the desk. `fitment` must be null. Absence requires a clear, observed
holder plus a clear pen-absent observation; occlusion/uncertainty is unknown.
Positive presence does not establish attachment or paper contact.

Returns a `pen_observable_presence` component check with full shared provenance,
`verdict: verify`, `step: null`, and `score: 0.0` under EVERY observation.
No `REQUIRED_CHECK_NAMES` or six-check/green rule is changed. Muse can call this
provider in the existing live composition and select an evidence summary for
amber without importing any probe or GPU dependency.

Mode/freshness is explicit. LIVE retains the existing5s clock/provenance policy;
old frames, unverified capture clocks and mismatched bytes cannot become live
checks. API response time does not refresh capture time. The current query+JPEG
request wire has no sensor timestamp: do not set clock_verified just from server
receipt. Review the phone capture/clock binding with Muse; until then label any
replay/received-image demonstration honestly and keep it ineligible for readiness.

Every request saves exact image/request/response/attempt/binding/replay bytes in
private storage and appends an attempt/outcome to the shared API ledger before
sending. Runtime vault key only, no retry/repair calls, no secret/error output.
`providers.pen_presence.replay(path)` rechecks all original hashes/timestamps and
returns ARCHIVE mode, `live_eligible: false`, and amber. A stale live response
still retains a replay manifest for diagnosis; it is never silently promoted.

### Actual provider observations and replay

The earlier saved S04 observation was unresolved. It remains unresolved; no
labels or old outputs were edited. Two authorized runtime-provider checks using
the narrower neutral presence prompt on existing archived S04/S05 images now
produce absent and present respectively. This is component verification, not a
new held-out benchmark or a live phone claim. Both replays remain amber,
contact=false, fitment=false, live_eligible=false. Exact original capture times
and operator-staged scenes are preserved. Private packet:
`~/Movies/Ambient-Field-Lens/2026-10-29/pen-presence/`.

For non-geometric technical correction text use only
`providers.corrections.retrieved(chunks, chunk_id, exact_quote)`: verifies a unique
retrieved chunk/source hash and literal quote. Otherwise leave correction empty.
Do not let Spark generate repair/advice text or treat an unquoted canned hardware
instruction as a retrieved correction. VG03 contact stays unknown/open.

## Measured mapping and signed paper correction

`providers.measured_geometry.compute(frame, paper_mask, record,
robot_vertices_mm, now=...)` composes measured camera-to-plane homography,
measured robot-to-plane affine linkage, and mask containment. The implementation
requires all of the following server-owned evidence; none may be filled by an LLM:

- `reviewed_by_operator: true`, `units: mm`, current frame hash, exact camera/rig/
  surface pose/image dimensions, original physical-measurement SHA256 references.
- `markers_fixed_to_workspace: true` and
  `markers_coplanar_with_drawing_surface: true`. Fixed references must survive
  paper displacement. Previous markers drawn ON the loose paper cannot satisfy it.
- At least4 fit+4 independent validation marker points, actual measured plane_mm
  and native image_px, unique IDs. No fit/held-out point reuse.
- `robot_link` with `units: mm`, `physically_measured: true`, >=3 noncollinear fit
  points and>=3 distinct validation positions, each with robot_mm and physically
  measured plane_mm from actual marks. Commanded40mm is not measured40mm; retain
  the observed45x40 discrepancy instead of concealing it.
- Explicit nonnegative `reading_uncertainty_mm` and measured
  `tool_repeatability_allowance_mm`; unquantified values stay unknown.
- The requested robot footprint must lie within the measured support regions.

The result includes signed clearance, registration error, reading uncertainty,
robot-link residual, robot/tool/raster allowance and source hashes. It always
has `verdict: verify` and no step. It does not apply the historical2px cutoff or
replace past failed results. Missing measurements/camera mismatch cannot pass.

If the observed paper lies outside the footprint, the provider derives a convex
boundary FROM THE ACTUAL MASK and solves for the minimum paper translation,
reported in signed robot X/Y millimetres. A reviewed extractor is required
(`boundary_extractor_reviewed: true`). Holes, excessive concavity, singular
mapping, or an impossible fit refuse correction. No user/model boundary polygon
is accepted. Correction is explicitly "move the PAPER", never an actuator
command, and the human must recheck afterward. Computation tests use synthetic
measurements; no real geometry accepted by those tests.

### Physical protocol for the next supervised setup

1. Choose the demo camera first (iPhone vs Reolink); calibrations are separate.
2. Keep the robot and rigid support fixed. Put small reference crosses/coded
   markers on a rigid reference at DRAWING SURFACE height, outside the paper's
   travel, so they remain when the loose sheet moves. Desk-level marks under a
   raised pad are not coplanar. Do not use the moving sheet as robot coordinates.
3. Measure their actual positions in mm with a clear origin and +X/+Y direction;
   record8+ distinguishable points and freeze a fit/validation split. Capture
   native pixels with the same camera/resolution/pose used by the check.
4. With Miguel supervising any calibration/drawing, establish robot-to-reference
   linkage from actual marked positions spanning the intended drawing area.
   Measure marks independently; retain command-vs-measurement offsets and tool
   repeatability. No software here issues movement or assumes earlier calibration.
5. Review/freeze the measurement artifact and uncertainty bounds. Only then run
   one fixed footprint against well-placed and displaced paper, same fixed marks.
   Record signed offsets; movement of the sheet must not move the robot footprint.

No real record has been marked reviewed by Codi. Awaiting camera choice and
physical measurements; code/tests do not certify the current rig.

## Controller/log/lock evidence

`providers.robot_state.capture(output_dir=...)` is read-only: local GET status,
bounded stable snapshots of calibration.json, ready flag, job lock and calibration
log; only known Ross process IDs/states/start identities are retained. Relative
script names are resolved through actual process cwd, not a matching basename.
No serial connection, lock deletion, process killing, calibration reset or job.

`.assess(frame, snapshot, binding, now=...)` requires fresh evidence and a
server-reviewed binding to calibration/ready hashes+mtime, controller process
identity (PID+start+script), endpoint arm port, tool, surface and controller
session. File existence and UI "calibrated" alone cannot establish that binding.
Restart/PID reuse/tool/surface changes invalidate it. Inconsistent lock with no
worker is only a possible stale-lock diagnosis, not a confirmed zombie; actual
Z-state is separate evidence. Results are amber only; technical correction text
must come from exact retrieved evidence.

Today's read found calibration/ready data and a responsive controller, no job
lock, and one non-zombie control_center process. Session/tool/surface binding is
unreviewed, so the current result is unknown. Snapshot captures and raw hashes
are private in `~/Movies/Ambient-Field-Lens/2026-10-29/controller-state/`.

RED is proposed ONLY in [the review document](proposals/red-controller-contract.md).
No change to the existing response enum or iOS/server verdict logic.

### Mac-to-cloud boundary

The collector must run on Miguel's Mac. Reading container `/tmp` or container
processes would inspect Modal, not Ross. `publish_once(robot_id=..., snapshot=...)`
uses the existing authenticated Modal SDK/receipted client to send one compact
snapshot to CPU-only `put_controller_snapshot`; `fetch_published(robot_id)` calls
CPU-only `get_controller_snapshot`. No public unauthenticated ingestion and no
phone-supplied controller verdict. Both RPCs store/return hashes and ORIGINAL
observation time; fetching never refreshes it. Missing or older-than5s snapshots
cannot become fresh readiness evidence. IAM access is the trust boundary; these
are not hardware-signed attestations. Server policy must pin the robot ID and
reviewed root/process/tool/session binding.

These RPC additions are prepared for Muse's coordinated deployment/review; Codi
has not redeployed the shared app or started a polling daemon. Run a supervised
capture/publish at the needed stage, or review a separately budgeted short-lived
collector window. No indefinite background polling, GPU call or token generation.
