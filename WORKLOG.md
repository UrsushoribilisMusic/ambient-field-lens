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
