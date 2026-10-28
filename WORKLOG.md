# Codi — paired grounding/J-space comparison (2026-10-28)

Miguel confirmed the $100 Modal hackathon grant on workspace miguel-40686,
expiring 2027-10-31. This supersedes the prior $20 authorization; it does not
relax experiment or shutdown discipline. No active Modal containers at start.

1. Declare paired present/removed manual-evidence cases and fixed topic folds,
   using external Ross question references and the already-ingested manual
   snapshot. Define both estimators before model scores. No old matrices,
   vectors, extraction code or chunkers are copied into this repository.
2. Write fresh forward-only J-space/logit-lens extraction and contrastive
   baseline on exactly the same activations/cases/folds. State precisely which
   Jacobian approximation is measured; do not call a last-layer shortcut the
   full network Jacobian. Report paired sensitivity and held-out discrimination.
3. CPU tests and token/checkpoint preflight, then a finite reserved A100-80GB
   window, no retries, one container, scale to zero. Persist artifacts after
   each stage; ledger every attempt even failure. Check live containers after.
4. Publish small provenance/results reports, preserve failed earlier certainty
   results, and update daily. /assist untouched, no green wiring, fixture frozen.

Branch is based on the existing clean-room recalibration PR #2 checkpoint;
this comparison is a separate reviewable unit and does not require /assist
integration or any physical robot motion.

## Complete — pending independent review

Text smoke and real-camera paired rounds completed; measured results and CPU
recomputation are in docs/verification/paired-comparison-2026-10-28.md/.json.
Hidden test AUROC0.889, norm/head Jacobian0.861 in both rounds; no lens advantage.
Two independent held-out topic clusters only.16research/preflight and19backend
regressions covered. $8new GPU reservations, $14total including prior and CPU;
all five launch apps stopped and final container inventory empty. No queued
GPU work, no automatic follow-up window. Fixture and /assist unchanged.

Draft PR5: https://github.com/UrsushoribilisMusic/ambient-field-lens/pull/5
stacked on PR2. Do not repeat these runs because the first client's TorchVersion
transfer failed: all artifacts were recovered and independently audited.
Next work is human label review and genuinely camera-dependent held-out cases,
not another sweep or a lower confidence threshold. Local private review page:
~/Movies/Ambient-Field-Lens/2026-10-28/paired-comparison/review.html .
