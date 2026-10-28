# Clean cross-sheet result — 27 October 2026

Miguel prepared the fresh sheet following the [new 60mm-midpoint layout](clean-marker-sheet-protocol-2026-10-27.md)
and reported ready after removing/replacing the pad. All nine fine crosses are
visible in new native2880×1616 frame `clean-cross-sheet-200843.jpg`. This is a
new surface pose, with no old robot calibration/registration assumed valid.
Source frame/readings remain private; [frozen readings and residual metadata](clean-cross-sheet-reprojection-2026-10-27.json)
are versioned without image pixels.

Hand-read intersections, excluding adjacent labels, were frozen before the
same normalized DLT fit1–4 / independent validation5–9. No annotation tuning.
Positions are the layout the operator prepared; the agent has not independently
read ruler graduations verifying each actual coordinate. Small crosses remain
blurred, with roughly1–3 native-pixel reading ambiguity, unquantified.

| Held-out mark | Error px | Against unchanged2px bar |
| --- | --- | --- |
| 5 | 1.293 | pass |
| 6 | 3.235 | fail |
| 7 | 1.061 | pass |
| 8 | 0.761 | pass |
| 9 | 5.290 | fail |

**RMS2.892333px, max5.290237px — overall FAIL.** Four exact fitting corners
interpolate; their residuals are not validation. Geometry is not accepted and
robot-frame linkage is unknown. No new masks, presence/footprint evidence,
calibration or procedure adapters are supplied by this measurement. No live
gate change, paid calls, GPU or robot movement. Existing86-test implementation
result remains distinct from physical scene acceptance; no source changed here.

The result improves over the earlier ring layout in the same native resolution
and camera view, but the sheet/pose and layout also changed, so no isolated
causal attribution to finer pen marks is justified. Do not redraw until
independently checking distances. Next: check mark9 at x80/y90mm from mark1's
intersection, then verify the top midpoint6 at60mm between1and2. Preserve actual
measurements even if they disagree with target coordinates. If physical values
are confirmed, resolve image-reading uncertainty/camera geometry rather than
continue changing the paper to match predictions. Robot recalibration/drawing
waits for explicit operator continuation and physical registration work.

## Operator correction: cross9 at85–90

Miguel reports cross9 is actually85–90, interpreted as x85/y90mm. A separate
correction record changes only that physical coordinate. Image intersections,
four fitting corners, split and2px bar are unchanged; previous results remain
preserved. [Corrected diagnostic](clean-cross-sheet-correction-01-reprojection-2026-10-27.json)
remains FAIL: cross9 error18.569767px, overall RMS8.469682px. Other errors are
unchanged, including mark6 at3.235px. The reported coordinate increases the
image disagreement. Do not reject an operator measurement just to reduce error
or move a mark to fit predictions. Confirm the measurement origin is cross1's
intersection rather than the sheet edge; original image centre readings and
other physical coordinates remain possible uncertainty sources. No acceptance.
