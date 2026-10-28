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
