# Independent label review — Miguel, 2026-10-28

Scope: six paired topics (18 pairs / 36 records) from
`docs/verification/paired-case-manifest-2026-10-28.json`. Reviewed
step-against-support only; control passages confirmed as unrelated
by design (confirming they do not support the step is the check).

Reviewer is the operator and rig owner; verdicts are his own words,
paraphrased here from chat. No agent approval under his name.

| Topic | Verdict | Correction |
| --- | --- | --- |
| calibration | supported | none |
| port | supported | none (control text initially confusing; step correct as stated) |
| pressure | supported | none |
| approval | supported | none |
| locking | supported with note | none to this pair; see annotation |
| narration | supported | none |

Controls: clean on all six (no control passage supports its step).

Annotation (locking): the real operator query is usually "no jobs are
executing, why?" — an active lock from an aborted job the system did not
catch is one possible reason. The pair as stated is correct, but a future
diagnostic-reasoning task over lock state is wanted. Not a correction;
a new task.

Freeze: these labels are fixed before any new scoring. Corrections: none.
