# Ambient Field Lens

Safety-gated field assistant for the Meta Global AI Developer Hackathon,
Startup track. Built Oct 26 – Nov 4, 2026.

**[afl.flotilla.cc](https://afl.flotilla.cc)** — the submission page, with the
film, the measured numbers and the limits. &nbsp;·&nbsp;
**[The film (2:59)](https://www.youtube.com/watch?v=--41dwUlMIs)** &nbsp;·&nbsp;
[Privacy](https://afl.flotilla.cc/privacy/) &nbsp;·&nbsp;
[Terms](https://afl.flotilla.cc/terms/)

## For judges

**Track:** Startups. **Built:** Oct 26 – Nov 4, 2026, in this repo, from empty.

**The fit.** A technician in front of a machine asks a setup question and gets
an answer whose grounding they cannot check. We put a wearable-class capture
path in front of the operator's own manuals, and made the assistant refuse
rather than guess when those manuals do not cover the question — then turn the
refusal into a passage a human writes and approves.

**Meta models and APIs used.** Both routes the rules name are in the live path —
the Meta Model API, and Meta open-weight models.

| Model | How it is used | Route | Call site |
|---|---|---|---|
| **Glimmer 30B** | Residual-stream readout at prefill; weights never modified | **Open weights**, self-hosted on Modal GPU | [`backend/providers/modal_runtime.py`](backend/providers/modal_runtime.py) |
| **SAM 3.1** | Segments the frame into paper-mask candidates | **Meta Model API** | [`backend/providers/sam.py#L88`](backend/providers/sam.py#L88) |
| **Muse Spark 1.3** | Scene wording and pen-presence observations | **Meta Model API** | [`backend/providers/pen_presence.py#L71`](backend/providers/pen_presence.py#L71) |
| **Muse Spark Open** (`meta-models/muse-spark-open-1026`) | Offline wording generation | **Open weights** | [`backend/generation/wording.py#L16`](backend/generation/wording.py#L16) |
| **Meta Wearables DAT** | Capture, and the glasses display path | SDK | [`ios/AmbientFieldLens/ViewModels/WearablesViewModel.swift`](ios/AmbientFieldLens/ViewModels/WearablesViewModel.swift) |

**One frame through both Meta models, with receipts.**
[`docs/verification/live-provider-integration-2026-10-28.json`](docs/verification/live-provider-integration-2026-10-28.json)
carries a single `frame_sha256` through SAM 3.1 (one mask returned, 1.68 s) and
Glimmer 30B (prefill readout, layer 27, 861 prefix tokens, one forward pass,
`model_revision` recorded). That mask's `origin` is `server_reviewed_manual_box`
— a reviewed box prompt, not autonomous detection, and it says so in the file.

Read this next to the film, because the two show different things: the filmed
refusal at d=0.820 returns from the **coverage gate**, which runs on retrieval
distance *before* any frame is inspected ([`backend/live_backend.py#L341`](backend/live_backend.py#L341);
SAM at L357, Glimmer at L372). That shot proves the refusal behaviour, not Meta
model use. The answered re-ask, and the receipt above, are where SAM and Glimmer
actually run.

**Verify in two minutes, with no credentials.**

```bash
git clone https://github.com/UrsushoribilisMusic/ambient-field-lens
cd ambient-field-lens/backend
python3.12 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests recal -q
```

Last run from a clean environment: **213 passed, 8 skipped, 131 subtests
passed**, no network, no Modal account, no Meta API key. Live inference is a
separate path and does need credentials — see [Run the demo](#run-the-demo).

**What pre-existed** is in [Built during the hackathon](#built-during-the-hackathon)
and [docs/existing-work.md](docs/existing-work.md): the robot arm, its manuals
and the wiki backend are the test bench; the software here is new.

**This is not a RAG chatbot.** Most assistants answer even when your manual
does not cover the question, and nothing in the answer tells you which
happened. Ambient Field Lens *measures* whether your documentation covers the
question, refuses when it does not, and turns that refusal into a documented
answer a human wrote and approved.

![The Field Lens app refusing a question: NOT COVERED, d=0.820 > 0.760, with a
button to report the missing instruction](docs/img/refusal-card.jpg)

*The real app, on the real rig. The question is outside the manuals, the
distance that says so is on the card, and the refusal offers to file the gap.*

**One-liner:** an operator looks at a machine through the phone (standing in
for glasses) and asks setup questions. The system answers with amber cards
carrying their evidence, refuses when coverage or the scene cannot be
established, and never emits a green step — the backend is type-level
incapable of one until a reviewed evidence contract says what green requires.

## Built during the hackathon

Required by Rule 4. Nothing below was copied from earlier work; see
[docs/existing-work.md](docs/existing-work.md) for the code-provenance boundary.

**Pre-existing platform, used as a test bench:**

- Robot Ross — the Huenit arm, its controller, and the physical rig.
- The ATF wiki corpus (Robot Ross manuals) as source documents.
- Sovereign Mind — the wiki/console product the repair loop writes back into.

**Built during the hackathon, in this repo:**

- Field Lens iOS app — viewfinder, verdict card, gate chips, on the Meta
  Wearables Device Access Toolkit interface. The same binary is the glasses
  host: it streams from the glasses camera and sends an amber-only card to
  the glasses display over the same device session. There is no separate
  glasses binary, and no display hardware was available — the display path
  is validated against a display-capable mock
  ([docs/glasses-display-handoff.md](docs/glasses-display-handoff.md)).
- The `/assist` contract and its default-deny service on Modal.
- SAM 3.1 scene gating — paper-mask candidates in the live path, and a
  measured footprint geometry the live card reports as unverified rather than
  accepting as clearance.
- The Glimmer 30B prefill activation readout, its four probe protocols, and
  the negative results that retired them.
- The coverage gate: corpus ingestion, retrieval-distance measurement, and
  the calibration that fixed the threshold at 0.760.
- Immutable corpus versioning with a code-reviewed pin registry, and the
  guarded documentation-repair path (`providers/corpus_repair.py`).
- The documentation repair loop end to end: refusal → gap report → drafted
  candidate → human approval → re-index → new citation.

## What it does today

![One request: frame, SAM 3.1, identity, retrieval, then the coverage check,
with world checks as a separate gate](docs/img/request-path.png)

- Frame a rig, tap **Ask**: the phone captures one frame; retrieval runs over
  the Robot Ross manuals, SAM segments paper candidates, and the Glimmer
  prefill readout is taken and reported. The card carries its evidence —
  mask count, manual chunk ids, retrieval distance — and refuses in amber.
- **Coverage gate.** The nearest manual passage is measured by retrieval
  distance against a threshold calibrated at **0.760** over 13 labelled
  questions (`docs/verification/coverage-calibration-2026-10-30.json`).
  Covered questions top out at 0.741. A question the corpus does not answer
  returns `NOT COVERED` with the distance on the card.
- **World checks.** A separate gate: is there a paper candidate in this frame
  at all. Failing it returns `WORLD CHECK FAILED`. It is independent of
  coverage — either can refuse. Footprint clearance is measured but **not
  accepted**: the card reports `footprint unverified`, and no geometry in the
  live path can pass anything.
- **The repair loop.** A refusal offers to report the gap, carrying the
  question, the answer and the exact retrieved chunk ids. A candidate answer
  is drafted against the operator's own documents; a human edits and approves
  it in their wiki; the corpus is re-versioned and re-indexed. Asking again
  cites the new passage. Nothing is retrained.
- Header chips (WORLD / COV) show only earned failures in colour; anything
  unestablished renders grey. No chip can pass anything.

### The gate is calibrated, not asserted

![Coverage gate calibration: eight covered questions between 0.31 and 0.74,
three near-misses, two absurd questions, against a gate at 0.76](docs/verification/coverage-calibration-2026-10-30.png)

*Thirteen labelled questions, frozen before scoring. The gate sits at 0.760
because covered questions top out at 0.741 and the nearest non-covered
observation is 0.787. Receipt:
[`docs/verification/coverage-calibration-2026-10-30.json`](docs/verification/coverage-calibration-2026-10-30.json).*

### The refusal is the input

![The improvement loop: a coverage refusal or operator feedback leads to a
drafted passage, human review in the wiki, re-indexing, and asking
again](docs/img/repair-loop.png)

![The review console: the refusal with its distance, the operator's comment,
the retrieved chunk ids, and a drafted candidate answer awaiting
approval](web/img/backend-approved.jpg)

*The gap report as the reviewer sees it — the question, the refusal with
`d=0.820`, the chunks that were actually retrieved, and a candidate answer
nobody has approved yet. Approving it publishes the passage and re-versions
the corpus from 38 records to 39. Asking the same question then measures 0.400
and cites the new passage.*

## What it does not do

![Negative result: held-out text pilot AUROC 1.000; live visual task
supported −0.018, unsupported −0.015 — no separation](docs/img/negative-result.png)

- **No weight readout in the verdict.** Four independent probes (contrastive,
  Jacobian lens, trajectory, live prefill) found no signal separating grounded
  from improvised answers on this task. On the live visual task a supported
  question scored −0.018 and an unsupported one −0.015 — no separation. The
  score is pinned to zero on the wire and the verdict does not read it.
  Groundedness here is a system property — retrieved passage, hash-bound
  evidence, fail-closed on anything missing — not a model readout.
  **Open weights remain the precondition for having tried:** a hosted API
  returns tokens and never internal state.
- **No green steps**, no red blocks, no instructions to touch the machine.
  The arm moves only on a human command, over a local serial link the cloud
  never reaches.
- **No capture-time proof.** A receipt binds which frame, question, passage
  and masks went into an answer — never when the photo was taken. A
  photograph from yesterday passes every check on the card.
- **Distance is not relevance.** Two of the three labelled near-misses fall
  *below* the gate (0.668 and 0.725), and an off-domain question ("make
  coffee") measures 0.787 — closer than the legitimate near-miss at 0.820.
  The gate measures embedding proximity, not whether a passage answers.

## Where each piece runs

![What runs where: capture and card on the person, the /assist contract,
retrieval, SAM and Glimmer on Modal, and the controller, arm and camera in the
workshop](docs/img/runs-where.png)

| Piece | Runs on |
|---|---|
| Capture, viewfinder, verdict card | iPhone (Meta Wearables DAT interface) |
| Retrieval over your manuals | Modal, **CPU** — Chroma, local index |
| SAM 3.1 segmentation | Meta API |
| Glimmer 30B prefill readout | Modal, **GPU** |
| Wiki authoring and approval | Sovereign Mind console |
| Arm control | The operator's own hardware, local serial |

The index is portable: it is a Chroma database over the operator's own
documents, and the retrieval half of the pipeline has no cloud dependency
other than where we chose to host it.

## Run the demo

Requires an open window (finite: 600 s, 4 single-use token calls):

```bash
cd backend
.venv/bin/python -c "
import modal
from providers import client
from live_backend import arm_tokens
r = client.open_window(seconds=600, max_calls=4)
d = modal.Dict.from_name('afl-live', create_if_missing=True)
rec = {'id': r['id'], 'expires_at': r['expires_at'], 'max_calls': 4, 'calls_used': 0}
d.put('active', rec); arm_tokens(rec)"
```

Then Ask from the phone (base URL in Setup; backend default-deny otherwise).
Each framed call burns one token: ~15–90 s of Modal GPU/CPU plus one Meta SAM
decode. A window reserves a fixed ceiling in the local budget ledger whether
or not the calls are used. Close with `client.close_window(id)`.

## Layout

- [ARCHITECTURE.md](ARCHITECTURE.md) — system as built, gates, contracts.
- [docs/submission.md](docs/submission.md) — hackathon narrative and limits.
- [docs/documentation-repair-handoff.md](docs/documentation-repair-handoff.md) — the repair procedure and its guard.
- [docs/live-assist-wiring.md](docs/live-assist-wiring.md) — live path ops log.
- [docs/observable-checks-handoff.md](docs/observable-checks-handoff.md) — providers.
- [docs/existing-work.md](docs/existing-work.md) — provenance boundary.
- [docs/proposals/red-controller-contract.md](docs/proposals/red-controller-contract.md) — red proposal (not implemented).
- [web/](web/) — the source of [afl.flotilla.cc](https://afl.flotilla.cc).

## Disclosure

Clean-room repo created Oct 26, 2026. Nothing copied from earlier private
prototypes; prior art is referenced as declared dependencies or in
[docs/existing-work.md](docs/existing-work.md). Calibration labels were
reviewed by a human; scoring ran only on frozen labels. Every negative
result is in-repo under `docs/verification/`.
