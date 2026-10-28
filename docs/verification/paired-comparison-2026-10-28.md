# Paired readout comparison — 28 October 2026

**No demonstrated Jacobian-lens advantage.** The paired contrastive baseline
scored0.889 held-out AUROC; the full-vocabulary norm/head Jacobian lens scored
0.861. Both ordered all6held-out support/control pairs correctly. Camera
conditioning changed the scores, but not these ranking metrics. This is a
small controlled-context pilot, not evidence that either readout can authorize
an instruction. `/assist` and the frozen physical fixture are unchanged.

## What was actually compared

Fresh18pairs from six Ross manual topics: calibration, port selection, pen
pressure, preview approval, job locking and narration. Each pair shares the
question and a fixed teacher-forced candidate answer. A supporting exact
manual span is replaced by an unrelated manual span. These labels mean
**support present in supplied context**, not generated-answer correctness.
Codi (agent) authored/checked the pairs; independent human review is pending.
The negative spans are only approximately length-matched; lexical and length
cues remain potential confounds. These are new task-specific pairs, not the
older150-question answerability benchmark; that failed benchmark stays failed.

The same36records, model states, fixed folds and layer-selection rule were
used for both methods. Calibration/port topics fit; pressure/approval select
layers; locking/narration are untouched test topics. Three paraphrases per
topic never cross folds. Fit/validation/test each contain12records /6pairs.
All52layers were examined. Validation AUROC alone selected layer4zero-based
for both methods in both rounds (smallest layer wins ties).

| Input round | Hidden contrastive test AUROC | Norm/head Jacobian test AUROC | Correct test-pair ordering |
| --- | ---: | ---: | --- |
| Text-only smoke | 0.8889 | 0.8611 | 6/6for each |
| Same pairs + six real archived Reolink frames | 0.8889 | 0.8611 | 6/6for each |

The camera round uses native Glimmer image processing,256visual-token limit,
maximum375total tokens, and verified pixel tensors. Each pair shares the same
frame digest. S04missing-pen, S27clear/covered/clear, S28before-displacement
and S30displaced-paper frames retain original camera profile and coarse pose
metadata. Scene filenames/condition labels are not supplied as prompt text.
All six scenes recur across topic folds: this holds out question topics,
**not** camera viewpoints or scenes. No metric geometry or physical verdict
is inferred. Maximum absolute score changes across all layers are0.526hidden
and1.131lens; same rank metrics do not mean images were omitted.

## Scope of “Jacobian”

This freshly implemented method computes the **complete Jacobian of the final
norm plus all202,048unembedding coordinates**, at each layer's fit-only mean
residual. Exact forward-mode norm JVPs are followed by the full head projection.
FP32 readout arithmetic follows BF16 model extraction. No diagonal/token-subset
approximation, old seeds, matrices or layer depths are imported.

It is a local logit-lens readout, **not the end-to-end Jacobian of intervening
transformer blocks**. It cannot establish that a generated answer causally
used a passage. The external Canis concept is a declared reference, with its
document hash in the report; no prior implementation or dataset is vendored.
See the [frozen protocol](../paired-comparison-protocol.md).

## Uncertainty and limits

Only **two test topic clusters** underlie the six test pairs. The two-sided
sign test on topic-mean margins is**p=0.5**for both methods. The naive per-pair
p=0.03125is retained only as an unadjusted diagnostic: paraphrases in a topic
are correlated. The exploratory two-topic bootstrap interval is[0.778,1.000]
for both arms; it does not justify reliable population coverage or a precise
operating threshold. No threshold was fitted and every `enabled` field stays
false. Images are included, but this task does not require identifying a pen
or checking a footprint, so these results do not establish visual grounding.

The old certainty/answerability AUROC0.5747and rejected90%precision threshold
are not replaced, lowered or repackaged as success. No confidence meter,
product-green path, geometry acceptance or viewpoint-invariance claim is made.

## Execution and grant ledger

Miguel confirmed the **$100grant**, miguel-40686, expires2027-10-31. The old
$20authorization is superseded; prior reservations are retained.

- Text run: A100-80GB,**75.27s**inside function. All52layers complete. The
  client could not deserialize TorchVersion without local Torch; the canonical
  JSON and saved score arrays were recovered from Modal volume. **No GPU rerun.**
- Camera run: A100-80GB,**77.06s**inside function. Peak allocated GPU memory
  about65.0GBin each run. Source checkpoint weight bytes59,553,435,272verified
  before allocation; pinned revision unchanged.
- **$8new nonrefundable GPU reservations**, plus the previous$4and retained$2
  CPU/build reserve: **$14reserved of$100**. These are conservative ceilings,
  not invoiced spend. Inside-function time excludes queue/startup/build time.
- Three CPU-stage failures (launcher dependency, remote sibling import, native
  torchvision dependency) remain in the ledger; none allocated a GPU. The
  image dependency is now pinned and the runner self-contained.
- One maximum container per function, no retries or warm minimum,45minfunction
  /5minstartup deadlines,2sscale-down. Both GPU apps stopped; final container
  inventory is empty. Every launch and recovery is retained in the ledger.

15research/preflight tests were covered across the base and Torch-capable CPU
environments before the runs; after adding the clustered-inference regression,
16distinct research tests are covered.19backend regressions pass. The actual
native RMSNorm JVP, image grids and candidate-token cursor were CPU-preflighted.
Both reports were independently recomputed on CPU from saved52-layer scores;
selected layers, AUROCs and every test margin match the original GPU reports.
The CPU audit adds topic-cluster diagnostics without altering measured scores.

[Machine-readable reports, provenance, source hashes and ledger](paired-comparison-2026-10-28.json).
Private inputs, raw images and vectors stay outside Git; review page:
`~/Movies/Ambient-Field-Lens/2026-10-28/paired-comparison/review.html`.

Next: independent review of the candidate/support labels, then a larger
held-out set whose answer genuinely depends on the camera evidence, plus
independent generated-answer support judgments. Existing world-check target
association, measured geometry, controller/procedure adapters and the reviewed
evidence contract still precede any live green integration. No more GPU
windows are left running or automatically queued.
