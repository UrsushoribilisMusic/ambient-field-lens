"""Prepare a hash-verified six-frame SAM review manifest. Cannot execute calls.

No network imports, API credentials or image upload. Full pixel dimensions stay
explicit; no resizing/cropping. Archived evaluations cannot become live inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

CASES = (
    ('S04-pen-missing.jpg', 'missing-pen; paper remains visible', 'tool-reference'),
    ('S27-clear-before-t030.jpg', 'clear before holder/paper occlusion', 'S27-visibility'),
    ('S27-occluded-t080.jpg', 'holder and much of paper obscured', 'S27-visibility'),
    ('S27-clear-after-t100.jpg', 'clear after occlusion removed', 'S27-visibility'),
    ('S28-before-move-t000.jpg', 'drawn outline on paper before displacement', 'paper-placement-F'),
    ('S30-paper-outside-pen-check.jpg', 'fixed pen visibly outside displaced paper', 'paper-placement-F'),
)


def prepare(inventory, media_root):
    rows = inventory['scenes']
    profiles = {profile['id']: profile for profile in inventory['profiles']}
    requests = []
    for name, condition, pair in CASES:
        matches = [row for row in rows if Path(row['asset']).name == name]
        if len(matches) != 1:
            raise ValueError('Batch needs one unambiguous inventoried asset: ' + name)
        row = matches[0]
        path = (media_root / row['asset']).resolve()
        if not path.is_relative_to(media_root.resolve()) or not path.is_file():
            raise ValueError('Batch frame missing or outside media root: ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != row['frame_sha256']:
            raise ValueError('Batch image digest mismatch: ' + name)
        profile = profiles[row['camera_profile']]
        with Image.open(path) as image:
            if image.size != (profile['width'], profile['height']) or image.getexif().get(274, 1) != 1:
                raise ValueError('Batch image profile/orientation mismatch: ' + name)
            image.load()
        requests.append({
            'frame_asset': row['asset'], 'frame_sha256': row['frame_sha256'],
            'camera_profile': row['camera_profile'], 'width': profile['width'], 'height': profile['height'],
            'pose_bucket': row['pose_bucket'], 'source_record': row['source_record'],
            'review_condition': condition, 'pair': pair, 'mode': 'archival_replay',
            'request_body_template': {'model': 'sam-3.1', 'input': [
                {'type': 'message', 'role': 'user', 'content': [
                    {'type': 'input_text', 'text': 'graph paper'},
                    {'type': 'input_image', 'image_url': '{{verified_frame_data_url}}'}]}],
                'stream': True, 'metadata': {'mask_encoding': 'one_bit'}},
            'semantic_role_origin': 'model_concept', 'role_binding': {'*': 'paper'},
            'automatic_retries': 0,
            'required_saved_outputs': ['exact sent request digest and receipt', 'original frame digest/profile',
                                       'raw SSE through response.completed', 'provider response ID and timestamps'],
        })
    return {'status': 'PREPARED_FOR_REVIEW_NOT_APPROVED', 'execution_implemented': False,
            'network_calls_made': 0, 'planned_requests': len(requests), 'automatic_retries': 0,
            'provider': 'meta-model-api', 'endpoint_reference': 'https://api.meta.ai/v1/responses',
            'approval': None, 'estimated_api_cost_usd': None,
            'cost_status': 'Unverified; review authorization and cost before any execution',
            'gpu_allowed': False, 'gpu_budget_ceiling_usd': 20,
            'source_inventory_sha256': hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest(),
            'notes': ['Review template only; this tool has no execute flag or network client.',
                      'Archived images preserve original clocks; no live admission or green decision.',
                      'This batch segments graph paper only, not pen fitment or autonomous holder presence.',
                      'Zero matches stays empty; multiple paper masks are ambiguous without validated association.',
                      'No largest-mask, nominal-marker or threshold-based shortcut to choose drawing paper.',
                      'Structured model observations need a separately reviewed invocation batch.'],
            'requests': requests}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--media-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = prepare(json.loads(args.inventory.read_text()), args.media_root)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'planned_requests': report['planned_requests'],
                      'execution_implemented': False, 'network_calls_made': 0}))


if __name__ == '__main__':
    main()
