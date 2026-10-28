# /assist Phase 3 contract — server-owned evidence, review-gated green

Status: contract frozen for implementation. No green verdict may be
returned by any server until this contract plus its implementation are
reviewed separately. The Phase 1 stub (always `verify`) stays live until
that review lands.

## Request (unchanged wire)

`POST /assist`, uncompressed JSON, existing size/timeout bounds:

```json
{ "query": "Can I draw this here?", "image_jpeg_base64": "<jpeg>" }
```

`query` non-blank, max 2000 chars. Frame optional; missing frame is an
immediate amber (no capture to judge).

## Response

```json
{
  "verdict": "verified",
  "checks": [
    {"name": "paper_present", "state": "pass", "reason": "...", "correction": ""},
    {"name": "pen_holder_observable_presence", "state": "pass", "reason": "...", "correction": ""},
    {"name": "pen_fitted", "state": "pass", "reason": "...", "correction": ""},
    {"name": "footprint_inside_paper", "state": "pass", "reason": "...", "correction": ""},
    {"name": "calibration_ready", "state": "pass", "reason": "...", "correction": ""},
    {"name": "approved_current_step", "state": "pass", "reason": "...", "correction": ""}
  ],
  "grounding": {"score": 0.93, "threshold": 0.90, "method": "hidden_contrastive_L27", "validated": true},
  "clearance": {"registration_error_mm": 2.1, "reading_uncertainty_mm": 1.5, "clearance_margin_mm": 80.0},
  "receipt": {"frame_sha256": "<hex>", "mask_id": "<id>", "chunk_ids": ["..."], "model": "sam-3.1", "score_model": "glimmer-30b"},
  "step": "Drawing footprint fits. Confirm the preview.",
  "detail": ""
}
```

Amber returns the same shape with `"verdict": "verify"`, `step: null`,
failing/unknown checks carrying their corrections, and no step text.

## Green rule (all required, no exceptions)

1. All six checks `pass` — exactly the composition in
   `docs/drawing-readiness-contract.md` v2. Unknown or fail anywhere
   is amber, and passing checks never hide another's failure.
2. `grounding.score >= grounding.threshold` with a validated method
   (frozen contrastive direction at its frozen layer). Unvalidated
   methods, missing scores, and thresholds below the reviewed value
   are amber.
3. `registration_error_mm + reading_uncertainty_mm << clearance_margin_mm`,
   all three stated per response. Marginal placements are amber.
4. Fresh frame (≤5s), bound receipt (frame SHA matches the judged frame),
   approved procedure step matched by exact source hash.

A missing frame, stale state, unreviewed method, or absent evidence is
amber with a named correction. There is no path to green that skips a
check, and no client-supplied score is trusted.

## Client rules (iOS)

- Render verdict, failing-check corrections, score-vs-threshold, and
  receipt identifiers (short frame SHA, chunk ids) on the HUD/detail view.
- Request timeout 10s; first-card goal 3s is measured, not blocking.
- Transport failure clears the HUD verdict (already implemented).
- No replay mode, no bundled sample green, no query-triggered overrides.
  The client cannot produce green by itself under any input.

## Review gate

Green-enabling implementation needs a second review covering: the
displaced-paper amber control demonstrated live (fault named, no step),
per-response stated numbers, and receipt checkability by a third party
cloning the repo. Until then the stub stays live.
