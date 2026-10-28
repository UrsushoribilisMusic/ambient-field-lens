# Codi — frozen-label prompt expansion, 28 October 2026

Starts from fresh main4eafbe5 after PR4/2/5/6 and Miguel's independent label
review landed. User authorizes larger held-out scoring only against those frozen
labels. No new topic labels, candidate steps, manual passages, controls, frames,
physical scene changes, or diagnostic-lock task enters this experiment.

1. Declare24 new held-out prompt wordings (12 locking,12 narration), with exact
candidate/context/image inheritance from the human-reviewed18 pairs. Keep the
original fit(calibration/port), validation(pressure/approval), test(locking/
narration) groups. Include original36 records as audit controls, never pool old
test with the novel-wording primary metric.84records total,48 new test records.
2. Fix true-prefill hidden layer27 and norm/head lens layer22 from the prior
round before scores; fit direction/anchor only on original12 fit records.
No trajectory extension, new layer search, test tuning or generated answers.
3. Pure CPU invariance/partition tests and native tokenizer/prefix/image preflight
before one finite non-retrying $4 window. Same budget ledger and pinned model.
Capture only actual pre-candidate residuals; no candidate tokens consumed.
4. Report new-wording test separately from known controls, including all pair
margins and only TWO independent test topics. This increases wording coverage,
not independent tasks, scenes, labels or visual-grounding evidence. No new
scoring beyond exact reviewed evidence/candidate/frame combinations.

Future aborted-job/stale-lock diagnostic reasoning is a separate backlog issue.
/assist stays default-deny; no green wiring, fixture frozen, no Meta calls.

## Complete — independent review pending

One $4 attempt578c40bb-df38-4b11-a342-f612685d75bd ran109.33s;84 actual
prefix-only forwards, zero candidate tokens consumed. Hidden fixed-layer27:
new-wording AUROC1.000; norm/head lens fixed-layer22:0.970486. Both order24/24
pairs correctly; old six-pair controls both1.000. Only two independent test
facts/topics, so topic sign-test p0.5; this is wording robustness, not a new
independent grounding benchmark or Jacobian advantage. No labels changed.

Independent CPU analysis exactly matches every pair margin/metric. Original
prefix scores reproduce previous true-prefill scores (hidden drift0; lens
maximum1.11e-16). Native preflight84 measured prefixes, maximum363 tokens.
28 research tests:27 pass, one unchanged Torch-dependent skip.

App ap-NCHRhgTtXrcmAhzGnlmxrX stopped, final containers[]. $22 cumulative
conservative reservations under$100 grant, not invoices. Final client log wait
timed out after report/ledger completion; no rerun and no function failure.
No further calls queued. /assist and fixture unchanged, green remains denied.

Draft PR8: https://github.com/UrsushoribilisMusic/ambient-field-lens/pull/8
Separate diagnostic backlog: https://github.com/UrsushoribilisMusic/ambient-field-lens/issues/7
Report: docs/verification/heldout-wording-results-2026-10-28.md/.json.
Private overview: ~/Movies/Ambient-Field-Lens/2026-10-28/heldout-wording/review.html.
