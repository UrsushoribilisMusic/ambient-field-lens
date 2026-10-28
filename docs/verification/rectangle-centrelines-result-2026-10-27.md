# Rectangle and centreline diagnostic — physical coordinates unresolved

**Superseding clarification:** Miguel reports this sheet has4mm grid squares,
not5mm. Coordinates obtained by counting squares are therefore unverified.
No automatic80% scaling is applied: some distances may have come from a ruler,
and the origin/individual positions must be established from measurements.
Paper-plane/robot registration remains **unknown / not accepted**. The operator
need not redraw or move anything to resolve actual distances with a ruler.

Before that clarification, the operator reported cross9 was20mm right and30mm
below the drawn centre lines. This was interpreted as80/90mm under the assumed
60mm midpoint layout. New line intersections were hand-read in native2880×1616
frame `rectangle-centrelines-201939.jpg`, frozen before normalized DLT fitting
corners1–4 and validating5–9. The pen hides additional centre10; its pixel is
explicitly unknown, not inferred under the pen.

[Raw conditional diagnostic](rectangle-centrelines-reprojection-2026-10-27.json):
errors5–9=1.010/3.062/1.043/1.631/7.356px, RMS3.694776px, max7.356228px.
This fails2px **under the supplied coordinate assumptions**; it is not an
accepted measurement of physical registration while those coordinates remain
unverified. No pixels were altered to reduce errors. Previous readings/results
and the separate85/90 report are preserved as superseded hypotheses.

Next ask for actual ruler-only centre/intersection distances: top span1→2 and
left span1→3. Then establish midpoint offsets and cross9 from the rectangle's
measured edges. A uniform change of units alone cannot reduce pixel reprojection
errors: the mapping rescales accordingly. The4mm discovery does not by itself
diagnose every residual, and mixed measurement methods must not be silently
treated as one scale factor. No new fit until measured inputs are recorded.

No mask/presence/footprint pass, robot calibration, drawing, paid call, GPU or
live `/assist` change. $20 ceiling and default-deny retained.
