# Paired footing readout — frozen protocol, 28 October 2026

Research only; no /assist changes, robot motion, or product verdict. The earlier
failed confident-minus-uncertain/answerability experiment remains failed.

## Cases and folds

Fresh task-specific pairs from the already-indexed Ross manual snapshot. Same
question and same teacher-forced candidate step; only supporting context changes.
The negative has an unrelated manual excerpt of similar length, not a magic
"evidence missing" label. The target is **support present in supplied context**,
not correctness, physical readiness or truth of a generated answer. Candidate
steps are explanatory text only; no command is executed. Hand-author/review the
support span and candidate before extracting model scores. Keep full source
passages outside Git and images; retain digests and sources in the manifest.

Six disjoint topic/support-span groups, three question paraphrases per group:
18 pairs / 36 records. Fixed groups 0–1 fit directions/anchors, 2–3 choose layers,
4–5 untouched test. Each group has both classes. Pair members and paraphrases
never cross partitions. This tiny pilot cannot establish broad generalization
or viewpoint invariance. No physical measurements or images are invented.

## Estimators

Both get the **same** Glimmer residuals, at the last candidate-step token, all
52 decoder layers, pinned BF16 checkpoint and tokenizer. No generation changes
between arms. No prior vectors, Canis matrices, extractors or chunkers imported.
The declared external method reference is the Canis disposition draft, section3
(J-space/discriminant concept only); fresh implementation here.

- Hidden contrastive baseline: unit(mean(h_positive)-mean(h_negative)) on fit
  only; cosine scores; choose layer by validation AUROC, smallest layer on ties.
- Full-vocabulary Jacobian lens: at each layer's fit-only mean residual a,
  F(h)=lm_head(final_norm(h)); compute z=DF(a)[h-a] by exact forward-mode JVP of
  final_norm followed by the entire unembedding, with FP32 readout arithmetic.
  Fit the same contrastive direction in z-space; choose layer by the exact same
  validation rule. All vocabulary coordinates are used, no token subset,
  randomized sketch, diagonal-only approximation, or transferred layer choice.

This is the **complete Jacobian of the norm/unembedding readout**, evaluated at
a declared training anchor. It is a local logit-lens linearization, NOT the
Jacobian of all intervening transformer blocks and NOT causal evidence that
an answer consulted a passage. That distinction must stay in all reports.
No entropy blend, confidence threshold or certainty proxy is reused.

Report every layer's validation AUROC, frozen test AUROC, sign-correct paired
accuracy (ties count one half), raw pair margins, exact two-sided sign test,
group-bootstrap AUROC uncertainty, sample counts and resource/runtime metadata.
No test-set sign flips, refitting, layer tuning, threshold tuning or selective
case removal. Neither readout can unlock green. Corpus quality and generated
answer support require separate human review and larger held-out data.

## Execution

Miguel's grant confirmation: $100 active in miguel-40686 on 2026-10-28, expires
2027-10-31. It supersedes $20 locally; previous reservations remain visible.
Reserve $4 per non-retrying A100-80GB attempt, with 45min function / 5min startup
limits, maximum one container and 2s scale-down, persist partial results and
ledger failures. $2 CPU/build reserve retained. Verify checkpoint CPU marker,
all prompt token lengths, frozen manifest and CPU tests before allocation.
After the finite run, stop the app if necessary and save container inventory.
Reservations are conservative bounds, not provider invoices or a workspace cap.

Rates/control references: https://modal.com/pricing and
https://modal.com/docs/guide/scale . JVP semantics:
https://docs.pytorch.org/docs/stable/generated/torch.func.jvp.html .
