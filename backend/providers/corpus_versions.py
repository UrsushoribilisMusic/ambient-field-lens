"""Immutable Ross corpus versions; pins are code-reviewed, not ingestion output."""
import hashlib
import json
import math
from pathlib import Path

BASELINE = 'ross-manuals-2ca5f2f152267049'
PINS = Path(__file__).with_name('corpus-pins.json')
SELECTOR = 'afl-ross-corpus-selection'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def rows(snapshot):
    fields = ('ids', 'documents', 'metadatas', 'embeddings')
    if any(snapshot.get(k) is None for k in fields):
        raise ValueError('complete_corpus_snapshot_required')
    size = len(snapshot['ids'])
    if not size or any(len(snapshot[k]) != size for k in fields):
        raise ValueError('corpus_snapshot_shape')
    if len(set(snapshot['ids'])) != size:
        raise ValueError('duplicate_chunk_ids')
    result = []
    for ident, text, metadata, vector in zip(*(snapshot[k] for k in fields)):
        if (not isinstance(ident, str) or not isinstance(text, str) or not text.strip()
                or not isinstance(metadata, dict) or not vector
                or any(not math.isfinite(v) for v in vector)):
            raise ValueError('invalid_corpus_record')
        result.append({'id': ident, 'text': text, 'metadata': metadata, 'embedding': vector})
    return sorted(result, key=lambda r: r['id'])


def read_snapshot(collection):
    value = collection.get(include=['documents', 'metadatas', 'embeddings'])
    if hasattr(value.get('embeddings'), 'tolist'):
        value['embeddings'] = value['embeddings'].tolist()
    return value


def manifest(report, snapshot):
    records = rows(snapshot)
    if report['records'] != len(records):
        raise ValueError('corpus_count_changed')
    return {'schema': 'ross-corpus-version-v1', 'collection': report['collection'],
            'records': len(records), 'fingerprint': report['fingerprint'],
            'report_sha256': digest(report), 'snapshot_sha256': digest(records)}


def load_pins():
    return json.loads(PINS.read_text())


def guard(collection, report, snapshot, pins=None):
    pins = load_pins() if pins is None else pins
    pin = pins.get(collection)
    if pin is None:
        raise ValueError('unreviewed_corpus_version')
    actual = manifest(report, snapshot)
    if actual != pin or actual['collection'] != collection:
        raise ValueError('corpus_fingerprint_or_content_changed')
    return actual


def report_path(root, collection):
    return Path(root) / 'versions' / collection / 'ingestion-report.json'


def database_path(root, collection):
    return Path(root) / 'chroma' if collection == BASELINE else Path(root) / 'versions' / collection / 'chroma'


def read_report(root, collection):
    path = report_path(root, collection)
    # Legacy baseline stays valid without modifying its existing report.
    if collection == BASELINE and not path.exists():
        path = Path(root) / 'ingestion-report.json'
    return json.loads(path.read_text())


def guarded_collection(client, name, root, embed, pins=None):
    collection = client.get_collection(name, embedding_function=embed)
    report = read_report(root, name)
    guard(name, report, read_snapshot(collection), pins)
    return collection


def activate(client, root, embed, request, store, pins=None):
    """Atomic selector replacement only after the deployed pin and data match."""
    pins = load_pins() if pins is None else pins
    name = request.get('collection')
    if not isinstance(name, str) or name not in pins or request.get('pin') != pins[name]:
        raise ValueError('deployed_corpus_pin_mismatch')
    guarded_collection(client, name, root, embed, pins)
    store.put('active', name)
    return {'collection': name, 'pin': pins[name], 'gpu_used': False}


def retrieve_evidence(collection, question, frame, n_results=3):
    found = collection.query(query_texts=[question], n_results=n_results,
                             include=['documents', 'metadatas', 'distances'])
    chunks = [{'id': ident, 'text': text, 'source': meta['source'],
               'source_sha256': meta['source_sha256'], 'source_commit': meta['source_commit'],
               'distance': float(distance)}
              for ident, text, meta, distance in zip(found['ids'][0], found['documents'][0],
                                                    found['metadatas'][0], found['distances'][0])]
    if not chunks:
        raise ValueError('no_ross_evidence')
    if any(not math.isfinite(c['distance']) for c in chunks):
        raise ValueError('invalid_retrieval_distance')
    context = chunks[0]['text']
    # Only the top chunk feeds prefill, exactly as before; runners-up are audit data.
    return {'question': question, 'frame_sha256': frame, 'collection': collection.name, 'chunks': chunks[:1],
            'runners_up': chunks[1:], 'context': context,
            'context_sha256': hashlib.sha256(context.encode()).hexdigest(), 'gpu_used': False}


