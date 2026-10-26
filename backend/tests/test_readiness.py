"""Synthetic adversarial fixtures; never counted as filmed calibration data."""
from dataclasses import replace
import unittest

from readiness.checks import (ApprovedProcedure, Calibration, Fitment, Footprint,
                              Frame, Mask, ProcedureStep, State, evaluate)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.frame = Frame('synthetic-image', 10, 10, 100, 'camera', 'rig', 'pose-1', 'pen-1', 'session-1')
        self.paper = Mask('synthetic-image', 10, 10, frozenset((x, y) for x in range(1, 9) for y in range(1, 9)), 'paper', True)
        self.pen = replace(self.paper, kind='pen', pixels=frozenset({(2, 2)}))
        self.fitment = Fitment('synthetic-image', 'pen-1', True, True)
        self.footprint = Footprint('synthetic-image', 'camera', 'rig', 'pose-1', frozenset({(3, 3), (4, 4)}), True, 2, 2)
        self.calibration = Calibration(100, True, True, 'session-1', 'pen-1', 'pose-1', True)
        self.step = ProcedureStep('synthetic-only', 'v1', 'preview', 'Check preview', 'synthetic-source')

    def run_checks(self, **changes):
        inputs = dict(frame=self.frame, paper=self.paper, pen=self.pen, fitment=self.fitment,
                      footprint=self.footprint, calibration=self.calibration, selected_step=self.step,
                      approved_procedure=ApprovedProcedure(self.step, True), now=101)
        inputs.update(changes)
        return evaluate(**inputs)

    def test_all_five_required_for_scoped_offline_green(self):
        result = self.run_checks()
        self.assertEqual(result.verdict, 'green')
        self.assertEqual(len(result.checks), 5)

    def test_every_missing_evidence_input_stays_amber_with_correction(self):
        for key in ('paper', 'pen', 'fitment', 'footprint', 'calibration', 'selected_step', 'approved_procedure'):
            with self.subTest(key=key):
                result = self.run_checks(**{key: None})
                self.assertEqual(result.verdict, 'amber')
                self.assertTrue(all(c.correction for c in result.checks if c.state is not State.PASS))

    def test_wrong_frame_dimensions_class_or_hidden_mask(self):
        for change in (dict(frame_sha256='old'), dict(width=9), dict(kind='table'),
                       dict(visible=False), dict(ambiguous=True), dict(pixels=frozenset({(-1, 2)}))):
            with self.subTest(change=change):
                self.assertEqual(self.run_checks(paper=replace(self.paper, **change)).verdict, 'amber')

    def test_empty_paper_is_observed_failure(self):
        result = self.run_checks(paper=replace(self.paper, pixels=frozenset()))
        self.assertEqual(result.checks[0].state, State.FAIL)

    def test_pen_mask_does_not_prove_fitment(self):
        for change in (dict(fitted=False), dict(fitted=None), dict(visible=False), dict(tool='brush'), dict(frame_sha256='old')):
            with self.subTest(change=change):
                self.assertEqual(self.run_checks(fitment=replace(self.fitment, **change)).verdict, 'amber')

    def test_paper_hole_fails_despite_identical_bounding_box(self):
        paper = replace(self.paper, pixels=self.paper.pixels - {(4, 4)})
        self.assertEqual(self.run_checks(paper=paper).checks[2].state, State.FAIL)

    def test_offscreen_footprint_is_not_clipped_to_pass(self):
        footprint = replace(self.footprint, cells=self.footprint.cells | {(10, 3)})
        self.assertEqual(self.run_checks(footprint=footprint).checks[2].state, State.FAIL)

    def test_invalid_geometry_does_not_pass(self):
        for change in (dict(registration_validated=False), dict(surface_pose='moved'), dict(rig='moved'),
                       dict(frame_sha256='old'), dict(cells=frozenset()), dict(margin_mm=0),
                       dict(margin_mm=float('nan')), dict(cells=frozenset({(1.2, 3)}))):
            with self.subTest(change=change):
                self.assertEqual(self.run_checks(footprint=replace(self.footprint, **change)).checks[2].state, State.UNKNOWN)

    def test_saved_ready_flag_does_not_prove_current_calibration(self):
        for change in (dict(binding_verified=False), dict(controller_session='previous-boot'),
                       dict(surface_pose='previous-pose'), dict(tool='another-pen'),
                       dict(observed_at=90), dict(observed_at=102), dict(observed_at=float('nan'))):
            with self.subTest(change=change):
                self.assertEqual(self.run_checks(calibration=replace(self.calibration, **change)).checks[3].state, State.UNKNOWN)

    def test_explicit_uncalibrated_state_is_failure(self):
        self.assertEqual(self.run_checks(calibration=replace(self.calibration, calibrated=False)).checks[3].state, State.FAIL)

    def test_exact_current_approved_step_required(self):
        for change in (dict(step='start'), dict(text='Skip preview'), dict(version='v0'), dict(source_sha256='other')):
            with self.subTest(change=change):
                self.assertEqual(self.run_checks(selected_step=replace(self.step, **change)).checks[4].state, State.FAIL)
        self.assertEqual(self.run_checks(approved_procedure=ApprovedProcedure(self.step, False)).verdict, 'amber')

    def test_stale_or_future_frames_invalidate_all_checks(self):
        for timestamp in (90, 102, float('nan')):
            result = self.run_checks(frame=replace(self.frame, captured_at=timestamp))
            self.assertEqual(result.verdict, 'amber')
            self.assertTrue(all(c.state is State.UNKNOWN for c in result.checks))


if __name__ == '__main__':
    unittest.main()
