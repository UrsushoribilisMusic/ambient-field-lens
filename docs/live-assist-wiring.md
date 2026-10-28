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

## Unresolved (morning work, NO spend overnight)
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
