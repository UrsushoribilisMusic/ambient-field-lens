"""Explicit CPU-only wiki-export staging and receipted activation/rollback.

Run from backend: modal run -m providers.corpus_repair --help
No serving-app redeploy, no GPU definition and no automatic activation.
"""
import json
from pathlib import Path
import modal

HERE = Path(__file__).resolve().parent
app = modal.App('afl-corpus-repair-cpu')
volume = modal.Volume.from_name('afl-ross-chroma', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12').pip_install('chromadb==1.5.9')
         .add_local_dir(HERE, '/opt/afl/providers'))


@app.function(image=image, gpu=None, volumes={'/corpus': volume}, timeout=180,
              retries=0, min_containers=0, max_containers=1, scaledown_window=2)
def stage(request):
    import sys
    sys.path.insert(0, '/opt/afl')
    from providers.corpus_versions import BASELINE, database_path, stage_repair
    import chromadb
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
    embed = ONNXMiniLM_L6_V2(preferred_providers=['CPUExecutionProvider'])
    with chromadb.PersistentClient(path=str(database_path('/corpus', BASELINE))) as client:
        result = stage_repair(client, '/corpus', embed, request['text'], request['source'],
                              request['revision'], request['reviewer'])
    volume.commit()
    return result


def stage_receipted(request, *, output_root):
    """Private exact export and every attempted call saved before dispatch; no retry."""
    import time
    from generation.wording import append_event, DEFAULT_LEDGER, private_write, utc
    from readiness.adapters import canonical
    from providers.corpus_versions import digest
    folder = Path(output_root) / ('stage-' + str(time.time_ns()))
    folder.mkdir(parents=True, mode=0o700)
    private_write(folder / 'request.json', canonical(request))
    row = {'job_id': folder.name, 'event': 'attempt', 'provider': 'modal',
           'purpose': 'repair-corpus-stage-cpu', 'attempted_at': utc(),
           'request_sha256': digest(request), 'usage': None,
           'estimated_api_cost_usd_uncached': None, 'automatic_retries': 0}
    append_event(DEFAULT_LEDGER, row, unique_attempt=True)
    status = 'failed_no_retry'
    try:
        result = stage.remote(request)
        private_write(folder / 'response.json', canonical(result))
        private_write(folder / 'candidate-pin.json', canonical(result['candidate_pin']))
        status = 'complete'
        return result, folder
    finally:
        outcome = {**row, 'event': 'outcome', 'status': status, 'completed_at': utc()}
        private_write(folder / 'outcome.json', canonical(outcome))
        append_event(DEFAULT_LEDGER, outcome)


@app.local_entrypoint()
def main(operation: str = 'stage', passage: str = '', source: str = '',
         revision: str = '', reviewer: str = '', collection: str = '', before: str = ''):
    from providers.corpus_versions import load_pins
    from providers.client import rpc, retrieve
    root = Path.home() / 'Movies/Ambient-Field-Lens/repair-reingest'
    if operation == 'stage':
        text = Path(passage).read_text() if passage else ''
        from providers.corpus_versions import repair_record
        repair_record(text, source, revision, reviewer)  # validate before any call
        result, folder = stage_receipted(
            dict(text=text, source=source, revision=revision, reviewer=reviewer), output_root=root)
        print(json.dumps(result, indent=2))
        print('Private export, receipt and proposed pin:', folder)
    elif operation == 'select':
        pins = load_pins()
        if collection not in pins:
            raise ValueError('review_commit_and_deploy_candidate_pin_first')
        print(json.dumps(rpc('select_corpus', {'collection': collection, 'pin': pins[collection]}), indent=2))
    elif operation in ('query', 'compare'):
        # Audit-only frame identity, not an assertion that a camera was captured.
        # Query text is exact and unchanged before/after; no image or score call.
        from providers.corpus_versions import digest
        question = 'what to do if the paper is in the wrong position'
        result = retrieve(question, digest({'purpose': 'retrieval-only-film-audit'}))
        # Older deployed retrieval has no question field; exact call argument binds it.
        result['question'] = question
        if operation == 'compare':
            from providers.corpus_versions import compare_citations
            result = compare_citations(json.loads(Path(before).read_text()), result)
            from generation.wording import private_write
            from readiness.adapters import canonical
            import time
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            private_write(root / ('citation-comparison-' + str(time.time_ns()) + '.json'), canonical(result))
        print(json.dumps(result, indent=2))
    else:
        raise ValueError('operation_must_be_stage_select_query_or_compare')
