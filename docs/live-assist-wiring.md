# Live /assist wiring (amber-only) — status 2026-10-29 ~00:40 CET

## What it is
`backend/live_backend.py`: real providers (Ross retrieval, SAM paper
candidates, Glimmer grounding readout) composed into the reviewed
`AssistResponse` contract (`verdict='verify'`, `step=None`, `score=0.0`,
detail <= 300 chars). No threshold exists, so every world check stays
unverified; the amber detail carries a compact evidence summary
(mask count + ids, chunk ids, uncalibrated score).

`backend/modal_assist.py`: `AFL_LIVE_ASSIST=1` at deploy time serves the
live composition; otherwise the Phase 1 stub. Live image adds
`modal==1.6.2`, `meta-sam-parser`, and the `afl-model-api` Modal Secret
(`MODEL_API_KEY`, for in-container SAM decode). `generation/wording.py`
`credential()` gained an env fallback (vault first, env second).

## Proven so far
- Deploy works; `/healthz` stays `default-deny`; empty frame -> stub-style
  amber; framed request with no window -> 503 amber (live path active).
- Window open/claim/close via `afl-live` Dict works from Mac.
- Mac-local chain works: retrieval returns chunks, SAM runs (0 masks on the
  archived cross-sheet frame), grounding not reached without masks.
- Unit tests: 128 pass, 7 expected skips (`tests/test_live_backend.py`: 7).

## Root cause found (morning, no spend)
Framed `/assist` 502s at stage `segment` with `RuntimeError`: the
`afl-model-api` Modal Secret contains whitespace — it was filled from a
failed vault fetch (Infisical browser session expired overnight, so
`agent-fetch.sh` printed its error message into the dotenv file).
`credential()` rightly rejects it (`credential_unavailable`, fail-closed).
Fix chain (needs Miguel, 2 min): `infisical login` (browser) ->
verify `agent-fetch.sh MODEL_API_KEY dev` returns no whitespace ->
`modal secret create afl-model-api --from-dotenv <600-file> --force` ->
verify with the length-only probe (`/tmp/afl-secret-probe.py`: present,
length ~3-digit, **no whitespace**) -> NO redeploy needed (secret resolves
at container start) -> open fresh window -> one framed call.
Hardening for Codi: make the refill procedure + whitespace probe a doc,
and consider a deploy-time secret-shape check.

## iOS companion (built + installed 2026-10-29)
`AssistViewModel`: frames downscaled to <=1600px longest edge before send
(full-res JPEGs hit the 422 contract limit); timeouts 10s -> 180s for the
live path. Builds clean, installed on the 15 Pro Max. Not yet tapped.

## Unresolved (needs the key above, then minutes)
Full-frame `/assist` returns **502** after ~7-21s. Fixed so far:
`create_if_none` -> `create_if_missing`, `Dict[...] = ...` -> `.put()`.
Hypotheses ranked: (1) container crashing mid-SAM (native parser) rather
than a caught exception — failure notes never landed in the Dict;
(2) container->Modal function call auth for retrieve/score;
(3) `evidence_detail` edge on live shapes.
Next: redeploy (progress-note build is committed, NOT deployed), open a
fresh window, single full-frame call, read `afl-live` `stage`/`last_error`.

## Hard limits (unchanged)
- Calls claimed BEFORE providers run (budget-safe); max 4 per window.
- Any provider failure -> amber denial, never a step, never provider text.
- Phone must downscale frames to <= 4MP before send (contract rejects
  full-res phone JPEGs with 422). iOS timeout still 10s -> raise to ~180s
  in the same build as the downscale fix.
- Spend tonight: one $4 window reserved then closed, provider attempts
  empty -> no GPU burn. Modal dashboard is the final word on charges.
