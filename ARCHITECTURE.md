# Ambient Field Lens — Phase 1 boundaries

The clean-room iOS client captures a frame, encodes a JPEG and sends the existing
`query` / `image_jpeg_base64` JSON contract to `POST /assist`. It renders the
four-field verdict response on the HUD. This branch does not change DAT wiring.

## Backend request path

1. `RequestBoundary` permits uncompressed JSON only, enforces a 3 MiB actual-body
   budget (including chunked requests) and a three-second total receive deadline.
2. `AssistRequest` rejects unknown fields, blank/control-character queries,
   queries over 2,000 characters, malformed base64 and invalid/truncated images.
   JPEGs are limited to 2 MiB decoded bytes and 4,194,304 pixels. No image is
   persisted or included in error responses.
3. A missing frame returns amber immediately. Otherwise `AssistService` admits
   at most four calls, with a bounded admission wait and a 2.5-second processing
   deadline. Providers must be asynchronous/nonblocking. Local timeout does not
   claim to cancel external GPU billing; no such provider is configured here.
4. A per-worker circuit opens after three consecutive failures or explicit
   `LowGrounding` results. Thirty seconds later, one half-open probe is allowed.
   Generation-tagged permits prevent late earlier calls from overriding the
   open circuit or the probe. Normal uncalibrated refusals are not failures.
5. The Phase 1 response contract permits only `verify`, null step and zero
   score. It revalidates even preconstructed model objects. Provider detail is
   replaced with application-owned text; neither a green flag nor an instruction
   in the amber detail can bypass the stub. Failures also return an amber
   envelope, with appropriate 4xx/5xx HTTP status and `Cache-Control: no-store`.

## Scope and later work

The breaker is process-local. With several workers, each has its own four-call
budget and breaker; distributed budgets are not implemented. There is no model,
SAM endpoint, Modal deployment, calibration artefact, Chroma client or secret
dependency in this implementation. The first-card <3s goal has not been measured
against the planned multimodal/GPU pipeline. Request/processing limits are
bounded failure handling, not an end-to-end latency guarantee.

Phase 3 needs an explicitly reviewed server-owned calibration/evidence contract
before this schema can represent green instructions. A client-provided score,
unvalidated provider text or merely connecting a model cannot enable green.

Conceptual references are the disclosed Flotilla fail-closed validation and
cooldown patterns. This implementation was written in this repository during
the event; no Flotilla code was vendored. No code/data was copied from
`ambient-field-lens-test`, Canis matrices or Sovereign Mind chunkers.

The baseline iOS error handler should be reviewed in the later green-path work:
transport failures set `lastError` without clearing the previous HUD verdict.
Phase 1 cannot produce a green verdict, and this backend branch leaves the
client-owned area for Muse's integration work.