def compare_citations(before, after):
    """Film audit: evidence changed, never a coverage/readiness or verdict claim."""
    if before.get('question') != after.get('question') or not before.get('question'):
        raise ValueError('same_exact_question_required')
    old = (before.get('ranked') or before.get('chunks') or [None])[0]
    new = (after.get('chunks') or [None])[0]
    if not old or not new:
        raise ValueError('both_full_citations_required')
    return {'question': before['question'],
            'before_collection': before['collection'], 'after_collection': after['collection'],
            'before': old, 'after': new,
            'cited_chunk_changed': old['id'] != new['id'],
            'cited_text_changed': old['text'] != new['text'],
            'claim': 'retrieved evidence changed; no coverage flip or permission claim'}


def repair_record(text, source, revision, reviewer):
    """Use the exact human-authored exported wiki passage, never a model rewrite."""
    if (not isinstance(text, str) or not text.strip() or len(text.encode()) > 6000
            or any(not isinstance(v, str) or not v.strip() for v in (source, revision, reviewer))):
        raise ValueError('reviewed_wiki_export_required_max_6000_bytes')
    sha = hashlib.sha256(text.encode()).hexdigest()
    meta = {'source': source, 'source_sha256': sha, 'source_commit': revision,
            'reviewed_by': reviewer, 'provenance': 'human-authored-SM-wiki-export',
            'ingestion': 'immutable-documentation-repair-v1'}
    ident = digest({'text': text, 'metadata': meta})
    return {'id': ident, 'text': text, 'metadata': meta}


def stage_repair(client, root, embed, text, source, revision, reviewer, pins=None, client_factory=None):
    """Copy-on-write: never upsert/delete a baseline or previously staged version."""
    pins = load_pins() if pins is None else pins
    parent = guarded_collection(client, BASELINE, root, embed, pins)
    parent_rows = rows(read_snapshot(parent))
    if digest(parent_rows) != pins[BASELINE]['snapshot_sha256']:
        raise ValueError('parent_changed_during_staging')
    record = repair_record(text, source, revision, reviewer)
    fingerprint = digest({'parent': pins[BASELINE], 'addition': record})
    name = 'ross-repair-' + fingerprint[:24]
    report = {'collection': name, 'records': len(parent_rows) + 1,
              'fingerprint': fingerprint, 'parent': BASELINE,
              'parent_snapshot_sha256': pins[BASELINE]['snapshot_sha256'],
              'addition': {'id': record['id'], 'metadata': record['metadata']},
              'embedding': 'Chroma ONNX all-MiniLM-L6-v2 / CPUExecutionProvider',
              'gpu_used': False}
    expected_metadata = {'repair_fingerprint': fingerprint}
    if client_factory is None:
        import chromadb
        client_factory = lambda path: chromadb.PersistentClient(path=str(path))
    path = report_path(root, name)
    if path.parent.exists() and not path.exists():
        raise ValueError('incomplete_version_not_reused_operator_inspection_required')
    existed = path.exists()
    version_client = client_factory(database_path(root, name))
    try:
        if existed:
            collection = version_client.get_collection(name, embedding_function=embed)
            saved = json.loads(path.read_text())
            snap = rows(read_snapshot(collection))
            if (saved != report or collection.metadata != expected_metadata
                    or [r for r in snap if r['id'] != record['id']] != parent_rows
                    or len(snap) != len(parent_rows) + 1):
                raise ValueError('staged_version_changed')
            added = next(r for r in snap if r['id'] == record['id'])
            if {k: added[k] for k in ('id', 'text', 'metadata')} != record:
                raise ValueError('staged_addition_changed')
        else:
            # Preserve the parent's exact vectors; no re-embedding or source re-read.
            collection = version_client.create_collection(name, embedding_function=embed,
                                                  metadata=expected_metadata)
            collection.add(ids=[r['id'] for r in parent_rows],
                           documents=[r['text'] for r in parent_rows],
                           metadatas=[r['metadata'] for r in parent_rows],
                           embeddings=[r['embedding'] for r in parent_rows])
            collection.add(ids=[record['id']], documents=[record['text']], metadatas=[record['metadata']])
            snap = rows(read_snapshot(collection))
            if len(snap) != report['records'] or [r for r in snap if r['id'] != record['id']] != parent_rows:
                raise ValueError('copy_verification_failed')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2))
        added = next(r for r in rows(read_snapshot(collection)) if r['id'] == record['id'])
        if {k: added[k] for k in ('id', 'text', 'metadata')} != record:
            raise ValueError('staged_addition_changed')
        # Proposed explicit pin: caller must review/commit it before deployment/activation.
        proposed = manifest(report, read_snapshot(collection))
        return {'candidate_pin': proposed, 'addition_chunk_id': record['id'],
                'active_changed': False, 'review_required': True}
    finally:
        close = getattr(version_client, 'close', None)
        if close is not None:
            close()
