# Clean checkout verification — 2026-10-26

Verified public `main` commit `c73c514f3f8296abc515f41fa3d8c3eefbb0a561`
from an isolated clone, before implementing backend hardening.

## Baseline

- Xcode 27.1 (27A9275): `xcodegen generate` succeeded.
- `xcodebuild -project AmbientFieldLens.xcodeproj -scheme AmbientFieldLens
  -sdk iphonesimulator -configuration Debug -destination 'generic/platform=iOS Simulator'
  -derivedDataPath /tmp/afl-codi-clean-derived CODE_SIGNING_ALLOWED=NO build`
  succeeded. This checks compilation, not physical-device glasses integration.
- Python 3.12.13, newly created backend virtual environment: requirements
  installed; live Uvicorn health and default-deny `/assist` requests succeeded.

## Hardened backend

A second fresh virtual environment installed `backend/requirements.lock`.
`python -m unittest discover -s tests -v`, run from `backend`, passed all
19 tests. Coverage includes strict JSON/JPEG validation, body and pixel limits,
slow uploads, provider timeouts, overload, cancellation, circuit recovery,
stale completions, forged green responses and unsafe provider detail text.

Live Uvicorn checks from that environment passed with a synthetic JPEG:
health returned 200, a valid request returned 200 with verify/null/zero, and
client-injected verdict fields returned 422 with the same default-deny envelope.
Machine-readable results are in `clean-checkout-2026-10-26.json`.

iOS source is unchanged by backend hardening; the baseline build covers the
submitted client source. No generated Xcode project or local build artefact is
part of this change. No GPU or external model API was invoked; stub HTTP timings
do not measure the future multimodal pipeline.

## Integration handoff

- Muse: clear previous HUD verdicts on transport failure before introducing any
  green response path; the baseline client currently only updates `lastError`.
- Modal/recalibration/Ross ingestion remain pending visible credit confirmation.
- Validation and cooldown patterns reference the declared Flotilla design only.
  No code or data was transferred from the previous test project, Canis matrices
  or Sovereign Mind chunkers.
