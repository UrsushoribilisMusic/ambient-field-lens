"""HTTP is mocked: verify the paid-call boundary and no-retry receipts."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error

from PIL import Image
from test_observation_adapters import model_response

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('model_batch_executor', TOOLS / 'execute_model_observation_batch.py')
executor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(executor)
from prepare_model_observation_batch import prepare
from prepare_sam_batch import CASES


class ModelExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        rows = []
        for index, (name, _, _) in enumerate(CASES):
            path = self.root / '2026-10-27/drawing-readiness' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new('RGB', (16, 12), (index, 0, 0)).save(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            record = dict(id='fixture'+str(index), frame=name, frame_sha256=digest,
                          capture_started_utc='2026-10-27T12:00:00+00:00', representative_frame_seconds=0)
            path.with_suffix('.capture.json').write_text(json.dumps(record))
            rows.append(dict(asset=str(path.relative_to(self.root)), frame_sha256=digest,
                             camera_profile='fixture', pose_bucket='fixture', source_record='fixture'))
        self.plan = prepare({'scenes': rows, 'profiles': [dict(id='fixture', width=16, height=12)]}, self.root)
        self.manifest = self.root / 'prepared.json'
        self.manifest.write_text(json.dumps(self.plan))

    def test_preflight_rejects_extra_options_changed_frames_and_budget_overrun(self):
        for change in ('tools', 'digest'):
            plan = copy.deepcopy(self.plan)
            if change == 'tools':
                plan['requests'][0]['request_body_template']['tools'] = []
            else:
                plan['requests'][0]['frame_sha256'] = 'f'*64
            with self.subTest(change=change), self.assertRaises(ValueError):
                executor.preflight(plan, self.root)
        ledger = self.root / '.local/state/ambient-field-lens/budget.json'
        ledger.parent.mkdir(parents=True)
        ledger.write_text(json.dumps({'cpu_and_build_reserve_usd': 19, 'windows': []}))
        with patch.object(executor.Path, 'home', return_value=self.root), self.assertRaisesRegex(ValueError, 'budget'):
            executor.preflight(self.plan, self.root)

    def test_one_http_failure_consumes_attempt_and_stops_without_retry(self):
        output = self.root / 'run'
        error = urllib.error.HTTPError('https://api.meta.ai/v1/responses', 429, 'private provider text', {}, None)
        with patch.dict(os.environ, {'MODEL_API_KEY': 'fixture-secret'}), patch.object(executor.Path, 'home', return_value=self.root), \
                patch.object(executor.urllib.request, 'urlopen', side_effect=error) as call, contextlib.redirect_stdout(io.StringIO()) as log:
            result = executor.execute(self.manifest, self.root, output)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(result[0]['adaptation'], 'http_error_no_retry')
        self.assertTrue((output/'01/attempt.json').exists())
        self.assertNotIn('fixture-secret', log.getvalue())
        self.assertNotIn('private provider text', log.getvalue())

    def test_six_mocked_responses_save_exact_requests_and_run_offline_checks(self):
        output = self.root / 'run'
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, budget):
                value = json.loads(model_response())
                value.update(model='muse-spark-1.3', created_at=time.time(), completed_at=time.time(),
                             usage={'input_tokens': 100, 'output_tokens': 100})
                return json.dumps(value).encode()
        with patch.dict(os.environ, {'MODEL_API_KEY': 'fixture-secret'}), patch.object(executor.Path, 'home', return_value=self.root), \
                patch.object(executor.urllib.request, 'urlopen', side_effect=lambda *args, **kw: Response()) as call, \
                contextlib.redirect_stdout(io.StringIO()) as log:
            result = executor.execute(self.manifest, self.root, output)
        self.assertEqual(call.call_count, 6)
        self.assertTrue(all(row['adaptation'] == 'accepted_archival' for row in result))
        self.assertTrue(all(row['archival_component_presence']['state'] == 'pass' for row in result))
        self.assertTrue(all(row['pipeline']['verdict'] == 'amber' for row in result))
        self.assertNotIn('fixture-secret', log.getvalue())
        self.assertEqual(len(list(self.root.glob('model-pipeline-*.json'))), 6)
        with patch.dict(os.environ, {'MODEL_API_KEY': 'fixture-secret'}), patch.object(executor.Path, 'home', return_value=self.root), self.assertRaises(FileExistsError):
            executor.execute(self.manifest, self.root, output)
