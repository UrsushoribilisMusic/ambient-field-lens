"""SAM child process is mocked; verify explicit limits and no retry behavior."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image
from readiness.adapters import sha256

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('sam_batch_executor', TOOLS/'execute_sam_observation_batch.py')
executor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(executor)


class SamExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        image = self.root/'frame.png'
        Image.new('RGB', (16, 12)).save(image)
        self.plan = self.root/'plan.json'
        self.plan.write_text(json.dumps({'requests': [{'frame_asset': image.name, 'frame_sha256': sha256(image.read_bytes()),
                                                       'width': 16, 'height': 12}]}))

    def child(self, command, *, fail=False, **kwargs):
        folder = Path(command[command.index('--output')+1])
        folder.mkdir()
        (folder/'summary.json').write_text(json.dumps({'completed': not fail, 'http_status': 429 if fail else 200, 'mask_tokens': 0}))
        return SimpleNamespace(returncode=1 if fail else 0)

    def test_two_still_requests_per_frame_without_credentials_in_command_or_log(self):
        with patch.object(executor, 'credential', return_value='fixture-secret'), \
                patch.object(executor.subprocess, 'run', side_effect=self.child) as call, \
                contextlib.redirect_stdout(io.StringIO()) as log:
            rows = executor.execute(self.plan, self.root, self.root/'run')
        self.assertEqual(call.call_count, 2)
        self.assertEqual([r['role'] for r in rows], ['paper', 'pen'])
        self.assertNotIn('fixture-secret', log.getvalue())
        for args in call.call_args_list:
            self.assertNotIn('fixture-secret', ' '.join(args.args[0]))

    def test_failure_stops_before_second_call_and_changed_image_rejected_before_credentials(self):
        with patch.object(executor, 'credential', return_value='fixture-secret'), \
                patch.object(executor.subprocess, 'run', side_effect=lambda *a, **kw: self.child(*a, fail=True, **kw)) as call, \
                contextlib.redirect_stdout(io.StringIO()):
            rows = executor.execute(self.plan, self.root, self.root/'run')
        self.assertEqual(call.call_count, 1)
        self.assertEqual(len(rows), 1)
        (self.root/'frame.png').write_bytes(b'changed')
        with patch.object(executor, 'credential') as fetch, self.assertRaises(ValueError):
            executor.execute(self.plan, self.root, self.root/'different-run')
        fetch.assert_not_called()
