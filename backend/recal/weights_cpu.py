"""Download and verify the declared public checkpoint. This app has no GPU function."""
import hashlib
import json
from pathlib import Path
import time

import modal

REPO = 'meta-models/Muse-Glimmer-30B'
EXPECTED_WEIGHT_BYTES = 59_553_435_272
VOLUME_NAME = 'glimmer-weights'
app = modal.App('ambient-field-lens-weights-cpu')
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
         .pip_install('huggingface_hub==1.33.0')
         .env({'HF_HUB_DISABLE_XET': '1', 'HF_HUB_DISABLE_TELEMETRY': '1'})
         .add_local_file(Path(__file__).with_name('source-manifest.json'), '/source-manifest.json'))


def verify_files(root, manifest):
    verified = []
    for entry in manifest['files']:
        path = root / entry['path']
        if not path.is_file() or path.stat().st_size != entry['bytes']:
            raise ValueError('Missing or wrong-sized source file: ' + entry['path'])
        actual_hash = None
        if entry.get('sha256'):
            digest = hashlib.sha256()
            with path.open('rb') as source:
                for chunk in iter(lambda: source.read(8 * 1024 * 1024), b''):
                    digest.update(chunk)
            actual_hash = digest.hexdigest()
            if actual_hash != entry['sha256']:
                raise ValueError('SHA-256 mismatch: ' + entry['path'])
        verified.append({'path': entry['path'], 'bytes': path.stat().st_size, 'sha256': actual_hash})
    weight_bytes = sum(e['bytes'] for e in verified if e['path'].endswith('.safetensors'))
    if weight_bytes != manifest['weight_bytes']:
        raise ValueError('Total weight byte count does not match source manifest')
    return verified


@app.function(image=image, gpu=None, cpu=(1, 2), memory=(4096, 8192),
              volumes={'/weights': volume}, timeout=1800, retries=0,
              min_containers=0, max_containers=1, buffer_containers=0,
              scaledown_window=2)
def download_and_verify():
    import importlib.metadata
    from huggingface_hub import snapshot_download

    started = time.time()
    manifest = json.loads(Path('/source-manifest.json').read_text())
    if manifest['repo'] != REPO or manifest['weight_bytes'] != EXPECTED_WEIGHT_BYTES:
        raise ValueError('Unexpected checkpoint manifest')
    root = Path('/weights/Muse-Glimmer-30B')
    root.mkdir(parents=True, exist_ok=True)
    marker = root / 'verified-download.json'
    marker.unlink(missing_ok=True)
    try:
        print(json.dumps({'stage': 'download', 'repo': REPO, 'revision': manifest['revision'],
                          'expected_weight_bytes': EXPECTED_WEIGHT_BYTES, 'gpu': False}), flush=True)
        snapshot_download(repo_id=REPO, revision=manifest['revision'], local_dir=str(root),
                          allow_patterns=[e['path'] for e in manifest['files']], max_workers=2)
        print('Download complete; checking file sizes and SHA-256 hashes on CPU.', flush=True)
        files = verify_files(root, manifest)
        config = json.loads((root / 'config.json').read_text())
        if config.get('dtype', config.get('torch_dtype')) != 'bfloat16':
            raise ValueError('Source configuration does not declare BF16')
        report = {'verified': True, 'repo': REPO, 'revision': manifest['revision'],
                  'weight_bytes': EXPECTED_WEIGHT_BYTES, 'source_file_bytes': sum(e['bytes'] for e in files),
                  'files': files, 'elapsed_seconds': round(time.time() - started, 2),
                  'gpu_used': False, 'huggingface_hub_version': importlib.metadata.version('huggingface_hub')}
        staged = marker.with_suffix('.tmp')
        staged.write_text(json.dumps(report, indent=2))
        staged.replace(marker)
        volume.commit()
        print(json.dumps(report, indent=2), flush=True)
        return report
    finally:
        # Retain resumable partial downloads if interrupted; a verification marker
        # is written only after every source check succeeds.
        volume.commit()


@app.local_entrypoint()
def main():
    report = download_and_verify.remote()
    out = Path(__file__).parents[2] / 'docs/verification/glimmer-download.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print('Saved CPU verification report:', out)
