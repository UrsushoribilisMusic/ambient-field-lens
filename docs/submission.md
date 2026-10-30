# Submission — Ambient Field Lens

## Problem

Operators set up machines by guesswork: uncalibrated equipment, wrong
attachments, missing steps discovered mid-job. An assistant that answers from
confidence instead of evidence makes this worse, not better — and from the
outside, an answer read out of your manual and an answer improvised from
training look identical.

**This is not a RAG chatbot.** The product is the measurement and the refusal:
whether a passage in the operator's own documentation actually covers the
question, and what happens when none does.

## Approach

A safety-gated assistant that demonstrates grounding behaviourally. Every
answer carries its evidence — retrieved manual passage, frame and mask
receipts — and the system refuses whenever anything is missing, unmeasured or
unvalidated. Groundedness is a property of the composition: provenance, hash
bindings, and fail-closed defaults. Thresholds were never set to produce a
passing screen.

Two independent gates, and the film is about the first:

- **Coverage** — retrieval distance from the question to the nearest passage
  in the operator's corpus, against a calibrated threshold.
- **World checks** — is there a paper candidate in the frame, and does the
  drawing footprint fall inside its boundary, in millimetres.

## Built during the hackathon (Rule 4)

**Pre-existing, used as a test bench:** the Robot Ross Huenit arm and rig; the
ATF wiki corpus used as source documents; the Sovereign Mind wiki/console the
repair loop writes back into.

**Built here, Oct 26 – Nov 4:** the Field Lens iOS app on the Meta Wearables
DAT interface; the default-deny `/assist` contract on Modal; SAM 3.1 scene
gating with millimetre geometry; the Glimmer 30B prefill readout and the four
probe protocols that retired it; the coverage gate and its calibration;
immutable corpus versioning with a code-reviewed pin registry; and the
documentation repair loop end to end.

Code provenance is in `docs/existing-work.md`.

## Results

**The coverage gate is calibrated, not asserted.** 13 labelled questions,
threshold fixed at **0.760**; covered questions top out at 0.741.
Receipt: `docs/verification/coverage-calibration-2026-10-30.json`.

**The repair loop closed on camera, 2026-10-30.** The same question, before
and after a human improved the documentation:

| | chunk | distance | source |
|---|---|---|---|
| before | `8135308218c2c50d…` | 0.8199 | `atf-wiki/Topics/Calibration.md` |
| after | `59bb1a272e2ed09d…` | 0.3997 | `sm-faq/robot-ross-atf/fb-1793359723991-x33ca` |

Corpus `ross-manuals-2ca5f2f152267049` (38 records) → `ross-repair-ad3c9065b45ac2d3a0562011`
(39 records), the addition being one passage written and approved by a human
in their own wiki. `cited_chunk_changed: true`, `cited_text_changed: true`.
Nothing was retrained; the only thing that changed is the documentation.

**The negative result we are not burying.** Four independent probes for a
grounding signal in the model's own activations: contrastive 0.575; Jacobian
lens 0.861 vs plain 0.889; trajectory retired; live prefill **−0.018 supported
vs −0.015 unsupported** — no separation. The protocols validated on text
grounding and did not transfer to the live visual task. The score is pinned to
zero on the wire and the verdict does not read it.

Open weights are still the reason the attempt was possible at all: the readout
is taken on the residual stream at prefill, which a hosted API cannot return.

## Limits (stated on camera)

- No green steps, no red blocks, no instructions to touch the machine. The arm
  moves only on a human command, over a link the cloud never reaches.
- No capture-time proof: a receipt binds which frame, question, passage and
  masks went into an answer — never when the photo was taken.
- Autonomous masks are candidates, never presence or approval.
- **Distance is not relevance.** Two of the three labelled near-misses fall
  below the gate (0.668, 0.725), and an off-domain question measures 0.787 —
  closer than the legitimate near-miss at 0.820. Near-miss and absurd
  negatives have to be evaluated separately.
- The readout is reported and never trusted.

## Disclosure

Clean-room repo; prior art declared in `docs/existing-work.md`. Calibration
labels human-reviewed; scoring only on frozen labels. Spend: Modal grant +
metered Meta API; Baseten credits used only for offline wording. Nothing
withheld that a judge needs to reproduce the claims.
