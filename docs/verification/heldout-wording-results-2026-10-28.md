# Frozen-label wording robustness — 28 October 2026

Miguel's independent labels on main4eafbe5 remain unchanged: six reviewed
candidate/support facts and clean unrelated controls. This round adds **24 new
question wordings**, using only identical reviewed candidate/context/image
combinations. No new fact labels were created or inferred across changed evidence.
New wording was authored by Codi; Miguel did not independently review each new
question. The target is support for the SAME fixed candidate in the supplied
context, not answer correctness under a newly generated response.

## Frozen protocol and result

Original fit: calibration/port,12 records. Validation: pressure/approval,12.
Held-out fact topics: locking/narration. Primary test: new wording only,
48 records /24 pairs; old test12 records /6 pairs are separate controls.
Model and images unchanged. True prefill only: input is truncated immediately
before the candidate; **zero candidate tokens consumed**,84 model forwards.
Readout layers frozen BEFORE new scores: hidden27, norm/head lens22. Fit-only
means/directions use original fit12; no new layer/point selection or thresholds.

| Estimator | Fixed layer | New wording AUROC | New pair ordering | Legacy control AUROC |
|---|---:|---:|---:|---:|
| Hidden contrastive |27|1.000000|24/24|1.000000|
| Final-norm/full-head Jacobian lens |22|0.970486|24/24|1.000000|

Both validation AUROCs are1.000, descriptive only; neither influences the fixed
settings. Both methods correctly order all24 new pairs, while pooled score ranks
overlap for the lens across pairs, giving AUROC0.970486. No Jacobian advantage.

**Only TWO independent held-out fact/topic clusters remain.** More paraphrases
do not create independent tasks or scenes; topic-level two-sided sign-test p=0.5
for both. This is a wording robustness extension of known facts, not a fresh
independent grounding benchmark. The same camera scenes recur in the folds,
and questions generally do not require the images. No visual readiness,
operator instruction correctness or deployment threshold has been validated.
The lens is a complete final-norm/unembedding readout derivative at fit-only
anchors, not an end-to-end transformer Jacobian. Extra trajectory scoring stays
retired; the earlier failed certainty calibration stays failed.

## Audit and resources

Independent CPU recomputation from saved score arrays exactly matches both
remote reports, including every pair margin and old/new cohort count.
True-prefill legacy score drift versus the prior teacher-forced prefix capture:
- Hidden: maximum absolute difference 0.
- Lens: maximum absolute difference 1.11022302463e-16.

Native CPU preflight measured all84 prefix boundaries and image tensors; maximum
prefix363 tokens. Review hash and exact parent candidate/context/frame identities
were verified before allocation. Six new CPU tests cover inheritance, partitions,
actual candidate exclusion, fit isolation and non-pooled primary reporting.
Research suite28 tests:27 passed, one existing Torch-dependent skip (the unchanged
JVP implementation was tested separately in the earlier Torch CPU environment).

One $4 attempt `578c40bb-df38-4b11-a342-f612685d75bd`, function109.33s;
peak CUDA allocation65,133,145,600bytes. Total local
conservative reservations$22 under the$100
grant, including previous attempts/CPU allowance; not invoiced spend. App
`ap-NCHRhgTtXrcmAhzGnlmxrX` stopped; final container inventory[]. No retries or
further GPU work queued. A final-client-log wait timed out AFTER report/ledger
completion; the function and app completed successfully, with no repeat call.

/assist remains default-deny, fixture frozen, no green wiring, model sampling,
Meta calls or robot activity. Aborted-job/stale-lock diagnostic reasoning is
separate [backlog issue7](https://github.com/UrsushoribilisMusic/ambient-field-lens/issues/7),
not a label correction or a member of this set.

[Protocol](../heldout-wording-protocol-2026-10-28.md) ·
[Manifest](heldout-wording-manifest-2026-10-28.json) ·
[Evidence JSON](heldout-wording-results-2026-10-28.json) ·
[Independent label review](label-review-2026-10-28.md) ·
[Draft PR8](https://github.com/UrsushoribilisMusic/ambient-field-lens/pull/8)
