# Glimmer Phase 1 research — 2026-10-26

The checkpoint is verified, Ross ingestion works, and recalibration steps 1–4
were executed. **The measured certainty axis did not yield a Ross operating
threshold meeting the 90% precision target. `/assist` remains incapable of
returning a green step.**

## Checkpoint and execution

- Source: `meta-models/Muse-Glimmer-30B`, revision
  `cec94fcfd6512f2cfe708138c32533b346ea4f69`.
- Two weight shards: **59,553,435,272 bytes**, both SHA-256 hashes matched.
  All source files total **59,581,830,875 bytes**.
- Download and verification ran on CPU in `glimmer-weights`. The Mac did not
  download the model. [Download evidence](verification/glimmer-download.json).
- CPU model construction identified the native multimodal loader and
  `model.language_model.layers`. All 1,460 experiment inputs passed a 1,024-token
  limit; the largest was 788 tokens. No silent prompt truncation occurred.
- One A100-80GB window ran for **488.37 seconds** inside the research function.
  The app stopped and container inventory was empty after completion.
  [CPU preflight](verification/glimmer-cpu-model-preflight.json),
  [runtime versions](verification/glimmer-runtime.json).
- The local budget ledger reserved $4 for that GPU attempt and $2 for CPU/build
  work under the $20 ceiling. Reservations are conservative execution bounds;
  they are not invoice measurements or verification of a workspace billing cap.
  [Ledger snapshot](verification/budget-reservations.json).

## Steps 1–2: contrastive directions and layer selection

New contrastive means were fitted on even core IDs. Odd core IDs selected
layers across all 52 text decoder layers. The 350 matched-negative and 420 OOD
cases did not fit directions or choose layers. Selected validation AUROCs are
selection metrics; the table reports the separate OOD evaluation.

This is a **contrastive baseline**, not a reproduction of the Canis Jacobian
estimator. No prior vectors or layer depths were transferred.

| Axis | Layer, zero-based | OOD AUROC | Positive, selective lexical steering proxy |
| --- | ---: | ---: | --- |
| Confident | 8 | 0.8774 | No |
| Uncertain | 34 | 0.9167 | Yes |
| Curious | 28 | 0.8153 | Yes |
| Concern | 26 | 0.7540 | Yes |
| Reluctant | 11 | 0.8715 | No |
| Warm | 30 | 0.9997 | No |
| Mischief | 23 | 0.9441 | No |

## Step 3: domain calibration

The experiment measured 150 Ross prefill scores using retrieved, sanitized
manual evidence. The confident-minus-uncertain score was calibrated against
the existing answerability labels. Each question used up to two retrieved
passages, capped at 160 words each before the tokenizer budget check.

The initial category-hash partition lacked one class in the test fold and was
rejected. A CPU-only correction assigned whole categories with stratified group
folds, using labels/groups rather than model performance. The same measured
scores and unchanged source labels were reused; their hashes are recorded.
The original rejection remains in `initial_calibration` in the full report.

The corrected partitions contain 47 fit, 48 threshold-selection and 55 test
items. Held-out test AUROC is **0.5747**. No validation threshold met the 90%
empirical precision target. The research threshold therefore rejects all items,
and its `enabled` field remains false.

This measures corpus answerability, not generated-answer correctness. It does
not validate operator instructions. The external labels also need review
against the current manual snapshot before any Phase 3 deployment decision.
[CPU calibration result](verification/glimmer-domain-calibration.json).

## Step 4: steering experiment

Seven axes each received five interventions, alpha −2 through +2, with generated
examples and downstream token readouts recorded. Uncertain, curious and concern
passed the positive monotonic/selective **lexical proxy** check; other axes did
not. A first-token readout of an axis name is a limited proxy. The reports make
no semantic causal claim and require review of the generated examples.

## Ross corpus

**38 fresh chunks from 10 user-owned manuals/wiki documents** were embedded on
CPU and persisted in `afl-ross-chroma`, collection
`ross-manuals-2ca5f2f152267049`. Ingestion was implemented here; no Sovereign Mind
chunker or prebuilt chunk dataset was used. Credential-bearing URL components
and credential assignments are removed before indexing.

Retrieval smoke checks returned the calibration material for a calibration
query and drawing documentation for a writing query. Evidence retrieval also
completed for all 150 domain questions. [Ingestion evidence](verification/ross-ingestion.json).

## Disclosure and reproducibility

The 540 core, 350 matched-negative and 420 OOD Canis cases and the pre-event Ross
question set were read as external references. The raw files, prior scripts,
seed vectors and source prompts are absent from this repo and the Modal images.
Their filenames, counts, provenance and hashes are in the result report. Inputs
were supplied privately at runtime; only derived results are retained.

The model is from Meta; the machine, manuals and evaluation references existed
before the event. The new work is the staging/verification, ingestion, research
implementation and Glimmer measurements. Prior Canis/Flotilla concepts are
declared references. The backend remains the Phase 1 default-deny service.

[Full results](verification/glimmer-research.json),
[execution instructions](../backend/recal/README.md),
[documented SAM invocation](sam-invocation.md).

Resource limits use the checked [Modal pricing](https://modal.com/pricing);
independent workspace workloads require a [workspace budget](https://modal.com/docs/guide/budgets).
