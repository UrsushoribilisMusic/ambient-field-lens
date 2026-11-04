# Evidence index — current status

Every load-bearing claim, and where it is proven. This is the current-state
document: the dated handoffs under `docs/` are historical working notes and
their test counts and open questions are not status.

Last verified 4 November 2026 against `main`.

## Verify it yourself, without credentials

```bash
git clone https://github.com/UrsushoribilisMusic/ambient-field-lens
cd ambient-field-lens/backend
python3.12 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests recal -q
```

**213 passed, 8 skipped, 131 subtests passed** from a clean virtual environment.
No network, no Modal account, no Meta API key. 29 test files are tracked in the
repository. Live inference is a separate path and does need credentials — see
[Run the demo](../README.md#run-the-demo).

## The claims

| Claim | Where it is proven |
|---|---|
| The coverage gate sits at a retrieval distance of 0.760, calibrated over 13 labelled questions; questions the manuals genuinely cover top out at 0.741 | [coverage-calibration-2026-10-30.json](verification/coverage-calibration-2026-10-30.json) |
| Retrieval runs *before* any frame is inspected, so a refusal returns without calling SAM or Glimmer | `backend/live_backend.py` — retrieve at L329, gate with early return at L341, segment at L357, ground at L372 |
| The repair ran end to end: a human wrote and approved the passage, and the corpus went from 38 records to 39 | [corpus-pins.json](../backend/providers/corpus-pins.json) — the reviewed pin `ross-repair-ad3c9065b45ac2d3a0562011`, with fingerprint, report and snapshot hashes beside the 38-record baseline |
| The same question measured 0.820 before and 0.400 after | before: [repair-before-retrieval-2026-10-29.json](verification/repair-before-retrieval-2026-10-29.json) (`records: 38`, `distance: 0.8199…`); after: the 39-record pin above, and the film |
| Approval does not deploy anything by itself | [documentation-repair-handoff.md](documentation-repair-handoff.md) — wiki export, immutable CPU staging, reviewed pin, guarded activation with rollback |
| One frame went through both Meta models | [live-provider-integration-2026-10-28.json](verification/live-provider-integration-2026-10-28.json) — a single `frame_sha256` through SAM 3.1 (1 mask, 1.681 s) and Glimmer 30B (prefill, layer 27, 861 prefix tokens, 1 forward pass, `model_revision` recorded) |
| That SAM mask was a reviewed box prompt, not autonomous detection | same file: `"origin": "server_reviewed_manual_box"` |
| The activation readout never gates | `backend/live_backend.py#L372`; the score is pinned to 0.0 on the wire and the verdict does not read it |
| No readout established a reliable grounding gate for the live task | live visual: supported −0.018 vs unsupported −0.015, no separation. Held-out text pilot separated at AUROC 1.000 over 24 pairs, with two topic clusters and a length confound we did not resolve. Per-probe: contrastive 0.575; Jacobian lens 0.861 vs plain 0.889; trajectory retired. All of [docs/verification/](verification/) — 53 files |
| Footprint geometry is measured but never accepted | the live card reports `footprint unverified`; no geometry in the live path can pass anything |
| The glasses display path was validated against a mock, with no display hardware | [glasses-display-handoff.md](glasses-display-handoff.md) — "Same iPhone binary is the glasses host. No separate glasses binary." |
| Nothing was copied from earlier private work | [existing-work.md](existing-work.md); repo created 26 October 2026, 156 commits in the window, 0 before it |

## Meta models, and where each is called

| Model | Route | Call site |
|---|---|---|
| Glimmer 30B | Open weights, self-hosted on Modal GPU | [`backend/providers/modal_runtime.py`](../backend/providers/modal_runtime.py) |
| SAM 3.1 | Meta Model API | [`backend/providers/sam.py#L88`](../backend/providers/sam.py#L88) |
| Muse Spark 1.3 | Meta Model API | [`backend/providers/pen_presence.py#L71`](../backend/providers/pen_presence.py#L71) |
| Muse Spark Open | Open weights, served on Baseten | [`backend/generation/wording.py#L16`](../backend/generation/wording.py#L16) |
| Meta Wearables DAT | SDK | [`ios/AmbientFieldLens/ViewModels/WearablesViewModel.swift`](../ios/AmbientFieldLens/ViewModels/WearablesViewModel.swift) |

Drafting a candidate passage is a **hosted** call — Baseten or the Meta Model
API — not an on-premises model. A fully customer-hosted pipeline is a target,
not what this demo does.

## Document status

**Current.** [README](../README.md) · [ARCHITECTURE](../ARCHITECTURE.md) ·
[submission.md](submission.md) · [existing-work.md](existing-work.md) ·
[glasses-display-handoff.md](glasses-display-handoff.md) ·
this index · everything under [verification/](verification/).

**Historical working notes**, carrying a banner to that effect:
[live-assist-wiring.md](live-assist-wiring.md) (includes 502 failures that were
diagnosed and fixed — the root cause was whitespace in a Modal Secret from a
failed vault fetch) · [muse-handoff-2026-10-27.md](muse-handoff-2026-10-27.md) ·
[drawing-readiness-2026-10-27.md](drawing-readiness-2026-10-27.md) ·
[drawing-readiness-progress.md](drawing-readiness-progress.md) ·
[observable-checks-handoff.md](observable-checks-handoff.md) ·
[live-provider-handoff.md](live-provider-handoff.md) ·
[documentation-repair-handoff.md](documentation-repair-handoff.md) ·
[WORKLOG.md](../WORKLOG.md).

**Proposals, not implemented.**
[proposals/red-controller-contract.md](proposals/red-controller-contract.md).
