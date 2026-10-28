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
exists, record the missing evidence rather than synthesize a photograph or claim
unvalidated robot registration. A separately supplied, explicitly reviewed
image-space target may define a containment question without a robot mapping. The complete reviewed set is required
before any scoring/GPU eligibility. /assist default-deny; fixture unchanged.

## Review packet ready — no scoring authorization

Four pairs /8 conditions from6 unique native crops, source hashes and original
frame times retained. Proposed paper placement uses S28 before/after; supplied
image-space footprint uses the same S28 family in fit. Contact uses S06 at30s
versus60s in validation. Missing outline edge strokes use S19/S22 in test.
Only ONE test pair; no accuracy/calibration or independence claim.

Raw frames never retouched. Reviewer sees native crops and original source
links; the cyan target is a separate SVG layer, held fixed, NOT a recovered
robot path or accepted calibration. Miguel must approve that scope or reject
the pair. Pen presence is not substituted for visible contact; unknown blocks.
Outline interior is intentionally empty; only missing edge strokes are asked.

Private review.html lets Miguel enter his own labels/notes/name and export a
digest-bound JSON. Every member starts unreviewed. Human reviewer/labels remain
null in the committed draft. No approved human artifact created by the agent.
Six CPU gate tests pass: partial, text-answerable, unknown, hash drift and fold
leakage fail closed; validated review still launches no GPU or green verdict.
No provider/GPU/SAM calls, scoring, new filming, model sampling or hardware
activity. /assist untouched. Local grant ledger unchanged at$22 reserved.

Review: ~/Movies/Ambient-Field-Lens/2026-10-28/visual-grounding-review/review.html
Protocol: docs/visual-grounding-pair-protocol-2026-10-28.md
Manifest: docs/verification/visual-pair-manifest-2026-10-28.json
