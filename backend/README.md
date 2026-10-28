# Backend development

Python **3.12** was used for verification. Python 3.10+ is needed for type-union
syntax; the macOS `/usr/bin/python3` on the verification machine is 3.9 and is
not the interpreter used by this backend.

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -r requirements-readiness.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

`requirements.lock` records the complete tested development environment. Use
`pip install -r requirements.lock` for that exact dependency resolution.

`GET /healthz` reports readiness of the HTTP stub and its circuit state, not
readiness of calibration or a model. `POST /assist` retains the iOS request and
response field names. A nonblank query and an optional base64 JPEG are accepted;
an empty frame produces an amber result without invoking a provider. All error
responses also contain `verdict: verify`, `step: null`, `score: 0` and a generic
`detail`; invalid requests no longer echo submitted text/image data.

Limits and breaker behaviour are described in the root `ARCHITECTURE.md`.
There is deliberately no configurable green bypass or public calibration flag.
The tests use synthetic in-memory JPEGs, fake async providers and synthetic
geometry/evidence fixtures, never a GPU, external model API, production manual
corpus or secret. Offline readiness tests do not establish marker registration
or per-scene physical validation; see `docs/drawing-readiness-progress.md`.

Offline wording jobs use the [Baseten generation tool](../docs/generation-routing.md),
with explicit Meta overflow and shared API receipts. Run `python3.12 -m
unittest discover -s tests -p test_wording_generation.py -v` for its CPU-only
tests. It is not imported by the HTTP backend or scientific readout code.

Runtime demo providers: install `requirements-providers.txt` and follow
[`docs/live-provider-handoff.md`](../docs/live-provider-handoff.md). A Modal window
must be explicitly reserved/opened before Glimmer accepts requests. SAM and Ross
retrieval are callable independently. Do not change `AssistService` to accept a
provider score as a green verdict; Muse owns the reviewed admission contract.
