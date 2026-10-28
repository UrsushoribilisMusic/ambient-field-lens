# Glimmer staging and offline research

These are fresh in-event implementations. They do not import prior extraction,
J-lens, calibration or chunking code. The current estimator is a contrastive-mean
baseline, not a reproduction of the Canis Jacobian estimator.

Checkpoint files live in Modal `glimmer-weights`, never on the Mac. The pinned
HF revision, source byte counts and LFS hashes are in `source-manifest.json`.
`weights_cpu.py` has no GPU function and writes its marker only after all source
file sizes, weight/tokenizer hashes and the BF16 configuration check succeed.

Local setup (Python 3.12; no local Torch or model weights needed):

```sh
python3.12 -m venv .venv-recal
.venv-recal/bin/pip install -r backend/recal/requirements-local.txt
.venv-recal/bin/python -m unittest discover -s backend/recal -p 'test_*.py' -v
```

Commands below require an authenticated Modal CLI and the declared external
input paths. Raw reference files stay outside this repository and the images.

```sh
modal run --detach backend/recal/weights_cpu.py
modal run --detach backend/recal/corpus_cpu.py::main --source-root /path/to/robot-ross --wiki-root /path/to/ATF/artifacts/wiki
modal run backend/recal/corpus_cpu.py::evidence --questions-path /external/ross_draw_setup_questions.jsonl
modal run backend/recal/recal_window.py::inspect_model
modal run --detach backend/recal/recal_window.py::main --core /external/canis_eval001_matrix.jsonl --matched /external/canis_eval001_matched_negatives.jsonl --ood /external/canis_eval001_ood_matrix.jsonl --questions /external/ross_draw_setup_questions.jsonl --evidence-file /tmp/afl-ross-question-evidence.json --gpu-window
```

The research entrypoint verifies the completed download and native model
construction/token lengths on CPU before reserving a GPU window. A native
`AutoModelForImageTextToText` loader was required by the tested checkpoint.
All 52 text decoder layers are observed; depth is selected from validation data.
No 4B vectors or layer positions transfer into this implementation.

Core even IDs fit directions; core odd IDs select layers. Matched and OOD
inputs do not fit directions or select layers. Domain calibration uses whole
topic groups in three label-balanced partitions, fitted with Platt logistic
regression. Its target is corpus answerability. Empirical precision, sample
counts and precision uncertainty must be read together.

Steering measures a lexical readout proxy and records generated examples.
It does not establish a semantic or safety claim. All research gate artefacts
remain disabled, including after an apparently successful calibration.

GPU windows have no retries or warm minimum, one maximum container, a 45-minute
function deadline, five-minute startup deadline and two-second scale-down.
The shared local ledger at `~/.local/state/ambient-field-lens/budget.json`
reserves $2 for CPU/build work and a nonrefundable $4 per GPU attempt, refusing a
fifth window under the $20 ceiling. At the checked rates, the GPU/4-CPU/64-GiB
resource envelope fits inside that reservation. This guards these commands;
independent workspace jobs require their own controls or a workspace budget.

To repair/re-fit step 3 from already measured scores without any GPU:

```sh
python backend/recal/recalibrate_cpu.py --scores /private/question-scores.jsonl --questions /external/ross_draw_setup_questions.jsonl --report docs/verification/glimmer-research.json
```

Weights and derived vectors are not Git assets. Persistent research outputs
are in `afl-recal-artifacts`; the sanitized manual index is in `afl-ross-chroma`.
Only small provenance and result reports are committed. See
[`../../docs/recalibration-results.md`](../../docs/recalibration-results.md).
