"""Synthetic logic tests; these do not evaluate image recognition accuracy."""
from dataclasses import replace
import unittest

from readiness.checks import Frame, State
from readiness.presence import Observation, Visibility, check_pen_holder_presence


class PresenceTests(unittest.TestCase):
    def setUp(self):
        self.frame = Frame('synthetic', 100, 60, 0, 'camera', 'rig', 'pose', 'pen', 'session')
        self.pen = Observation('synthetic', 100, 60, 'pen', Visibility.CLEAR, True, 'human_reference')
        self.holder = replace(self.pen, role='holder')

    def test_clear_present_pair_passes_observable_presence_only(self):
        result = check_pen_holder_presence(self.frame, self.pen, self.holder)
        self.assertEqual(result.state, State.PASS)
        self.assertIn('fitment not established', result.reason)

    def test_missing_pen_with_visible_holder_fails(self):
        result = check_pen_holder_presence(self.frame, replace(self.pen, observed_present=False), self.holder)
        self.assertEqual(result.state, State.FAIL)

    def test_covered_pen_fails_without_claiming_physical_absence(self):
        result = check_pen_holder_presence(self.frame, replace(self.pen, visible=Visibility.OCCLUDED, observed_present=None), self.holder)
        self.assertEqual(result.state, State.FAIL)
        self.assertIn('physical absence not inferred', result.reason)

    def test_missing_observation_is_unknown_not_absent(self):
        self.assertEqual(check_pen_holder_presence(self.frame, None, self.holder).state, State.UNKNOWN)
        self.assertEqual(check_pen_holder_presence(self.frame).state, State.UNKNOWN)

    def test_unknown_visibility_is_not_a_pass(self):
        self.assertEqual(check_pen_holder_presence(self.frame, self.pen, replace(self.holder, visible=Visibility.UNKNOWN)).state, State.UNKNOWN)

    def test_mismatched_evidence_and_untyped_values_do_not_pass(self):
        changes = [dict(frame_sha256='old'), dict(width=99), dict(role='paper'),
                   dict(source='llm_verdict'), dict(visible='clear'), dict(observed_present=1)]
        for change in changes:
            with self.subTest(change=change):
                self.assertEqual(check_pen_holder_presence(self.frame, replace(self.pen, **change), self.holder).state, State.UNKNOWN)

    def test_failed_role_preserves_other_unknown_role(self):
        result = check_pen_holder_presence(self.frame, replace(self.pen, observed_present=False), None)
        self.assertEqual(result.state, State.FAIL)
        self.assertIn('holder: missing', result.reason)

    def test_model_observations_are_inputs_without_scores(self):
        self.assertEqual(check_pen_holder_presence(self.frame, replace(self.pen, source='model_observation'),
                                                  replace(self.holder, source='model_observation')).state, State.PASS)


if __name__ == '__main__':
    unittest.main()
