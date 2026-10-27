"""Replay saved S03 artifacts only. No network/model/secret/GPU/motion calls.

The request fingerprint is reconstructed, not claimed to be an original wire
digest. Local artifact association is explicit; S03 has no provider frame echo.
"""
import argparse
import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from PIL import Image

from readiness.adapters import (AdapterError, Binding, Mode, adapt_sam, parse_sse,
                                reconstructed_request_hash, sha256)
from readiness.checks import Frame, evaluate


def load_s03(diagnostic: Path, capture_path: Path):
    capture = json.loads(capture_path.read_text())
    image_path = Path(capture['frame'])
    if not image_path.is_absolute():
        image_path = capture_path.parent / image_path
    image = image_path.read_bytes()
    receipt_bytes = (diagnostic / 'attempt.json').read_bytes()
    response_bytes = (diagnostic / 'raw.sse').read_bytes()
    receipt = json.loads(receipt_bytes)
    events = parse_sse(response_bytes)
    response = events[-1]['response']
    with Image.open(image_path) as decoded:
        width, height = decoded.size
    captured_at = (datetime.fromisoformat(capture['capture_started_utc']).timestamp()
                   + capture['representative_frame_seconds'])
    if capture['frame_sha256'] != sha256(image):
        raise AdapterError('capture_image_digest_mismatch')
    frame = Frame(capture['frame_sha256'], width, height, captured_at,
                  capture['camera_id'], 'S03-archived-unmeasured-rig', 'S03-unregistered-surface',
                  'S03-unbound-archived-tool', '')
    binding = Binding(frame, 'meta-model-api', receipt['model'], response['id'],
                      datetime.fromisoformat(receipt['attempted_at']).timestamp(), receipt['prompt'],
                      'boxes', (('1', 'paper'), ('2', 'pen')), sha256(receipt_bytes), sha256(response_bytes),
                      reconstructed_request_hash(image, receipt), 'reconstructed_from_saved_receipt', False,
                      'Local saved receipt + raw SSE association; provider did not echo frame digest; capture time is clip-start plus offset estimate.')
    return frame, binding, image, receipt_bytes, response_bytes


async def replay(diagnostic, capture_path, now):
    frame, binding, image, receipt_bytes, response_bytes = load_s03(diagnostic, capture_path)
    bundle = await adapt_sam(frame, binding, image, receipt_bytes, response_bytes, now=now,
                             mode=Mode.ARCHIVE, saved_events_json=(diagnostic / 'events.json').read_bytes())
    try:
        await adapt_sam(frame, binding, image, receipt_bytes, response_bytes, now=now)
        live_rejection = None
    except AdapterError as error:
        live_rejection = str(error)
    try:
        bundle.require_live(frame, now=now)
        archive_rejection = None
    except AdapterError as error:
        archive_rejection = str(error)
    by_role = {mask.kind: mask for mask in bundle.masks}
    # Original completion clock, not a fabricated fresh frame. S03 is stale on
    # its own historical timeline, so all six evaluations correctly stay unknown.
    decision = evaluate(frame, paper=by_role.get('paper'), pen=by_role.get('pen'),
                        now=bundle.provenance.response_completed_at)
    return {'mode': Mode.ARCHIVE.value, 'frame_sha256': frame.sha256,
            'request_frame_age_seconds': binding.request_started_at - frame.captured_at,
            'capture_time_basis': 'clip start + representative offset estimate; not verified sensor timestamp',
            'normalized_masks': [{'kind': mask.kind, 'pixels': len(mask.pixels),
                                  'provenance': asdict(mask.provenance)} for mask in bundle.masks],
            'normalized_observation_count': len(bundle.observations), 'normalized_fitment': None,
            'provenance': asdict(bundle.provenance), 'warnings': bundle.warnings,
            'live_adaptation_rejected': live_rejection, 'archive_live_admission_rejected': archive_rejection,
            'historical_completion_clock': bundle.provenance.response_completed_at,
            'evaluations': [asdict(check) for check in decision.checks], 'verdict': decision.verdict,
            'gpu_eligible': False, 'geometry_accepted': False, 'network_calls': 0}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = await replay(args.diagnostic, args.capture, datetime.now(timezone.utc).timestamp())
    output = args.output or args.diagnostic / 'observation-adapter-replay.json'
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps({'mask_pixels': {m['kind']: m['pixels'] for m in report['normalized_masks']},
                      'request_frame_age_seconds': report['request_frame_age_seconds'],
                      'live_rejection': report['live_adaptation_rejected'],
                      'evaluations': len(report['evaluations']), 'verdict': report['verdict'], 'network_calls': 0}))


if __name__ == '__main__':
    asyncio.run(main())
