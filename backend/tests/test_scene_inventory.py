"""Provenance and reporting regressions, with no camera/model/network access."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('scene_inventory', Path(__file__).resolve().parents[2] / 'tools/report_scene_batch.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class SceneInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / '2026-10-27/drawing-readiness'
        self.root.mkdir(parents=True)
        self.frame = self.root / 'reference.jpg'
        self.frame.write_bytes(b'synthetic fixture; image decoding mocked')
        self.sha = hashlib.sha256(self.frame.read_bytes()).hexdigest()
        self.record = {'id': 'S04', 'frame': self.frame.name, 'frame_sha256': self.sha,
                       'requested_condition': 'operator requested absent pen', 'review_status': 'unreviewed'}
        (self.root / 'S04.capture.json').write_text(json.dumps(self.record))

    def test_digest_mismatch_aborts_inventory(self):
        self.frame.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            inventory.digest(self.frame, self.sha)

    def test_external_path_and_symlink_are_rejected(self):
        outside = self.root.parent / 'outside.jpg'
        outside.write_bytes(b'outside')
        (self.root / 'link.jpg').symlink_to(outside)
        for value in ['../outside.jpg', str(outside), 'link.jpg']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                inventory.resolve_asset(self.root, value)

    def test_expected_requested_fault_never_becomes_a_reference_observation(self):
        with patch.object(inventory, 'dimensions', return_value=(896, 512)):
            report = inventory.build_report([self.root], {})
        row = report['scenes'][0]
        self.assertEqual(row['reference_presence_logic']['state'], 'unknown')
        self.assertEqual(row['actual_presence_check']['state'], 'unknown')
        self.assertEqual(row['actual_footprint_check']['state'], 'unknown')
        self.assertFalse(report['gpu_eligible'])

    def test_reference_fail_does_not_count_as_detector_output(self):
        labels = {'reference.jpg': {'frame_sha256': self.sha, 'pen': 'clear_not_observed', 'holder': 'clear_present', 'expected_presence': 'fail'}}
        with patch.object(inventory, 'dimensions', return_value=(896, 512)):
            report = inventory.build_report([self.root], labels)
        row = report['scenes'][0]
        self.assertEqual(row['reference_presence_logic']['state'], 'fail')
        self.assertEqual(row['actual_presence_check']['state'], 'unknown')
        self.assertFalse(row['reference_logic_disagreement'])
        self.assertFalse(report['gpu_eligible'])
        labels['reference.jpg']['frame_sha256'] = 'stale-other-frame'
        with patch.object(inventory, 'dimensions', return_value=(896, 512)), self.assertRaises(ValueError):
            inventory.build_report([self.root], labels)

    def test_reference_disagreement_is_preserved(self):
        labels = {'reference.jpg': {'frame_sha256': self.sha, 'pen': 'clear_not_observed', 'holder': 'clear_present', 'expected_presence': 'pass'}}
        with patch.object(inventory, 'dimensions', return_value=(896, 512)):
            report = inventory.build_report([self.root], labels)
        self.assertEqual(report['reference_logic_disagreements'], [report['scenes'][0]['asset']])

    def test_curated_manifest_merges_same_asset_without_duplicate_scene(self):
        curated = {**self.record, 'review_status': 'visually-reviewed', 'observed_condition': 'operator absent pen confirmed'}
        (self.root / 'review-manifest.json').write_text(json.dumps({'scenes': [curated]}))
        records = inventory.load_records(self.root)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['review_status'], 'visually-reviewed')

    def test_stream_dimensions_do_not_share_profile(self):
        self.assertNotEqual(inventory.camera_bucket(896, 512), inventory.camera_bucket(2880, 1616))
        self.assertNotEqual(inventory.camera_bucket(896, 512), inventory.camera_bucket(896, 512, True))

    def test_pose_bucket_is_coarse_and_supports_letter_suffix(self):
        self.assertEqual(inventory.pose_bucket({'id': 'S01b'}), 'tripod-A-unmeasured')
        self.assertEqual(inventory.pose_bucket({'id': 'S27@80', 'pose_bucket': 'tripod-F-backed-away'}), 'tripod-F-unmeasured')
        self.assertEqual(inventory.pose_bucket({'id': 'S31', 'pose_bucket': 'tripod-G-sideways'}), 'tripod-G-unmeasured')


if __name__ == '__main__':
    unittest.main()
