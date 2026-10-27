# After-dinner native-resolution marker check

The operator adjusted lighting and camera framing. A new main-stream still
`marker-framing-check-194029.jpg` was saved at **2880×1616**, with all nine green
marks visible and margin around the marked area. This is a new camera pose and
stream profile; previous v2 pixels/homography were not reused or scaled.

All centres were read manually from a 2× nearest-neighbour crop in native pixel
coordinates and frozen before residual computation. Operator physical positions
remain those in `markers-2026-10-27.txt`. The green circles are thick/blurred;
mark 7 also overlaps the black drawing. Centre uncertainty is several native
pixels and has not been independently quantified. No adjusted centres or new
physical positions were inferred from residuals.

| Mark | Native image centre px | Split | Error px |
| --- | --- | --- | --- |
| 1 | 884, 836.5 | fit | <0.000001 |
| 2 | 1302, 737 | fit | <0.000001 |
| 3 | 1037, 1107 | fit | <0.000001 |
| 4 | 1528, 971 | fit | <0.000001 |
| 5 | 1270, 1042 | validation | 0.499 |
| 6 | 1089, 786 | validation | 8.634 |
| 7 | 1409, 852 | validation | 5.400 |
| 8 | 955, 970 | validation | 4.582 |
| 9 | 1319, 948 | validation | 7.071 |

Held-out RMS **5.915379 px**, maximum **8.634428 px**: **FAIL** against the same
2 px bar. These are native pixels in a different resolution/view; raw pixel
errors cannot be compared as physical accuracy against the earlier 896×512
frame. No robot registration is accepted. No masks exist for this new frame;
presence and footprint remain unknown, not inferred from visual staging.
The existing 45-frame inventory is the earlier batch, separate from this new
geometry-only capture. No paid calls, GPU, motion or live gate changes.

[Frozen readings, hashes and residuals](after-dinner-reprojection-2026-10-27.json).
Private source images and reading crops remain in the Movies capture folder.

Next: keep the setup fixed and independently verify physical centre distances.
First check mark 6: it must be 55 mm along the top row from the **centre of mark
1**, not from the sheet edge. Mark 9 must be x80/y90 mm from that same origin.
Do not move/redraw marks to match the fitted projections. Report what is
actually measured; resolve any discrepancy explicitly before another fit.
