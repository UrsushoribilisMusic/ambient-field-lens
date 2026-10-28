"""Artifact runner and paid-batch preparation invariants; no external IO."""
import asyncio
from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

from readiness.adapters import sha256
from test_observation_adapters import fixture, model_response

TOOLS = Path(__file__).resolve().parents[2] / 'tools'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


runner = module('artifact_pipeline_runner', 'run_observation_pipeline.py')
# Planner shares the existing hash/profile-verified scene selector.
sys.path.insert(0, str(TOOLS))
planner = module('model_observation_planner', 'prepare_model_observation_batch.py')


class ManifestRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        frame, binding, image, receipt = fixture()
        response = model_response()
        binding = replace(binding, response_sha256=sha256(response))
        for filename, data in [('frame.png', image), ('receipt.json', receipt), ('response.json', response)]:
            (self.root / filename).write_bytes(data)
        self.manifest = {'frame': asdict(frame), 'image': 'frame.png', 'mode': 'archival_replay', 'now': 103.,
                         'evidence': [{'kind': 'model', 'binding': asdict(binding),
                                       'receipt': 'receipt.json', 'response': 'response.json'}]}

    def replay(self):
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(self.manifest))
        return asyncio.run(runner.replay(path))

    def test_raw_saved_response_reaches_checks_without_network(self):
        result = self.replay()
        states = {c['name']: c['state'] for c in result['checks']}
        self.assertEqual(states['pen_holder_observable_presence'], 'pass')
        self.assertEqual(states['pen_fitted'], 'unknown')  # No pen mask.
        self.assertEqual(result['network_calls'], 0)
        self.assertFalse(result['live_ready'])

    def test_corrupt_response_is_reported_and_does_not_contribute_partial_passes(self):
        (self.root / 'response.json').write_text('private content that must never be echoed')
        result = self.replay()
        self.assertTrue(result['evidence_errors'])
        self.assertTrue(all(c['state'] == 'unknown' for c in result['checks']))
        self.assertNotIn('private content', json.dumps(result))

    def test_external_assets_and_live_manifest_are_rejected(self):
        self.manifest['image'] = '../outside.png'
        with self.assertRaises(ValueError):
            self.replay()
        self.manifest.update(image='frame.png', mode='live')
        with self.assertRaisesRegex(ValueError, 'archival'):
            self.replay()


class ModelBatchTests(unittest.TestCase):
    def test_prepared_requests_are_label_blind_and_output_bounded(self):
        # Existing SAM selector is separately integration-tested for paths/hashes.
        from unittest.mock import patch
        scene = dict(frame_asset='scene.jpg', frame_sha256='a'*64, camera_profile='fixture', width=16,
                     height=12, pose_bucket='fixture', source_record='fixture', pair='fixture')
        with patch.object(planner, 'verified_scenes', return_value={'requests': [scene]*6,
                                                                   'source_inventory_sha256': 'b'*64}):
            result = planner.prepare({}, Path('/unused'))
        self.assertEqual(result['planned_requests'], 6)
        self.assertEqual(result['max_generated_tokens_total'], 12288)
        self.assertIsNone(result['approval'])
        self.assertIsNone(result['estimated_api_cost_usd'])
        self.assertFalse(result['execution_implemented'])
        for request in result['requests']:
            body = request['request_body_template']
            self.assertFalse(body['store'])
            self.assertFalse(body['stream'])
            self.assertEqual(body['max_output_tokens'], 2048)
            self.assertEqual(body['input'][0]['content'][0]['text'], planner.PROMPT)
            self.assertNotIn('reference_labels', body)
            self.assertNotIn('review_condition', body)
