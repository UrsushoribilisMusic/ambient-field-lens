"""Diagnostic split and provenance safeguards; synthetic data is not scene evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

spec = importlib.util.spec_from_file_location('measured_report', Path(__file__).resolve().parents[2] / 'tools/report_measured_registration.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MeasuredReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        Image.new('RGB', (896, 512)).save(self.root / 'frame.png')
        (self.root / 'positions.txt').write_text('synthetic fixture, not operator data')
        points = [(0, 0), (120, 0), (0, 120), (120, 120), (55, 120), (55, 0), (120, 65), (0, 65), (80, 90)]
        self.readings = dict(source_frame='frame.png', physical_measurements='positions.txt',
                             source_frame_sha256=hashlib.sha256((self.root / 'frame.png').read_bytes()).hexdigest(),
                             physical_measurements_sha256=hashlib.sha256((self.root / 'positions.txt').read_bytes()).hexdigest(),
                             image_size_px=[896, 512], fit_ids=[1, 2, 3, 4], validation_ids=[5, 6, 7, 8, 9], acceptance_bar_px=2.0,
                             points=[dict(id=i+1, plane_mm=[x, y], image_px=[x+100, y+100]) for i, (x, y) in enumerate(points)])

    def test_paper_plane_pass_does_not_accept_robot_geometry(self):
        result = module.report(self.readings, self.root)
        self.assertEqual(result['paper_plane_validation'], 'PASS')
        self.assertFalse(result['footprint_registration_accepted'])
        self.assertEqual(result['robot_coordinate_linkage'], 'unknown')

    def test_held_out_error_is_not_refitted_away(self):
        self.readings['points'][8]['image_px'][0] += 3
        result = module.report(self.readings, self.root)
        self.assertEqual(result['paper_plane_validation'], 'FAIL')
        self.assertAlmostEqual(result['held_out_max_px'], 3.0)
        self.assertLess(max(p['error_px'] for p in result['residuals'][:4]), 1e-8)

    def test_split_bar_and_identity_changes_rejected(self):
        for key, value in [('fit_ids', [1, 2, 3, 9]), ('acceptance_bar_px', 3.0),
                           ('source_frame_sha256', '0'*64), ('physical_measurements_sha256', '0'*64)]:
            readings = copy.deepcopy(self.readings)
            readings[key] = value
            with self.assertRaises(ValueError):
                module.report(readings, self.root)
