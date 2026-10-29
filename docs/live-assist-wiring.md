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

## Prefix contract (app derives gate chips from these; Codi review)
Amber detail strings carry stable machine-readable prefixes. The phone
parses them into WORLD / COVERAGE chips; prose after the prefix is human
guidance and may change without notice.
- `Live check (amber): ...` — evidence path: WORLD ✓ (masks found),
  COVERAGE ✓ with an `uncal` tag while the text contains `no threshold`.
  A future validated cutoff will replace the tag with a PASS/FAIL claim;
  that change needs the frozen-label validation, not this doc.
- `WORLD CHECK FAILED: ...` — no paper candidate: WORLD ✗, COVERAGE ✓
  (chunks were retrieved before segmentation ran).
- `NOT COVERED: ...` — retrieval empty: COVERAGE ✗, WORLD unevaluated
  (retrieval precedes any frame inspection; the app shows WORLD …).
- Any other amber (window/busy/timeout/failure/no-frame): no prefix, chips
  stay neutral. No prefix may ever imply a pass; all paths stay amber-only.

## Hard limits (unchanged)
- Calls claimed BEFORE providers run (budget-safe); max 4 per window.
- Any provider failure -> amber denial, never a step, never provider text.
- Phone must downscale frames to <= 4MP before send (contract rejects
  full-res phone JPEGs with 422). iOS timeout still 10s -> raise to ~180s
  in the same build as the downscale fix.
- Spend tonight: one $4 window reserved then closed, provider attempts
  empty -> no GPU burn. Modal dashboard is the final word on charges.

## Codi review fixes (PR14, same branch)
- Admission is token-based (pop-atomic, namespaced per window, never refilled); arming scripts must call arm_tokens after writing the active row.
- Timeout holds the slot until the worker drains; worker gates every paid stage on the deadline event.
- Frame source is explicit (Phone/Glass toggle, rendered == submitted, switch clears retained phone still, Ask gated per source); resolveFrame pinned by simulator tests.

## Clau review (PR14): earned color only
- Chips: only the two real failures earn color (WORLD ✗ / COVERAGE ✗ orange). All unestablished state renders gray …, including the evidence path — a green ✓ beside amber claimed what the backend documents it cannot (masks are candidates, retrieval always hits pre-Q1).
- Slot bound 150s (phone quits at 180); max_containers=1 so the process-local semaphore is global. Spend was already bounded by single-use tokens independent of instance count.
- Open judgment call (Miguel): pull the grounding score from the amber card prose, keeping it server-side only.

## Decision (Miguel, shoot day): grounding score stays on the card for the first shot, then reevaluated. Reviewers note the readout-didn't-transfer position.
