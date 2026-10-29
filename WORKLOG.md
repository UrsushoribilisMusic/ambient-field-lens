# Codi — documentation repair re-ingest

Scope: capture exact current retrieval for “what to do if the paper is in the wrong position”, then prepare immutable versioned corpus ingestion and explicitly reviewed retrieval pins. Preserve original 38 chunks, original report, rollback and citation texts. No thresholds, verdict, /assist or PR14 changes; CPU only. Human-authored SM wiki passage is not available yet, so no repair content will be invented or activated.

1. Receipt one read-only CPU retrieval against the deployed corpus; save top three full passages, distances, original corpus snapshot privately.
2. Add deterministic version manifest validation, immutable copy-on-write ingestion and guarded activation/rollback.
3. Pin original and future approved versions by full content identity/count; test tampering, wrong counts and failed publication. Prepare reviewable PR and film handoff.
