"""Fresh event ingestion of user-owned Ross manuals; no legacy chunker imports."""
import hashlib
import json
from pathlib import Path
import subprocess
import re
from urllib.parse import urlsplit, urlunsplit

import modal

SOURCES = ('README.md', 'COMMANDS.md', 'skills/huenit/SKILL.md',
           'skills/robot-ross/SKILL.md', 'docs/macos-feature-parity.md')
app = modal.App('ambient-field-lens-ross-corpus-cpu')
volume = modal.Volume.from_name('afl-ross-chroma', create_if_missing=True)
image = modal.Image.debian_slim(python_version='3.12').pip_install('chromadb==1.5.9')


def scrub_credentials(text):
    def clean_url(match):
        value = match.group(0)
        try:
            parts = urlsplit(value)
            host = parts.hostname or ''
            if ':' in host: host = '[' + host + ']'
            if parts.port: host += ':' + str(parts.port)
            return urlunsplit((parts.scheme, host, parts.path, '', parts.fragment))
        except ValueError:
            return '[redacted URL]'
    text = re.sub(r'(?:rtsp|rtmp|https?)://[^\s<>`]+', clean_url, text)
    return re.sub(r'(?im)((?:password|api_key|access_token|secret)\s*[:=]\s*)[^\s,;]+',
                  r'\1[redacted]', text)


def collect_manuals(source_root, words=240, overlap=40, wiki_root=None):
    if not 0 <= overlap < words:
        raise ValueError('Overlap must be smaller than chunk size')
    root = Path(source_root).resolve()
    commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    records, sources = [], []
    chosen = [(root / relative, relative) for relative in SOURCES]
    if wiki_root:
        wiki = Path(wiki_root).resolve()
        for relative in ('Overview.md', 'Subsystems/HardwareInterface.md',
                         'Subsystems/JobOrchestration.md', 'Topics/Calibration.md', 'Topics/Narration.md'):
            chosen.append((wiki / relative, 'atf-wiki/' + relative))
    for path, relative in chosen:
        if not path.is_file():
            continue
        content = path.read_bytes()
        if len(content) > 2 * 1024 * 1024:
            raise ValueError('Manual exceeds ingestion byte limit: ' + relative)
        digest = hashlib.sha256(content).hexdigest()
        cleaned = scrub_credentials(content.decode('utf-8'))
        cleaned_hash = hashlib.sha256(cleaned.encode()).hexdigest()
        source_commit = (subprocess.check_output(['git', '-C', str(path.parent), 'rev-parse', 'HEAD'], text=True).strip()
                         if relative.startswith('atf-wiki/') else commit)
        sources.append({'path': relative, 'sha256': digest, 'ingested_sha256': cleaned_hash,
                        'source_commit': source_commit})
        # Keep source order and overlap. Metadata points to the original document,
        # which remains outside this repo; generated text is stored only in Chroma.
        tokens = cleaned.split()
        for offset in range(0, len(tokens), words - overlap):
            chunk = ' '.join(tokens[offset:offset + words])
            if not chunk: continue
            key = hashlib.sha256((relative + '\0' + cleaned_hash + '\0' + str(offset)).encode()).hexdigest()
            records.append({'id': key, 'text': chunk, 'metadata': {
                'source': relative, 'source_sha256': digest, 'source_commit': source_commit,
                'word_offset': offset, 'provenance': 'existing-user-owned-Ross-manual',
                'ingestion': 'new-event-implementation', 'redacted': True}})
            if offset + words >= len(tokens): break
    if not records: raise ValueError('No supported Ross manuals found')
    fingerprint = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
    return records, sources, fingerprint


@app.function(image=image, gpu=None, cpu=(1, 2), memory=(2048, 4096),
              volumes={'/corpus': volume}, timeout=600, retries=0,
              min_containers=0, max_containers=1, buffer_containers=0,
              scaledown_window=2)
def ingest(records, sources, fingerprint):
    import chromadb
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

    client = chromadb.PersistentClient(path='/corpus/chroma')
    # Explicit CPU provider; this does not allocate a GPU or call an embedding API.
    embed = ONNXMiniLM_L6_V2(preferred_providers=['CPUExecutionProvider'])
    collection_name = 'ross-manuals-' + fingerprint[:16]
    collection = client.get_or_create_collection(collection_name, embedding_function=embed)
    for offset in range(0, len(records), 32):
        batch = records[offset:offset + 32]
        collection.upsert(ids=[r['id'] for r in batch], documents=[r['text'] for r in batch],
                          metadatas=[r['metadata'] for r in batch])
    if collection.count() != len(records):
        raise ValueError('Corpus count does not match deterministic source snapshot')
    queries = ['How do I calibrate the pen?', 'How do I write text on paper?']
    result = collection.query(query_texts=queries, n_results=min(3, len(records)), include=['metadatas', 'distances'])
    if not all(result['ids']): raise ValueError('Retrieval smoke check returned no records')
    report = {'collection': collection_name, 'records': collection.count(), 'sources': sources,
              'fingerprint': fingerprint, 'gpu_used': False,
              'embedding': 'Chroma ONNX all-MiniLM-L6-v2 / CPUExecutionProvider',
              'smoke_queries': queries, 'retrieved_ids': result['ids'],
              'retrieved_sources': [[m['source'] for m in row] for row in result['metadatas']]}
    Path('/corpus/ingestion-report.json').write_text(json.dumps(report, indent=2))
    volume.commit()
    return report


@app.function(image=image, gpu=None, cpu=(1, 2), memory=(2048, 4096),
              volumes={'/corpus': volume}, timeout=600, retries=0,
              min_containers=0, max_containers=1, buffer_containers=0, scaledown_window=2)
def query_evidence(collection_name, queries):
    import chromadb
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
    collection = chromadb.PersistentClient(path='/corpus/chroma').get_collection(
        collection_name, embedding_function=ONNXMiniLM_L6_V2(preferred_providers=['CPUExecutionProvider']))
    result = collection.query(query_texts=queries, n_results=3, include=['documents', 'metadatas'])
    return [[{'text': text, 'source': metadata['source'], 'source_sha256': metadata['source_sha256']}
             for text, metadata in zip(documents, metadatas)]
            for documents, metadatas in zip(result['documents'], result['metadatas'])]


@app.local_entrypoint()
def evidence(questions_path: str):
    qs = [json.loads(l) for l in Path(questions_path).read_text().splitlines() if l.strip()]
    report_path = Path(__file__).parents[2] / 'docs/verification/ross-ingestion.json'
    collection = json.loads(report_path.read_text())['collection']
    evidence = query_evidence.remote(collection, [q['prompt'] for q in qs])
    # Context text is a private runtime input, never a file in the public repo.
    output = Path('/tmp/afl-ross-question-evidence.json')
    output.write_text(json.dumps(evidence))
    output.chmod(0o600)
    print('Wrote private evidence for', len(evidence), 'questions:', output)


@app.local_entrypoint()
def main(source_root: str, wiki_root: str = ''):
    records, sources, fingerprint = collect_manuals(source_root, wiki_root=wiki_root or None)
    report = ingest.remote(records, sources, fingerprint)
    out = Path(__file__).parents[2] / 'docs/verification/ross-ingestion.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
