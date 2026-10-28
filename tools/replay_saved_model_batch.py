"""Re-adapt saved Meta responses without sending/repairing/retrying requests."""
import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import time

from readiness.adapters import AdapterError, Binding, Mode, adapt_model, sha256
from readiness.checks import Frame
from readiness.pipeline import run
from readiness.presence import check_pen_holder_presence
from report_scene_batch import capture_timestamp, load_records


def replay_batch(output, media_root):
    plan = json.loads((output / 'prepared-manifest.json').read_text())
    rows = []
    for index, item in enumerate(plan['requests'], 1):
        folder = output / f'{index:02d}'
        if not (folder / 'response.json').exists():
            continue
        image_path = (media_root / item['frame_asset']).resolve()
        if not image_path.is_relative_to(media_root.resolve()):
            raise ValueError('Image outside private root')
        image = image_path.read_bytes()
        if sha256(image) != item['frame_sha256']:
            raise ValueError('Image digest mismatch')
        record = next(r for r in load_records(image_path.parent) if r['_path'].resolve() == image_path)
        captured = capture_timestamp(record)
        frame = Frame(item['frame_sha256'], item['width'], item['height'], captured, item['camera_profile'],
                      item['pose_bucket'], record.get('surface_pose', 'archived-unregistered-surface'), 'ross-archived-pen', '')
        receipt_bytes, raw, request = ((folder / name).read_bytes() for name in ('attempt.json', 'response.json', 'request.json'))
        receipt, response = json.loads(receipt_bytes), json.loads(raw)
        binding = Binding(frame, 'meta-model-api', receipt['model'], response['id'],
                          datetime.fromisoformat(receipt['attempted_at']).timestamp(), receipt['prompt'],
                          'structured_json', (), sha256(receipt_bytes), sha256(raw), sha256(request),
                          'captured_request_bytes', False, 'Exact saved request/response and original frame digest; archived clip-offset timestamp.')
        row = {'asset': item['frame_asset'], 'frame_sha256': frame.sha256, 'usage': response.get('usage', {})}
        try:
            bundle = adapt_model(frame, binding, image, receipt_bytes, raw, now=time.time(), mode=Mode.ARCHIVE, request_bytes=request)
            observations = {o.role: o for o in bundle.observations}
            row.update(adaptation='accepted_archival', observations=[{'role': o.role, 'visibility': o.visible.value,
                       'observed_present': o.observed_present} for o in bundle.observations],
                       fitment=None if bundle.fitment is None else {'visible': bundle.fitment.visible, 'fitted': bundle.fitment.fitted},
                       archival_component_presence=asdict(check_pen_holder_presence(frame, observations.get('pen'), observations.get('holder'))),
                       pipeline=run(frame, (bundle,), now=bundle.provenance.response_completed_at, mode=Mode.ARCHIVE).report())
            manifest = {'frame': asdict(frame), 'image': str(image_path.relative_to(media_root)), 'mode': 'archival_replay',
                        'now': bundle.provenance.response_completed_at, 'evidence': [{'kind': 'model', 'binding': asdict(binding),
                        'receipt': str((folder/'attempt.json').relative_to(media_root)),
                        'response': str((folder/'response.json').relative_to(media_root)),
                        'request': str((folder/'request.json').relative_to(media_root))}]}
            (media_root / f'model-pipeline-{output.name}-{index:02d}.json').write_text(json.dumps(manifest, indent=2))
        except AdapterError as error:
            row.update(adaptation='rejected_archival', reason=str(error))
        rows.append(row)
    result = {'mode': 'archival_replay', 'network_calls': 0, 'gpu_used': False, 'results': rows}
    (output / 'replayed-results.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--saved-run', type=Path, required=True)
    parser.add_argument('--media-root', type=Path, required=True)
    args = parser.parse_args()
    result = replay_batch(args.saved_run, args.media_root)
    print(json.dumps({'network_calls': 0, 'results': [{'asset': r['asset'], 'adaptation': r['adaptation'],
                      'presence': r.get('archival_component_presence', {}).get('state'), 'fitment': r.get('fitment'),
                      'reason': r.get('reason')} for r in result['results']]}))
