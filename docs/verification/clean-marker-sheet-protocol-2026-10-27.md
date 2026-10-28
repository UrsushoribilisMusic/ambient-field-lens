# Proposed clean-sheet reset after ambiguous ring-centre readings

Operator proposed removing pad, marking a fresh sheet away from robot, replacing
it and recalibrating/redrawing if needed. Cleared mark6 still does not provide
a confidently readable intersection. Private capture `mark6-cross-clear-200058.jpg`
preserves this observation. No image point or accepted geometry is inferred.

Use a new marker revision and surface pose; preserve all prior records and
failed results. This new layout intentionally uses 60mm midpoint marks, not
the previous disputed55/65mm coordinates. It must never be paired with old
image annotations. The fit/validation split and2px bar remain unchanged.

## Operator layout

Take a fresh flat sheet, mark away from the robot with a ruler and fine black
pen. Each marker is a small cross, about4mm across, with one clear intersection;
no circles or thick strokes. Put numbers at least5mm away from intersections.
Allow about10mm sheet margin left/right of the120mm zone and clear binding at
the top. Choose the top-left cross as origin, not the sheet/book edge.

| ID | x mm | y mm | Role |
| --- | --- | --- | --- |
| 1 | 0 | 0 | top left; fit |
| 2 | 120 | 0 | top right; fit |
| 3 | 0 | 120 | bottom left; fit |
| 4 | 120 | 120 | bottom right; fit |
| 5 | 60 | 120 | bottom midpoint; validation |
| 6 | 60 | 0 | top midpoint; validation |
| 7 | 120 | 60 | right midpoint; validation |
| 8 | 0 | 60 | left midpoint; validation |
| 9 | 80 | 90 | interior; validation |

Coordinates as viewed: x right; y toward viewer/down the page. Use ruler
distances between intersections and record actual measurements/deviations;
the table is the target layout, not verified physical evidence. Confirm the
120mm spans and60mm midpoints before placing it under the robot.

Replace and secure the pad. Leave the camera at current view if all nine
crosses remain visible. The operator handles pad placement around the stationary
pen/arm; no software motion command is issued. Capture the new setup and read
all nine native pixels before fitting1–4 and independently validating5–9.
No old pose/calibration validity is assumed after removing/replacing the pad.

First establish paper-plane registration; then measure linkage to fixed robot
coordinates and revisit calibration before a supervised drawing. Recalibration
does not establish camera registration or make a moving paper define a fixed
robot footprint. No geometry pass, live readiness or GPU eligibility yet.

No paid calls/GPU, `/assist` unchanged, $20 ceiling retained.
