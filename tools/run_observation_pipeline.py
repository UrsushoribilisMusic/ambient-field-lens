"""Replay a local artifact manifest end to end; no network, secrets or GPU.

Paths must stay inside the manifest directory. Manifest binding includes exact
frame context; timestamps are preserved. CLI deliberately accepts archives only.
"""
import argparse
import asyncio
import json
from pathlib import Path

from readiness.adapters import AdapterError, Binding, Mode, adapt_model, adapt_sam, _json
from readiness.checks import Frame
from readiness.pipeline import run


def asset(root, name, max_bytes):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size > max_bytes:
        raise AdapterError('replay_asset_path_or_budget_invalid')
    return path.read_bytes()


async def replay(path):
    root = path.parent
    manifest = _json(path.read_bytes())
    if manifest['mode'] != Mode.ARCHIVE.value:
        raise AdapterError('replay_manifest_must_be_archival')
    frame = Frame(**manifest['frame'])
    image = asset(root, manifest['image'], 33_554_432)
    bundles, errors = [], []
    for artifact in manifest['evidence']:
        try:
            fields = dict(artifact['binding'])
            fields['frame'] = Frame(**fields['frame'])
            fields['object_roles'] = tuple(tuple(pair) for pair in fields['object_roles'])
            binding = Binding(**fields)
            receipt = asset(root, artifact['receipt'], 1_048_576)
            response = asset(root, artifact['response'], 8_388_608)
            request = asset(root, artifact['request'], 50_331_648) if artifact.get('request') else None
            kwargs = dict(now=manifest['now'], mode=Mode.ARCHIVE, request_bytes=request)
            if artifact['kind'] == 'sam':
                events = asset(root, artifact['events'], 8_388_608) if artifact.get('events') else None
                bundle = await adapt_sam(frame, binding, image, receipt, response,
                                         saved_events_json=events, **kwargs)
            elif artifact['kind'] == 'model':
                bundle = adapt_model(frame, binding, image, receipt, response, **kwargs)
            else:
                raise AdapterError('replay_artifact_kind_invalid')
            bundles.append(bundle)
        except AdapterError as error:
            errors.append(str(error))
    result = run(frame, tuple(bundles) if not errors else (), now=manifest['now'], mode=Mode.ARCHIVE).report()
    result['frame_sha256'] = frame.sha256
    result['historical_evaluation_time'] = manifest['now']
    result['evidence_errors'] = errors + result['evidence_errors']
    result['evidence_summary']['aggregate_inputs_rejected'] = bool(result['evidence_errors'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(replay(args.manifest))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('verdict', 'live_ready', 'evidence_errors', 'evidence_summary', 'network_calls')}))
