# Teacher-forced trajectory result — 28 October 2026

One authorized $4 A100-80GB window; frozen camera-conditioned 18 pairs/36 records, same folds and BF16 checkpoint. Exactly 36 forward passes, no sampling or generated commands. All 52-layer residuals for every candidate token plus its preceding token are saved privately on the Modal artifact volume.

The prior “prefill 0.889” endpoint was the LAST teacher-forced candidate token. Here true_prefill means the residual immediately before candidate tokens; early is the first token, mid is ceil(n/2), late is the last token. This is one-pass causal teacher forcing, not an incremental cached generation benchmark.

| Estimator | Point | Selected layer (zero-based) | Validation AUROC | Test AUROC | Pair ordering | Topic sign-test p |
|---|---|---:|---:|---:|---:|---:|
| hidden_contrastive | true_prefill | 27 | 1.000000 | 1.000000 | 6.0/6 | 0.500 |
| hidden_contrastive | early | 27 | 1.000000 | 1.000000 | 6.0/6 | 0.500 |
| hidden_contrastive | mid | 4 | 1.000000 | 1.000000 | 6.0/6 | 0.500 |
| hidden_contrastive | late | 4 | 1.000000 | 0.888889 | 6.0/6 | 0.500 |
| norm_head_jacobian | true_prefill | 22 | 1.000000 | 1.000000 | 6.0/6 | 0.500 |
| norm_head_jacobian | early | 27 | 1.000000 | 1.000000 | 6.0/6 | 0.500 |
| norm_head_jacobian | mid | 4 | 1.000000 | 1.000000 | 6.0/6 | 0.500 |
| norm_head_jacobian | late | 4 | 1.000000 | 0.861111 | 6.0/6 | 0.500 |

## Preregistered decision

- **hidden_contrastive: retain_for_review**. Validation selected early, layer 27; held-out AUROC 1.000000, delta+0.111111 versus 0.888889.
- **norm_head_jacobian: retain_for_review**. Validation selected early, layer 27; held-out AUROC 1.000000, delta+0.111111 versus 0.888889.

**Control changes the interpretation:** true pre-candidate scoring also reaches 1.000 for both methods. Thus the preregistered comparison beats the old final-token 0.889 endpoint, but there is no demonstrated incremental value from consuming candidate tokens, and no Jacobian advantage. **Final recommendation: retire the extra generation-time scoring for this task.** Preserve the positive old-endpoint comparison for review, but do not add trajectory complexity or claim a generation-time benefit. Pair ordering was already 6/6 at the old endpoint and remains 6/6.

All three trajectory points reach validation AUROC 1.0. Early wins the declared tie rule; validation did not demonstrate that it is the best timing point. Layer selection uses validation only; point selection also uses validation only, ties early→mid→late. True prefill is a control, never a tuning option. All preregistered points are reported; unselected test peaks do not justify retaining a failed selection or another window.

Independent CPU recomputation from saved all-layer score arrays exactly matches both remote reports, including every selected point/layer, margin and metric. Late-score reproduction versus prior camera run:

- hidden_contrastive: maximum absolute all-layer late-score difference 0.
- norm_head_jacobian: maximum absolute all-layer late-score difference 0.

## Limits and state

Only two held-out topic clusters; paraphrases are correlated. Labels were authored/reviewed by an agent, independent human review pending. Context-present discrimination is not generated-answer correctness, causal source attribution, pen detection or readiness. The same camera scenes recur in all folds, and these questions generally do not require visual evidence. The Jacobian method is the complete final-norm/unembedding readout derivative at fit-only anchors, not a full-network Jacobian. Prior failed certainty calibration remains failed.

Function time 415.03s (excludes queue/build/startup); peak CUDA allocation65,023,215,104 bytes. Reservation `a7a0324d-87c2-4a09-b988-ea04c8e7825b`: $4, $18 total reserved under the $100 grant including the $2 CPU/build reserve. These are conservative reservations, not invoiced spend. No retries or additional GPU calls. Final container inventory empty; app stopped.

Fixture frozen, /assist unchanged and default-deny, no green wiring.

## Review and merge order

PR4 merged 9396cbf; PR2 merged d1dfe4d with negative Platt-coefficient note; PR5 merged 31e73d6 after PR2. Concurrent fleet session completed these merges while Codi was preparing them. This new branch starts directly from 31e73d6 and PR6 targets main, carrying only trajectory work. No stacked unreviewed dependency lands through this PR.

[Protocol](../trajectory-protocol-2026-10-28.md) · [Machine-readable evidence](trajectory-comparison-2026-10-28.json) · [Draft PR6](https://github.com/UrsushoribilisMusic/ambient-field-lens/pull/6)

Validation: 22 distinct research tests covered across CPU environments (one Torch-dependent test run separately), 107 backend tests with 7 expected private-media skips.
