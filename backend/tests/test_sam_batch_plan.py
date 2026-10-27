"""Review preparation only: synthetic assets, no requests or paid calls."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

from PIL import Image

spec = importlib.util.spec_from_file_location('batch_plan', Path(__file__).resolve().parents[2] / 'tools/prepare_sam_batch.py')
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class SamBatchPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        rows=[]
        for name, _, _ in planner.CASES:
            path=self.root/'2026-10-27/drawing-readiness'/name
            path.parent.mkdir(parents=True,exist_ok=True)
            Image.new('RGB',(16,12),'white').save(path)
            rows.append({'asset':str(path.relative_to(self.root)), 'frame_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                         'camera_profile':'fixture-profile', 'pose_bucket':'fixture-unmeasured','source_record':'fixture'})
        self.inventory={'scenes':rows,'profiles':[{'id':'fixture-profile','width':16,'height':12}]}

    def test_exact_review_batch_has_no_execution_approval_cost_guess_or_retry(self):
        result=planner.prepare(self.inventory,self.root)
        self.assertEqual(result['planned_requests'],6)
        self.assertFalse(result['execution_implemented'])
        self.assertEqual(result['network_calls_made'],0)
        self.assertIsNone(result['approval'])
        self.assertIsNone(result['estimated_api_cost_usd'])
        self.assertTrue(all(r['automatic_retries']==0 and r['mode']=='archival_replay' for r in result['requests']))

    def test_changed_image_is_not_silently_rebound(self):
        (self.root/self.inventory['scenes'][0]['asset']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'digest mismatch'):
            planner.prepare(self.inventory,self.root)

    def test_missing_ambiguous_and_external_assets_are_rejected(self):
        for change in ['missing','duplicate','external']:
            inventory=copy.deepcopy(self.inventory)
            if change=='missing':inventory['scenes'].pop()
            elif change=='duplicate':inventory['scenes'].append(inventory['scenes'][0])
            else:inventory['scenes'][0]['asset']='../../'+planner.CASES[0][0]
            with self.subTest(change=change),self.assertRaises(ValueError):
                planner.prepare(inventory,self.root)

    def test_profile_dimensions_are_verified_before_preparation(self):
        self.inventory['profiles'][0]['width']=17
        with self.assertRaisesRegex(ValueError,'profile/orientation'):
            planner.prepare(self.inventory,self.root)


if __name__=='__main__':unittest.main()
