# Ambient Field Lens

Safety-gated wearable assistant for the Meta Global AI Developer Hackathon
(Cerebral Valley), Startup track. Built Oct 26 – Nov 4, 2026.

**One-liner:** a wearable machine-setup assistant intended to show an operator
step only when observable world checks and a validated grounding check both
pass; otherwise it names the fault and correction. The current backend is
amber-only; this describes the product target.

## How it works (Phase 1 skeleton)

1. iPhone captures a frame + voice query.
2. Frame + query POST to backend `POST /assist`.
3. Backend returns a gate verdict: `verified` (green badge + first step) or
   `verify` (amber badge, no instruction).
4. HUD card renders the verdict. HUD is a 600x600 card built with the
   Wearables DAT SDK (`MWDATDisplay`, MockDeviceKit `.metaRayBanDisplay`,
   phone camera as mock feed) — designed for Ray-Ban Display; no Display
   hardware is available to the team, which the demo video states.

The stub backend default-denies: every response is `verify`. Recalibration alone
cannot enable green. Real scene validation and a separately reviewed evidence
contract/integration are required; the failed confidence proxy remains failed.

Current evidence: [architecture](ARCHITECTURE.md),
[drawing-readiness contract](docs/drawing-readiness-contract.md), and
[CPU checkpoint / remaining overnight work](docs/drawing-readiness-progress.md).
The [27 October CPU scene report](docs/verification/scene-batch-2026-10-27.md)
inventories 45 image assets across coarse viewpoints and distinct stream profiles.
Viewpoint invariance and metric containment remain unvalidated; human-reference
logic replay is explicitly separate from actual image-model check outputs.
The [actual Meta observation round](docs/verification/real-model-pipeline-2026-10-27.md)
now connects Spark observations and SAM masks through one offline runner:
six completed Spark scene responses, explicit missing-pen/covered-holder
outcomes, and107 passing tests. Target association among SAM candidates remains
unresolved; no Modal GPU or live green integration was started.
The [measured v2 / adapter report](docs/verification/adapter-and-measured-v2-2026-10-27.md)
records failed held-out geometry (maximum 2.955 px versus 2 px), archival S03
adapter replay and the review-only next SAM batch. No live gate integration.

## Layout

| Path | What it is |
| --- | --- |
| `ios/` | Fresh SwiftUI app (camera + HUD + gate UX), built with xcodegen |
| `backend/app.py` | `/assist` stub + `/healthz` (FastAPI) |
| `backend/requirements.txt` | Backend deps |
| `backend/readiness/` | Offline pure checks and planar geometry; not wired into `/assist` |
| `tools/` | Explicit operator capture, one-request SAM diagnostic and offline replay utilities |

## Run

Backend:

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --port 8000
```

Python 3.12 was verified. See [backend setup/tests](backend/README.md) and
[architecture and failure boundaries](ARCHITECTURE.md). Phase 1 request/output
validation, limits, timeouts and a circuit breaker retain default-deny responses;
no model or GPU is started by the backend or its regression suite.

iOS (Xcode 26.4+, iOS 17.2+):

```bash
cd ios
xcodegen generate
open AmbientFieldLens.xcodeproj
```

In the app, set the backend base URL (default `http://localhost:8000`), pair
via MockDeviceKit or real glasses in Developer Mode, start the session, start
preview, then Ask.

## New work vs existing work (disclosure)

Per the hackathon rules, the demo highlights only work built during the event
in this repo (**new**). The following existed before kickoff, are **not**
demoed as new, and are referenced — never vendored — so the boundary stays
visible in the dependency graph:

- Canis disposition seed phrases + CANIS-EVAL-001 eval matrices (540 core /
  350 matched negatives / 420 OOD) — `agentic-fleet-hub/disposition-lens/`,
  used only as a declared reference for the Phase 3 probe design.
- Sovereign Mind ingestion/chunkers and the pre-event Robot Ross chunk corpus —
  external references only, not copied. Unmerged PR #2 freshly ingests 38 chunks
  from 10 user-owned documents with new in-event code.
- Flotilla validators / circuit-breaker patterns — referenced for the
  Phase 3 low-grounding breaker.
- `ambient-field-lens-test` (Oct 23–25) — throwaway pre-kickoff verification
  (SDK wiring, MockDeviceKit, Modal staging scripts). Nothing was copied from
  it; anything needed is retyped here against the DAT docs.

## License

Apache-2.0. See `LICENSE`.
