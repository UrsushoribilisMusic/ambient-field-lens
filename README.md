# Ambient Field Lens

Safety-gated wearable assistant for the Meta Global AI Developer Hackathon
(Cerebral Valley), Startup track. Built Oct 26 – Nov 4, 2026.

**One-liner:** the app identifies machine parts through smart glasses and only
shows an operator step when its internal grounding check passes — otherwise it
tells the user to verify in the manual.

## How it works (Phase 1 skeleton)

1. iPhone captures a frame + voice query.
2. Frame + query POST to backend `POST /assist`.
3. Backend returns a gate verdict: `verified` (green badge + first step) or
   `verify` (amber badge, no instruction).
4. HUD card renders the verdict. HUD is a 600x600 card built with the
   Wearables DAT SDK (`MWDATDisplay`, MockDeviceKit `.metaRayBanDisplay`,
   phone camera as mock feed) — designed for Ray-Ban Display; no Display
   hardware is available to the team, which the demo video states.

The stub backend default-denies: until the Glimmer recalibration lands
(Phase 3), every response is `verify`. That is the safe default, not a bug.

## Layout

| Path | What it is |
| --- | --- |
| `ios/` | Fresh SwiftUI app (camera + HUD + gate UX), built with xcodegen |
| `backend/app.py` | `/assist` stub + `/healthz` (FastAPI) |
| `backend/requirements.txt` | Backend deps |

## Run

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --port 8000
```

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
- Sovereign Mind ingestion/chunkers + Robot Ross chunk corpus (54 chunks) —
  retrieval corpus source, disclosed on use.
- Flotilla validators / circuit-breaker patterns — referenced for the
  Phase 3 low-grounding breaker.
- `ambient-field-lens-test` (Oct 23–25) — throwaway pre-kickoff verification
  (SDK wiring, MockDeviceKit, Modal staging scripts). Nothing was copied from
  it; anything needed is retyped here against the DAT docs.

## License

Apache-2.0. See `LICENSE`.
