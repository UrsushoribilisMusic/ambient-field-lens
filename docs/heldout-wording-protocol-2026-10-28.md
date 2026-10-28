# Frozen-label held-out wording expansion — 28 October 2026

User authorizes new scoring only under Miguel's label freeze on main4eafbe5:
[review](verification/label-review-2026-10-28.md). All six candidate/support
judgments stand, no corrections; all controls unrelated. Never create new
fact labels, passages, candidate steps, frames or lock-diagnostic cases here.

The base36 records remain exact audit controls. Add24 new held-out prompt
wordings,12 each for locking and narration, preserving the exact candidate,
support/control excerpt and image combination of a reviewed parent pair.
Source hashes, each parent mapping and every new question are frozen in
[manifest](verification/heldout-wording-manifest-2026-10-28.json) before scores.
Label inheritance is permitted only under these tested identity invariants;
Miguel did not separately review the newly authored wording. The target remains
candidate support in supplied context, not generated-answer correctness.

Unchanged topic folds: calibration/port fit (12 records), pressure/approval
validation (12), locking/narration test. New primary test comprises only the
48 new-wording records /24 pairs; old test12 records /6 pairs are reported
separately, never pooled to inflate primary performance. Total84 records.
This increases wording coverage, not independent topics: there are still only
TWO test clusters. Frames recur across all folds and generally are not needed
to answer these questions; no visual-grounding/scene-robustness claim.

Frozen estimator settings from the previous round: hidden contrastive layer27,
full-vocabulary final-norm/head Jacobian lens layer22 (zero-based). No new layer
or trajectory-point selection. Actual prefill only: native image/prompt inputs
are cut immediately before the first candidate token; no candidate token is
consumed, no sampling or generated instruction. One model forward per record.
Fit direction and lens anchor only on the original12 fit records, using the
unchanged estimators; validation AUROC descriptive only. Report new-wording
AUROC, every paired margin, pair ordering and topic-level sign test. No claims
of statistical independence for paraphrases, or advantage over actual prefill.
The lens is not the Jacobian of the complete transformer.

CPU invariant/partition tests, checkpoint staging and native prefix/image/token
preflight must pass first. One finite $4 non-retrying A100-80GB window under the
existing$100 grant ledger, same timeout/startup/single-container limits and2s
scale-down. Record every failure, save measured artifacts, verify app stopped.
Do not rerun a failed/completed tagged attempt. No other scoring is authorized.

Start from fresh main. Separate stale/aborted-job lock reasoning goes only to
the backlog, not this pair set. Fixture frozen, /assist default-deny, no green
wiring, Meta calls, geometry acceptance or hardware activity.
