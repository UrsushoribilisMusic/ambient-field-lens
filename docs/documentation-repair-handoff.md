# Documentation repair: evidence before and after

This is separate from PR14. No threshold, gate, /assist contract or verdict
changes. The supported film claim is **the cited evidence changed after a
human improved the documentation**, never “not covered → covered” or permission
to operate the robot.

## Before capture — 29 October, read-only CPU call

Exact question: `what to do if the paper is in the wrong position`

Original collection `ross-manuals-2ca5f2f152267049`, 38 records. The top full
stored passage is about calibration slopes and pen lift height; human reading
finds no procedure for correcting misplaced paper. The question is suitable
for the proposed documentation-repair demonstration, subject to Miguel's read.
This assessment is not a calibrated distance/coverage verdict.

| Rank | Full chunk ID | Distance | Source |
| --- | --- | --- | --- |
| 1 | `8135308218c2c50dfd8b0aec8c0a48b25782d42098b2af9d4aa03fb2d71ccbb6` | 0.8199027180671692 | atf-wiki/Topics/Calibration.md |
| 2 | `ddc2942ee79fe0e53ceffa020afa9aa1fb57c04db3fd47dda07a797ef4ea8e64` | 0.8298013210296631 | README.md |
| 3 | `d4ed86dba96660eeedf366fbf434f09cfc3c6dd431e8d676fd0007747bc90c17` | 0.8333027362823486 | COMMANDS.md |

Private film assets (full manual texts are not vendored into this repo):

- `~/Downloads/AFL-paper-position-before-passages.md`: full top passage and both runners-up.
- `~/Movies/Ambient-Field-Lens/2026-10-29/repair-reingest/before-evidence.json`: same exact ranking and text.
- Same directory, `before-capture.json`: original report and full 38-record
  snapshot including embeddings, plus the ranking. SHA in the public verification
  receipt `docs/verification/repair-before-retrieval-2026-10-29.json`.

Read-only Modal app `ap-CRz1i9zsDA4z1DTHXmJaAU` stopped with zero tasks after
capture. One CPU attempt/outcome ledgered. No GPU, model score, SAM or paid
hosted-model call. CPU billing is not assumed free. No live deployment touched.

## Versioning and the guard

`providers/corpus-pins.json` is the **code-reviewed allowlist**, not a manifest
that ingestion may grant itself. Each explicit pin binds the collection name,
full source fingerprint, exact count, report hash, and sorted full-record hash
(ID, text, source metadata, stored vectors). Retrieval verifies all of them.
It keeps only the top complete chunk in prefill as before; the two complete
runners-up are returned as audit data. The response also records its selected
pin. No ranking boost, forced citation, threshold or generated repair text.

Staging uses the exact UTF-8 export of a human-reviewed SM wiki passage, with
its stable page reference, revision and reviewer. A single passage of at most
6000 bytes is one new chunk: 38 becomes **39**, explicitly recorded in the
proposed new pin. A longer page must be deliberately reduced to the relevant
reviewed passage, not silently split or truncated.

The original DB `/corpus/chroma` and legacy `/corpus/ingestion-report.json`
are never changed. A new fingerprint-named collection and **separate DB** are
created under `/corpus/versions/ross-repair-<fingerprint>/chroma`, with its own
`ingestion-report.json`. The original records and vectors are copied exactly;
only the human addition is embedded, locally on CPU. Complete existing versions
are read-only on repeat staging. An incomplete or altered version aborts rather
than upserting over it. Failed staging cannot change the active version.

After staging, review and commit the **actual candidate pin** alongside the
baseline pin, and deploy the provider code with that registry. There is no
placeholder “approved 39” pin before the human text exists. The IAM-only
`select_corpus` RPC checks the deployed pin against the supplied pin, validates
the actual version, then changes one atomic selector entry. Retrieval reads
that selector once per request, defaults to the original baseline when absent,
and rejects unreviewed versions. Each Chroma client closes before volume reload
or commit; separate DBs avoid mutating the source SQLite store under the live reader.

## Shoot-day procedure

From the reviewed checkout, with `PYTHONPATH=backend` (or run from `backend/`):

1. Miguel writes and reviews the missing procedure **in SM wiki**. Export only
   that exact passage as a UTF-8 file. Retain its actual revision. This tool is
   an explicit wiki-export bridge, not a claim of automatic SM synchronization.
2. Stage it on CPU; this does not activate it:

   ```sh
   cd backend
   modal run -m providers.corpus_repair --operation stage \
     --passage /private/path/paper-position.txt \
     --source sm-wiki/ross/paper-position \
     --revision ACTUAL_WIKI_REVISION --reviewer Miguel
   ```

   Exact export, receipt and `candidate-pin.json` are saved privately under
   `~/Movies/Ambient-Field-Lens/repair-reingest/stage-*`. No retries. Use stable
   page references without authentication tokens. The source revision is supplied
   operator provenance, not a signed SM server attestation.
3. Review the staged contents and actual pin; add it keyed by its collection
   name to `providers/corpus-pins.json`. Keep the original baseline entry.
   Commit/review/deploy the updated provider app. **Coordinate the deployment
   with Muse**; this branch does not redeploy her shared serving app. Merely
   staging does not make a version trusted or available to the deployed code.
4. Switch using the deployed guard, not a raw Dict edit:

   ```sh
   modal run -m providers.corpus_repair --operation select --collection ross-repair-ACTUAL_FINGERPRINT
   modal run -m providers.corpus_repair --operation compare \
     --before /Users/miguelrodriguez/Movies/Ambient-Field-Lens/2026-10-29/repair-reingest/before-evidence.json
   ```

   Comparison runs retrieval only, with an audit identity explicitly unrelated
   to a real camera capture. It saves both full citations and reports whether
   the IDs **and texts actually changed**. If the old chunk remains first, say
   so; do not force the new ID or claim the shot worked. Confirm the new top
   ID is the staged `addition_chunk_id`. Then film the actual phone cards with
   the exact same query. Camera/SAM/readout calls remain Muse's window/ledger lane.
5. For a before reshoot, select the preserved original:

   ```sh
   modal run -m providers.corpus_repair --operation select --collection ross-manuals-2ca5f2f152267049
   ```

   Then restore the reviewed after version with the same selection command.
   Both paths retain full guard checks. Do not call the historical
   `recal/corpus_cpu.py::ingest` for this repair; that legacy path can overwrite
   the singleton ingestion report and is not the versioned repair workflow.

## Verification

Unit tests cover tampered text/metadata/vector/ID/count/report, unreviewed pins,
immutable/idempotent staging, incomplete-stage refusal, guarded activation and
rollback, exact-query citation comparisons and unchanged-evidence reporting.
`backend/tests/corpus_chroma_smoke.py` uses real ChromaDB 1.5.9 in temporary
local databases with synthetic embeddings: copy, close/reopen, one added chunk,
old vectors intact, idempotent retry. No network embeddings or GPU.
The actual archived 38-record snapshot independently matches the committed
baseline pin. A real 39-record SM repair and different after citation remain
pending Miguel's text and reviewed deployment; no completed payoff is claimed.
