# Drawing-setup readiness contract — v1

Locked by Miguel on 2026-10-26 before implementation. The demo is the five-step
drawing-setup sequence: look at Ross, identify pen/paper and preview footprint,
name a failed check and correction, re-check after correction, then let the
operator confirm the preview and start through the normal controls.

## Meaning of green

Green means **all five checks passed for this frame, this setup and this
approved procedure step**:

1. **Paper present.** Current-frame evidence identifies a sufficiently visible
   paper region. An empty, ambiguous, occluded or mismatched mask does not pass.
2. **Pen fitted.** Current-frame evidence identifies the intended pen in its
   holder, with fitment observable. A pen lying on the desk, another tool or a
   hidden fitment does not pass. A pen-shaped mask alone does not prove fitment.
3. **Footprint inside paper.** Every occupied footprint cell, including the
   configured margin, lies in the paper mask after an explicitly validated
   drawing-plane-to-camera mapping. A bounding rectangle, mask confidence or
   area-overlap percentage is insufficient. Unknown registration does not pass.
4. **Calibration ready.** Fresh controller state explicitly reports successful
   calibration for the current controller session, tool and work-surface setup.
   Missing/stale state, a restarted controller, changed tool/surface or an
   uncalibrated flag does not pass. A saved calibration file alone is insufficient.
5. **Approved current step.** The requested step is the current allowed step in
   the approved drawing-setup procedure, and its exact text/version/source hash
   matches the corresponding Ross corpus evidence. Retrieved free text, a draft,
   a stale document or a skipped step does not pass.

Unknown evidence produces amber. It cannot be converted to a pass by another
check, an LLM score, a confidence threshold or a probe. Checks consume model
observations as inputs; models never supply the combined verdict.

## Meaning of amber

Amber lists each failing/unknown check by name and gives its concrete correction:
show/position the paper; fit/show the correct pen; reposition paper or reduce
the footprint; establish/re-establish registration; calibrate this setup; obtain
fresh controller state; or return to the current approved procedure step.
Passing checks never hide another check's failure.

## Geometry and evidence identity

Frames, masks, registration and observations are bound by image digest and
camera/rig identity. Registration explicitly maps a measured planar work
surface into image pixels, with separately checked correspondences and bounded
reprojection error. SAM supplies object boundaries, not robot coordinates,
surface depth, physical pen contact or calibration state. Registration must be
invalidated by a changed camera/rig or surface coordinate frame.

## This round

The check suite is pure CPU code. New tripod scenes use the same question while
varying tool, visibility, paper position, calibration state and available
evidence. Real clips, frame hashes, changes, hand labels and provenance are
recorded; synthetic fixtures never count as filmed or hand-checked scenes.

After the checks and capture scaffold, one authorized documented SAM diagnostic
will establish whether actual masks arrive. Camera/surface registration is
implemented and tested explicitly. Observable checks, a task-specific grounding
readout and the full Jacobian method can then be compared on the same cases.

No GPU until the real paired set exists, has hand-checked labels and passes its
CPU checks. The $20 ceiling continues. Prior datasets remain external references;
the failed confidence threshold remains failed.

This round does **not** wire the new gate into `/assist`: that is a separate
reviewable change. The live backend remains default-deny. A check-suite green
is a scoped offline result, never a safety certification or robot motion command.
