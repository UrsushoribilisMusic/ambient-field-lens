"""Explicitly authorized six-frame Meta batch; no Modal imports or GPU jobs.

No retries. Each attempt is recorded before sending. Raw requests/responses
stay private; output never prints credentials or provider text. Separate from
the live backend and never emits a robot command or green product verdict.
"""
import argparse
import base64
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

from PIL import Image

from readiness.adapters import Binding, Mode, adapt_model, canonical, sha256
from readiness.checks import Frame
from readiness.pipeline import run
from readiness.presence import check_pen_holder_presence
from report_scene_batch import capture_timestamp, load_records

ENDPOINT = 'https://api.meta.ai/v1/responses'
INPUT_PER_MILLION = 1.25
OUTPUT_PER_MILLION = 4.25
CONTEXT_LIMIT = 1_048_576


def utc():
    return datetime.now(timezone.utc).isoformat()


def credential():
    key = os.environ.get('MODEL_API_KEY')
    if not key:
        fetch = Path.home() / 'projects/agentic-fleet-hub/vault/agent-fetch.sh'
        result = subprocess.run([str(fetch), 'MODEL_API_KEY', 'dev'], cwd=fetch.parent.parent,
                                capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError('credential_unavailable')
        key = result.stdout.decode().strip()
    if not key or any(c.isspace() for c in key):
        raise RuntimeError('credential_invalid')
    return key


def preflight(plan, media_root):
    requests = plan['requests']
    if not 1 <= len(requests) <= 6 or plan.get('endpoint') != ENDPOINT:
        raise ValueError('Only reviewed Meta endpoint and at most six frames allowed')
    assets = []
    for item in requests:
        body = item['request_body_template']
        if (set(body) != {'model', 'stream', 'store', 'reasoning', 'max_output_tokens', 'metadata', 'input'}
                or body['model'] != 'muse-spark-1.3' or body['stream'] is not False
                or body['store'] is not False or body['max_output_tokens'] != 2048
                or body['metadata'] != {} or body['reasoning'] != {'effort': 'low'}):
            raise ValueError('Unreviewed model request options')
        content = body['input'][0]['content']
        if (len(body['input']) != 1 or body['input'][0]['role'] != 'user'
                or len(content) != 2 or content[0]['type'] != 'input_text'
                or content[1] != {'type': 'input_image', 'image_url': '{{verified_frame_data_url}}'}
                or sha256(content[0]['text'].encode()) != item['request_prompt_sha256']):
            raise ValueError('Unreviewed prompt or image binding')
        path = (media_root / item['frame_asset']).resolve()
        if not path.is_relative_to(media_root.resolve()) or not path.is_file():
            raise ValueError('Frame missing or outside private media root')
        data = path.read_bytes()
        if sha256(data) != item['frame_sha256']:
            raise ValueError('Frame digest mismatch')
        with Image.open(path) as image:
            if image.size != (item['width'], item['height']) or image.getexif().get(274, 1) != 1:
                raise ValueError('Frame dimensions/orientation mismatch')
        record = next(r for r in load_records(path.parent) if r['_path'].resolve() == path)
        capture_timestamp(record)  # Validate every clock before any paid call.
        assets.append((item, path, data))
    # Conservative full-context maximum rather than guessing image token counts.
    maximum = len(requests) * ((CONTEXT_LIMIT - 2048) * INPUT_PER_MILLION + 2048 * OUTPUT_PER_MILLION) / 1e6
    ledger = Path.home() / '.local/state/ambient-field-lens/budget.json'
    reserved = 0.
    if ledger.exists():
        budget = json.loads(ledger.read_text())
        reserved = budget['cpu_and_build_reserve_usd'] + sum(w['reserved_usd'] for w in budget['windows'])
    if reserved + maximum > 20:
        raise ValueError('Conservative API plus reserved research budget exceeds20USD')
    return assets, maximum, reserved


def execute(plan_path, media_root, output):
    media_root, output = media_root.resolve(), output.resolve()
    if not output.is_relative_to(media_root):
        raise ValueError('Raw output must stay inside the private media root')
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    assets, maximum, reserved = preflight(plan, media_root)
    key = credential()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'prepared-manifest.json').write_bytes(plan_bytes)
    authorization = {'authorized_at': utc(), 'basis': 'Miguel explicitly authorized Meta calls on2026-10-27; Modal GPU remains off',
                     'prepared_manifest_sha256': sha256(plan_bytes), 'max_requests': len(assets), 'automatic_retries': 0,
                     'conservative_full_context_api_bound_usd': maximum, 'existing_research_reserve_usd': reserved,
                     'pricing_source': 'https://dev.meta.ai/docs/pricing-rate-limits', 'gpu_used': False}
    (output / 'authorization.json').write_text(json.dumps(authorization, indent=2))
    results = []
    for index, (item, image_path, image) in enumerate(assets, 1):
        folder = output / f'{index:02d}'
        folder.mkdir()
        records = load_records(image_path.parent)
        record = next(r for r in records if r['_path'].resolve() == image_path)
        captured_at = capture_timestamp(record)
        frame = Frame(item['frame_sha256'], item['width'], item['height'], captured_at,
                      item['camera_profile'], item['pose_bucket'], record.get('surface_pose', 'archived-unregistered-surface'),
                      'ross-archived-pen', '')
        body = json.loads(json.dumps(item['request_body_template']))
        mime = 'image/png' if image.startswith(b'\x89PNG') else 'image/jpeg'
        body['input'][0]['content'][1]['image_url'] = 'data:' + mime + ';base64,' + base64.b64encode(image).decode()
        request_bytes = canonical(body)
        (folder / 'request.json').write_bytes(request_bytes)
        receipt = {'attempted_at': utc(), 'model': body['model'], 'image_sha256': frame.sha256,
                   'image_bytes': len(image), 'prompt': body['input'][0]['content'][0]['text'],
                   'metadata': {}, 'stream': False, 'store': False, 'reasoning': {'effort': 'low'}, 'max_output_tokens': 2048,
                   'max_requests': 1, 'automatic_retries': 0}
        receipt_bytes = canonical(receipt)
        with (folder / 'attempt.json').open('xb') as stream:
            stream.write(receipt_bytes)
        request = urllib.request.Request(ENDPOINT, data=request_bytes,
                                         headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        row = {'index': index, 'asset': item['frame_asset'], 'frame_sha256': frame.sha256,
               'camera_profile': item['camera_profile'], 'pose_bucket': item['pose_bucket']}
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = response.read(8_388_609)
                row['http_status'] = response.status
            (folder / 'response.json').write_bytes(raw)
            response = json.loads(raw)
            row['usage'] = response.get('usage', {})
            row['estimated_api_cost_usd_uncached'] = (row['usage'].get('input_tokens', 0)*INPUT_PER_MILLION
                                                     + row['usage'].get('output_tokens', 0)*OUTPUT_PER_MILLION) / 1e6
            binding = Binding(frame, 'meta-model-api', body['model'], response['id'],
                              datetime.fromisoformat(receipt['attempted_at']).timestamp(), receipt['prompt'],
                              'structured_json', (), sha256(receipt_bytes), sha256(raw), sha256(request_bytes),
                              'captured_request_bytes', False, 'Saved exact request/response and original frame digest; capture clock is clip-start plus offset, not sensor verified.')
            bundle = adapt_model(frame, binding, image, receipt_bytes, raw, now=time.time(),
                                 mode=Mode.ARCHIVE, request_bytes=request_bytes)
            adapted = {o.role: o for o in bundle.observations}
            presence = check_pen_holder_presence(frame, adapted.get('pen'), adapted.get('holder'))
            row.update(adaptation='accepted_archival', observations=[{'role': o.role, 'visibility': o.visible.value,
                       'observed_present': o.observed_present} for o in bundle.observations],
                       fitment=None if bundle.fitment is None else {'visible': bundle.fitment.visible, 'fitted': bundle.fitment.fitted},
                       archival_component_presence=asdict(presence), usage=response.get('usage', {}))
            row['pipeline'] = run(frame, (bundle,), now=bundle.provenance.response_completed_at, mode=Mode.ARCHIVE).report()
            usage = row['usage']
            row['estimated_api_cost_usd_uncached'] = (usage.get('input_tokens', 0)*INPUT_PER_MILLION
                                                     + usage.get('output_tokens', 0)*OUTPUT_PER_MILLION) / 1e6
            # Private executable replay manifest uses the same original image,
            # receipt, exact request and unmodified response; no clock refresh.
            manifest = {'frame': asdict(frame), 'image': str(image_path.relative_to(media_root)), 'mode': 'archival_replay',
                        'now': bundle.provenance.response_completed_at,
                        'evidence': [{'kind': 'model', 'binding': asdict(binding),
                                      'receipt': str((folder/'attempt.json').relative_to(media_root)),
                                      'response': str((folder/'response.json').relative_to(media_root)),
                                      'request': str((folder/'request.json').relative_to(media_root))}]}
            (media_root / f'model-pipeline-{output.name}-{index:02d}.json').write_text(json.dumps(manifest, indent=2))
        except urllib.error.HTTPError as error:
            row.update(http_status=error.code, adaptation='http_error_no_retry')
        except Exception as error:
            # Stable adapter reason codes are safe; arbitrary provider text is not.
            from readiness.adapters import AdapterError
            row.update(adaptation='failed_no_retry', reason=str(error) if isinstance(error, AdapterError) else type(error).__name__)
        results.append(row)
        (output / 'results.json').write_text(json.dumps({'authorization': authorization, 'results': results}, indent=2))
        print(json.dumps({'index': index, 'asset': row['asset'], 'http_status': row.get('http_status'),
                          'adaptation': row['adaptation'], 'presence': row.get('archival_component_presence', {}).get('state'),
                          'reason': row.get('reason')}), flush=True)
        if row['adaptation'] != 'accepted_archival':
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
