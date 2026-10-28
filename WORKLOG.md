# Codi — Baseten wording generation routing, 2026-10-28

User authorizes Baseten for wording jobs: pair phrasings, step text, review copy.
Exact model meta-models/muse-spark-open-1026, endpoint https://inference.baseten.co/v1.
Runtime vault fetch BASETEN_API_KEY only; never print/store credentials. Meta
retains SAM and explicitly selected generation overflow. Modal Glimmer alone
retains probes/readouts. No hidden-state requests to hosted APIs.

Plan: add an offline generation CLI with default Baseten routing, explicit Meta
overflow, finite text/token caps, no automatic retries, exact private request /
response receipts and per-attempt append-only JSONL ledger shared by providers.
Publish pricing basis and distinguish reported usage from conservative token
cost estimates; missing usage is unknown, never free. Save attempt before send.
No live backend, fixtures, frozen labels, evaluation inputs or GPU modifications.
Test offline with fake transport including error, missing usage, truncation,
wrong model, routing, credential redaction and duplicate-attempt prevention.
Document usage and handoff; commit/push draft PR. No paid call just to prove a
connection; next authorized wording task uses this tool and records its usage.

## Implemented and CPU-verified

Added `backend/generation/wording.py` (default Baseten exact pinned model,
explicit Meta overflow), and `generation/import_meta.py` for historical receipt
consolidation. All three permitted wording purposes use private exact request /
response receipts, pre-send durable attempts, locked append-only hosted-API
ledger, usage-based uncached estimates, no retries or automatic fallbacks.
Unknown usage/cost remains null, and incomplete output is not published as a
usable draft. Runtime vault only; redirects rejected; no secret/error text output.

Seven new fake-transport tests pass. Full backend suite114 tests,107 pass and7
expected private-archive skips. No scoring/research/provider tests require paid
calls. Existing `/assist`, SAM tools, fixtures and Modal modules untouched.
Imported22 historical attempts:7 Spark and15 SAM, all with token usage. Known
Spark uncached estimates total$0.0393445; SAM token-rate cost remains unknown,
not zero. Import makes no calls, is idempotent and does not modify originals.
Modal grant ledger remains separate. No Baseten/Meta calls, model sampling,
GPU windows or hardware activity during this implementation. Baseten configured
but not live-tested here; next authorized wording job produces its first receipt.
PR review required; pending visual labels remain pending.
