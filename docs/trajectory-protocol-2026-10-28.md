# One-window candidate trajectory scoring — 28 October 2026

Same immutable camera-conditioned 36 records /18 pairs, checkpoint, tokenization,
image budget, support labels and topic folds as the paired comparison. Input
SHA256: 1f8fe74d3300b7aa09f1a76e723e5a323e686c5289c72fb95dfc8066bc33c17a.
No new cases, images, paid Meta calls, sampling, generation or robot activity.

One causal forward pass per record with the full fixed candidate teacher-forced.
At all52 decoder layers save every candidate-token residual plus the immediately
preceding residual. Preserve token IDs, exact measured candidate start, frame
SHA, candidate hash, lengths and source provenance. With causal attention,
future teacher-forced tokens cannot affect earlier positions; no later-token
averages or label-dependent slicing. Native model eval, use_cache=False.

Fixed points, measured relative to exact candidate suffix in the native encoding:
- true_prefill: preceding token, zero candidate tokens consumed (control).
- early: first candidate token consumed.
- mid: ceil(candidate-token-count/2) consumed.
- late: final candidate token consumed.

The previously named "prefill" 0.888888888888889 score was measured at the LAST
candidate token. It is the late/end-point baseline, not a pre-generation score.
No claim of incremental cached autoregressive execution: this is trajectory
scoring from one teacher-forced causal pass, as authorized.

At each point independently apply the unchanged fit-only hidden contrastive and
full-vocabulary final-norm/head Jacobian-lens estimators. Fit-only mean anchors,
no sign flip, no held-out fitting. Choose layer on validation only, smallest
layer on ties. Select one trajectory point per estimator on validation AUROC
only, ties early then mid then late. The true-prefill control cannot be selected.
Report all preregistered point/layer scores, but do not choose a deployment point
by looking at test scores. Retain each method only if its validation-selected
trajectory strictly exceeds 0.888888888888889 on held-out records; otherwise
retire. Unselected test peaks are descriptive, not a reason for another window.

Reproduce the old late hidden0.889 and lens0.861 measurements as audit controls;
report any discrepancy rather than adjusting it. No additional GPU attempt if
preflight/runtime fails; recover saved artifacts where possible. New reservation
exactly$4 in the existing grant ledger, 45min function/5min startup bounds,
no retries, one container, 2s scale-down; verify stopped afterward.

The norm/head lens is not a full-network Jacobian. Labels are agent-authored,
independent human review pending; two held-out topic clusters only. Scores are
support-present discrimination, not generated-answer correctness or visual
readiness. The same images recur across folds and questions generally do not
require looking at them. /assist remains default-deny; fixture and green wiring
untouched. Prior failed certainty calibration stays failed.
