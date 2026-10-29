# Submission — Ambient Field Lens

## Problem

Operators set up machines by guesswork: uncalibrated equipment, wrong
attachments, missing steps discovered mid-job. A wearable assistant that
answers from confidence instead of evidence makes this worse, not better.

## Approach

A safety-gated assistant that demonstrates grounding behaviorally. Every
answer carries its evidence — retrieved manual passage, frame and mask
receipts, an explicitly uncalibrated score — and the system refuses (amber,
never green) whenever anything is missing, unmeasured, or unvalidated.
Groundedness is a property of the composition: provenance, hash bindings,
and fail-closed defaults. No model weights were harmed, trusted, or tuned:
thresholds were never set to produce a passing screen.

## Demo (filmed live, two cameras, no cuts)

- Evidence card: top-down rig framing → paper candidates, manual chunk,
  uncalibrated score, everything else declared unverified.
- Refusals: displaced paper, wide angles, missing pen context — each names
  the fault and the correction.
- Coverage repair (pending shoot): a genuinely uncovered question refuses;
  a human authors the missing passage; re-ingest flips the verdict input.
- Timelapse: a full correct drawing under the close — the operation refusal
  protects, never the system's approval (green does not exist).

## Results

- Live loop proven on camera repeatedly, zero provider failures across the
  shoot windows; every refusal correct against its framing.
- Four negative weight results, all in-repo: contrastive 0.575; Jacobian
  lens 0.861 vs plain 0.889; trajectory retired; live prefill −0.018 vs
  −0.015 (supported vs absurd, no separation). Failed transfer, not failed
  method: protocols validated on text grounding, deployed on a visual task.
- A validated coverage threshold from human near-miss labels is the one
  open measurement; the film discloses the readout as uncalibrated until
  it lands.

## Limits (spoken on camera)

- Amber-only: no green steps, no red blocks, no machine instructions.
- No capture-time proof: yesterday's photograph passes every check.
- Autonomous masks are candidates, never presence or approval.
- The grounding number is shown, not trusted.

## Disclosure

Clean-room repo; prior art declared in `docs/existing-work.md`. Calibration
labels human-reviewed; scoring only on frozen labels. Spend: Modal grant +
metered Meta API; Baseten credits used only for offline wording. Nothing
withheld that a judge needs to reproduce the claims.
