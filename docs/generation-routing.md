# Hosted generation routing — 28 October 2026

Miguel authorized a second generation path on 28 October. This is an **offline
text-authoring tool**, not a live `/assist` provider or a scoring implementation.

| Work | Route |
| --- | --- |
| Pair phrasings, candidate step text, review copy | Baseten, exact `meta-models/muse-spark-open-1026` |
| Explicit text-generation overflow | Meta `muse-spark-1.3` |
| SAM segmentation / existing visual observation work | Existing Meta tools |
| All probes, residuals, Jacobians, readouts | Modal Glimmer only |

Hosted APIs supply generated text, not the hidden states used by our readouts.
No probe or readout path imports this package. No model alias substitution,
automatic overflow, retries, image calls, tools, label assignment or scoring.
New pair wording remains a draft for human review; never rewrite frozen inputs
or treat generated step text as an approved procedure or equipment command.
The independent visual-pair review remains pending. `/assist` stays default-deny.

## Prepare, inspect, execute once

From `backend/`, with Python 3.12 (standard library only):

```bash
python3.12 -m generation.wording \
  --job-id review-copy-20261028-01 --purpose review_copy \
  --input /absolute/private/path/to/prompt.txt
```

The default is a preview: route, exact model, request digest, rates and limits;
no secret fetched, prompt printed, network request or ledger mutation. Inspect
the input file directly. Add `--execute` for one paid call. Select `--provider
meta` only for an explicit overflow decision; a Baseten error does not trigger
another charge on Meta. Purposes are `pair_phrasings`, `step_text`, `review_copy`.
Default 2048 output tokens leaves reasoning headroom; allowed range64–4096.
Text input is capped at12000 UTF-8 bytes. These limits bound request size, not
provider billing or response latency; the tool is not an account-wide spend cap.

Runtime-only credentials are fetched with the existing hub `vault/agent-fetch.sh`
(`BASETEN_API_KEY` for Baseten, `MODEL_API_KEY` for Meta). No environment files,
credential-bearing command lines, credential stdout, persisted keys or provider
exception bodies. Requests are only sent to the fixed provider HTTPS endpoint;
redirects are refused. Public Baseten docs use an unversioned model alias; this
tool deliberately pins Miguel's exact `-1026` model and does not silently change
it. A response naming another model is retained as a mismatch, not accepted.

Default private output: `~/Movies/Ambient-Field-Lens/generation/<job-id>/`:
`request.json`, `attempt.json`, `response.json`, `outcome.json`, and `draft.txt`
only for complete, correctly identified, usage-reported outputs. No raw media,
prompts, generated drafts, credentials or private receipts are committed.

## Per-attempt ledger and accounting

Shared hosted-API ledger: `~/.local/state/ambient-field-lens/api-calls.jsonl`.
Baseten and Meta wording calls use the same append-only, flock-protected,
fsynced ledger. An attempt is saved before sending, then a separate outcome.
Both contain provider/model/purpose/request digest/time, token usage, rate basis,
estimated uncached cost or explicit unknown. Files are private (0600), job
folders0700. A job ID already in the ledger or output directory cannot rerun;
recovery inspects its saved response instead of issuing another paid call.

The full raw response retains provider usage details; completion token counts
already include reasoning, so reasoning is not added again. Cached inputs are
conservatively charged at the uncached estimate. Missing/malformed usage stays
`null`, never zero; HTTP/network failure may still be billable and is not retried.
Truncated, empty, model-mismatched or usage-missing responses do not publish a
usable draft. An interrupted process leaves an outstanding attempt, not a false
completion. Provider invoices remain authoritative.

Both Spark routes currently list$1.25/M input and$4.25/M output (checked28Oct).
Sources: [Baseten](https://www.baseten.co/library/muse-spark-open/) and
[Meta](https://dev.meta.ai/docs/pricing-rate-limits). Rates must be reviewed when
pricing changes. SAM costs are **not** inferred from Spark's token rates.

Bring existing/future Meta diagnostic receipts alongside the generation entries:

```bash
python3.12 -m generation.import_meta \
  --archive-root ~/Movies/Ambient-Field-Lens/2026-10-27/drawing-readiness
```

This reads saved `attempt.json` and response/events files, records source hashes,
imports each attempt once, and makes no network call. Re-run after future legacy
Meta batches, including failed attempts. Existing Meta tools remain unchanged;
they save their original private receipts, and this importer consolidates them.
Spark usage is estimated using published rates; SAM usage is retained where
available, but its cost remains unknown pending modality-specific reconciliation.
Historical imports are **not** new calls or fresh evidence. Do not double-count
imported source summaries and ledger rows.

The separate `budget.json` is the **Modal grant reservation ledger**. Hosted API
charges are not charged against or covered by the Modal grant. This tool never
reserves GPU windows, starts containers, or changes that ledger.

## Verification and current status

Seven offline tests cover exact routing, pre-send receipts, credential handling,
HTTP failure without retry/fallback, unknown usage, incomplete output, model
mismatch, unsupported work types, and idempotent historical import. No Baseten
request has been sent as part of implementation; model access is configured,
not live-tested here. Next authorized wording job supplies the first live receipt.
