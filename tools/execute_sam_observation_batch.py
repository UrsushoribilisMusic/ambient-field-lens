"""Authorized Meta paper/pen masks for the reviewed scenes; no paid retries."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image

from execute_model_observation_batch import credential
from readiness.adapters import sha256


def execute(plan_path, media_root, output):
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    cases = []
    for item in plan['requests']:
        path = (media_root / item['frame_asset']).resolve()
        if not path.is_relative_to(media_root.resolve()) or not path.is_file() or sha256(path.read_bytes()) != item['frame_sha256']:
            raise ValueError('SAM batch frame identity mismatch')
        with Image.open(path) as image:
            if image.size != (item['width'], item['height']):
                raise ValueError('SAM batch frame dimensions mismatch')
        for role, prompt in [('paper', 'graph paper'), ('pen', 'pen')]:
            cases.append((item, path, role, prompt))
    if not 1 <= len(cases) <= 12:
        raise ValueError('Only six reviewed frames/twelve still-image calls allowed')
    env = {**os.environ, 'MODEL_API_KEY': credential()}
    output.mkdir(parents=True, exist_ok=False)
    (output/'prepared-manifest.json').write_bytes(plan_bytes)
    (output/'authorization.json').write_text(json.dumps({'authorized_at': datetime.now(timezone.utc).isoformat(),
          'basis': 'Miguel authorized Meta Spark/SAM calls; Modal GPU remains forbidden',
          'prepared_manifest_sha256': sha256(plan_bytes), 'max_requests': len(cases), 'automatic_retries': 0,
          'prompts': {'paper': 'graph paper', 'pen': 'pen'}, 'price_per_image_usd': .0025,
          'maximum_segmentation_cost_usd': .0025*len(cases),
          'pricing_source': 'https://dev.meta.ai/docs/pricing-rate-limits', 'gpu_used': False}, indent=2))
    results = []
    for index, (item, image, role, prompt) in enumerate(cases, 1):
        folder = output/f'{index:02d}-{role}'
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('sam_mask_diagnostic.py')),
                                 '--image', str(image), '--output', str(folder), '--prompt', prompt],
                                 capture_output=True, env=env, timeout=110)
        summary = json.loads((folder/'summary.json').read_text()) if (folder/'summary.json').exists() else {}
        row = {'index': index, 'asset': item['frame_asset'], 'frame_sha256': item['frame_sha256'],
               'role': role, 'folder': folder.name, 'completed': summary.get('completed', False),
               'http_status': summary.get('http_status'), 'mask_tokens': summary.get('mask_tokens'),
               'returncode': result.returncode, 'automatic_retries': 0}
        results.append(row)
        (output/'results.json').write_text(json.dumps({'results': results}, indent=2))
        print(json.dumps(row), flush=True)
        if result.returncode or not row['completed']:
            break
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--media-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute-authorized-meta-batch', action='store_true', required=True)
    args = parser.parse_args()
    execute(args.manifest, args.media_root, args.output)
