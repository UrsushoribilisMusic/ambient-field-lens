# Ruler follow-up: unresolved measurement precision

**Operator scope clarification:** this is a Reolink development fixture, not
the intended phone camera. Stop further manual sheet modifications. The raw
2px check remains failed; no phone-camera performance follows from it. Applying
the same native-pixel bar at2880px instead of896px is3.21times stricter relative
to image width. Review the physical error budget and explicitly bound camera
profile/resolution before the phone validation round; do not retrospectively
change this result or silently relax contract v2. Other CPU replay/adapter work
can proceed with geometric containment unknown. No additional operator action
needed on this sheet for now.

Miguel confirms both rectangle spans120mm and centre lines60/60mm. He reports
cross9 approximately78.5/92mm, interpreted as x/right and y/down from cross1's
intersection. This supersedes earlier approximate85/90 and20right/30below
reports. The4mm paper grid does not change these ruler-reported values.
The operator's approximation remains explicit, with no invented uncertainty.

Replayed the frozen native image intersections from `rectangle-centrelines-201939.jpg`.
No image point or fit corner changed. Same corners1–4 fitting, points5–9 held
out,2px bar. [Detailed raw report](rectangle-ruler-confirmed-reprojection-2026-10-27.json).

| Held-out mark | Error px |
| --- | --- |
| 5 | 1.010 |
| 6 | 3.062 |
| 7 | 1.043 |
| 8 | 1.631 |
| 9 | 4.954 |

**RMS2.781517px, max4.953930px — FAIL.** Approximate ruler coordinates and
roughly1–3px unquantified manual reading ambiguity prevent an acceptance claim.
The centre10 is still hidden by the pen and explicitly unknown. No robot
linkage or presence/footprint pass is established. Corrected physical inputs
and earlier records are preserved separately; none were selected by residual size.

Stop modifying the sheet. Next work should resolve independent image-coordinate
precision and physical measurement uncertainty with this setup preserved. More
redrawing/point moving or a tolerance change is not warranted by this evidence.
An independent reviewer should check the frozen native intersections and ruler
origin before another fit. A sharper future capture needs its own native
annotations/profile; no scaling or tuning the existing readings to predicted
positions. No calibration/drawing, paid call, GPU, backend change or threshold
lowering. Implementation86-test result remains separate from this failed
physical validation. $20 ceiling retained.
