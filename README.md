# Ambient Field Lens

Safety-gated field assistant for the Meta Global AI Developer Hackathon,
Startup track. Built Oct 26 – Nov 4, 2026.

**This is not a RAG chatbot.** Most assistants answer even when your manual
does not cover the question, and nothing in the answer tells you which
happened. Ambient Field Lens *measures* whether your documentation covers the
question, refuses when it does not, and turns that refusal into a documented
answer a human wrote and approved.

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
  Wearables Device Access Toolkit interface.
- The `/assist` contract and its default-deny service on Modal.
- SAM 3.1 scene gating — paper candidates and footprint geometry in
  millimetres, not pixels.
- The Glimmer 30B prefill activation readout, its four probe protocols, and
  the negative results that retired them.
- The coverage gate: corpus ingestion, retrieval-distance measurement, and
  the calibration that fixed the threshold at 0.760.
- Immutable corpus versioning with a code-reviewed pin registry, and the
  guarded documentation-repair path (`providers/corpus_repair.py`).
- The documentation repair loop end to end: refusal → gap report → drafted
  candidate → human approval → re-index → new citation.

## What it does today

- Frame a rig, tap **Ask**: the phone captures one frame; retrieval runs over
  the Robot Ross manuals, SAM segments paper candidates, and the Glimmer
  prefill readout is taken and reported. The card carries its evidence —
  mask count, manual chunk ids, retrieval distance — and refuses in amber.
- **Coverage gate.** The nearest manual passage is measured by retrieval
  distance against a threshold calibrated at **0.760** over 13 labelled
  questions (`docs/verification/coverage-calibration-2026-10-30.json`).
  Covered questions top out at 0.741. A question the corpus does not answer
  returns `NOT COVERED` with the distance on the card.
- **World checks.** A separate gate: is there a paper candidate in the frame,
  and does the drawing footprint fall inside its boundary. Failing it returns
  `WORLD CHECK FAILED`. It is independent of coverage — either can refuse.
- **The repair loop.** A refusal offers to report the gap, carrying the
  question, the answer and the exact retrieved chunk ids. A candidate answer
  is drafted against the operator's own documents; a human edits and approves
  it in their wiki; the corpus is re-versioned and re-indexed. Asking again
  cites the new passage. Nothing is retrained.
- Header chips (WORLD / COV) show only earned failures in colour; anything
  unestablished renders grey. No chip can pass anything.

## What it does not do

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

## Disclosure

Clean-room repo created Oct 26, 2026. Nothing copied from earlier private
prototypes; prior art is referenced as declared dependencies or in
[docs/existing-work.md](docs/existing-work.md). Calibration labels were
reviewed by a human; scoring ran only on frozen labels. Every negative
result is in-repo under `docs/verification/`.
