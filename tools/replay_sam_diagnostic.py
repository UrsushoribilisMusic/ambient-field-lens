"""Decode saved SAM events and run offline readiness. Makes no network calls.

Use PYTHONPATH=backend. Requires meta-sam-parser==0.1.0. Replays at the frame's
capture time, not as a live verdict. Does not invent fitment/calibration/steps.
"""
import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from meta_sam_parser import decode_mask_to_raster, image_segmentation_format, parse_responses_stream
from readiness.checks import Frame, Mask, evaluate


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    args = parser.parse_args()
    capture = json.loads(args.capture.read_text())
    receipt = json.loads((args.diagnostic / 'attempt.json').read_text())
    image = Path(capture['frame']).read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if digest != receipt['image_sha256'] or digest != capture['frame_sha256']:
        raise SystemExit('Image digest mismatch')
    async def events():
        for event in json.loads((args.diagnostic / 'events.json').read_text()):
            yield event
    parsed = await parse_responses_stream(events(), image_segmentation_format()).final_result()
    if parsed.outcome.status != 'completed':
        raise SystemExit('SAM stream did not complete')
    # Prompt identities are hand-specified only for this documented diagnostic.
    # They are NOT an autonomous semantic classification result.
    roles = {'1': 'paper', '2': 'pen'}
    masks = {}
    records = []
    for record in parsed.records:
        if record.kind != 'mask':
            continue
        bounds = record.bounds
        if bounds.right-bounds.left != record.mask.width or bounds.bottom-bounds.top != record.mask.height:
            raise SystemExit('Diagnostic needs explicit mask resampling; refusing assumed coordinates')
        raster = decode_mask_to_raster(record.mask)
        cells = frozenset((int(bounds.left) + i % record.mask.width, int(bounds.top) + i // record.mask.width)
                          for i, value in enumerate(raster) if value)
        role = roles.get(record.object_id)
        if role:
            masks[role] = Mask(digest, 896, 512, cells, role, True)
        records.append({'object_id': record.object_id, 'role_from_manual_prompt': role,
                        'bounds': asdict(bounds), 'nonzero_pixels': len(cells)})
    # Time is relative for offline replay; this is never returned to a live app.
    frame = Frame(digest, 896, 512, 0, 'ross-reolink-tripod', 'rig-2026-10-26',
                  'S03-paper-block-pose-unregistered', 'ross-pen', '')
    decision = evaluate(frame, paper=masks.get('paper'), pen=masks.get('pen'), now=0)
    report = {'mode': 'offline-replay-at-capture-time', 'image_sha256': digest,
              'prompt_semantics': 'manual boxes; recognition and fitment not established',
              'records': records, 'verdict': decision.verdict, 'checks': [asdict(c) for c in decision.checks],
              'gpu_eligible': False,
              'pending': ['complete hand-reviewed paired scene coverage', 'measured real camera registration',
                          'current controller session/tool/surface calibration binding',
                          'exact approved procedure evidence from corpus', 'validated model comparison']}
    (args.diagnostic / 'readiness-replay.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
