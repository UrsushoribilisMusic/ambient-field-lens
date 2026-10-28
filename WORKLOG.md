# Codi — archived visual grounding pair authoring, 28 October 2026

User requests four image-only checks: paper correctly positioned, footprint
inside paper, pen made contact, drawing has no unintended blank areas. No new
filming or model/SAM/GPU calls. Miguel must review EVERY pair before scoring;
manual-only answerability is excluded, not retained as a control success.

Start from fresh main9e55904. Inspect archived full frames and supporting clips;
author the same question/neutral text for pass and fail image conditions. Keep
source provenance and provisional labels separate from future model inputs.
No labels signed for Miguel, no accepted geometry fabricated, no conversion of
pen presence into contact, no treating intentionally empty outline interiors
as defects. Reject/flag evidence that cannot establish a requested check.

Folds are scene/family grouped before scoring, never split adjacent frames of
the same clip across fit/validation/test. With only four checks this is a seed
review set, not an accuracy benchmark. Where no honest archived pass/fail pair
exists, record the missing evidence rather than synthesize an image or invent
an overlay/nominal robot registration. The complete reviewed set is required
before any scoring/GPU eligibility. /assist default-deny; fixture unchanged.
