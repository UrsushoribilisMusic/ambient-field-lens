"""Join saved Spark and SAM artifacts on exact frames, without provider calls."""
import argparse
import asyncio
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path

from readiness.adapters import Binding, parse_sse, sha256
from readiness.checks import Frame
from run_observation_pipeline import replay


async def join(media_root, sam_run, output):
    sam_rows = json.loads((sam_run / 'results.json').read_text())['results']
    names = ['meta-spark-low-reasoning-smoke-20261027', 'meta-spark-low-reasoning-continuation-20261027',
             'meta-spark-s30-20261027']
    manifests = sorted(path for name in names for path in media_root.glob('model-pipeline-'+name+'-*.json'))
    results = []
    for source in manifests:
        manifest = json.loads(source.read_text())
        frame = Frame(**manifest['frame'])
        for row in sam_rows:
            if row['frame_sha256'] != frame.sha256 or not row['completed']:
                continue
            folder = sam_run / row['folder']
            receipt_bytes = (folder/'attempt.json').read_bytes()
            raw = (folder/'raw.sse').read_bytes()
            request = (folder/'request.json').read_bytes()
            receipt = json.loads(receipt_bytes)
            response = parse_sse(raw)[-1]['response']
            binding = Binding(frame, 'meta-model-api', 'sam-3.1', response['id'],
                              datetime.fromisoformat(receipt['attempted_at']).timestamp(), receipt['prompt'],
                              'concept', (('*', row['role']),), sha256(receipt_bytes), sha256(raw), sha256(request),
                              'captured_request_bytes', False, 'Exact saved Meta request/stream and original frame hash; archived scene clock.')
            manifest['evidence'].append({'kind': 'sam', 'binding': asdict(binding),
                  'receipt': str((folder/'attempt.json').relative_to(media_root)),
                  'response': str((folder/'raw.sse').relative_to(media_root)),
                  'events': str((folder/'events.json').relative_to(media_root)),
                  'request': str((folder/'request.json').relative_to(media_root))})
            manifest['now'] = max(manifest['now'], response['completed_at'])
        path = media_root / ('joined-'+Path(manifest['image']).stem+'.json')
        path.write_text(json.dumps(manifest, indent=2))
        result = await replay(path)
        result['asset'] = manifest['image']
        results.append(result)
        print(json.dumps({'asset': result['asset'], 'errors': result['evidence_errors'],
                          'components': {c['name']: c['state'] for c in result['archival_image_component_checks']},
                          'evidence': result['evidence_summary']}), flush=True)
    report = {'scope': 'archival image components, not live readiness or model accuracy benchmark',
              'network_calls': 0, 'gpu_used': False, 'results': results}
    output.write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--media-root', type=Path, required=True)
    parser.add_argument('--sam-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(join(args.media_root, args.sam_run, args.output))
