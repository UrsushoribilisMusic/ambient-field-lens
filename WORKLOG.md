# Codi — bounded teacher-forced trajectory round, 2026-10-28

User authorizes exactly one new $4 Modal window, same frozen 18 pairs, folds,
checkpoint, camera payload and ledger. No sampling: one causal forward per
record captures every candidate-token residual at all 52 decoder layers.

1. Freeze protocol and meaningful CPU tests before allocation. Define first,
middle and last candidate token, plus true pre-candidate control. The old 0.889
"prefill" baseline was actually the final teacher-forced candidate token.
2. Reuse fit-only contrastive and full-vocabulary norm/head Jacobian estimators;
choose layer and trajectory point using validation only. Compare selected
held-out AUROC strictly against 0.888888888888889; no test-driven sweep.
3. CPU checkpoint/token-boundary preflight, reserve exactly one $4 attempt,
persist per-record trajectories and score reports. No sampling or execution,
no retries or extra GPU windows, scale to zero and verify shutdown.
4. If the validation-selected trajectory fails to beat the prior endpoint,
retire it. Report limitations, ledger, independent CPU audit and merge state.

PR4, PR2 (negative Platt line included), PR5 were merged by the concurrent
fleet session in that order (9396cbf, d1dfe4d, 31e73d6). This branch starts from
main 31e73d6; it does not carry those changes through a stacked PR. The local
recal worktree contains unpushed duplicate documentation-only commits from the
concurrent update; no shared changes were reset or overwritten.

Fixture frozen. /assist default-deny. No green wiring, new filming, Meta calls,
model sampling, threshold changes or hardware commands.
