import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from analysis import AXES, calibrate, select_directions, question_scores, steering_summary
from budget import reserve_window


class ResearchChecks(unittest.TestCase):
    def test_planted_layer_recovered_without_fitting_heldout_or_ood(self):
        rng = np.random.default_rng(17)
        records, hidden = [], []
        for group in ('core', 'matched', 'ood'):
            for axis_index, axis in enumerate(AXES):
                for index in range(24):
                    positive = group != 'matched'
                    item = {'id': f'{axis}-{index}', 'label': axis, 'positive': positive, 'pool': group}
                    state = rng.normal(0, .08, (4, len(AXES)))
                    if positive: state[2, axis_index] += 4
                    records.append(item)
                    hidden.append(state)
        hidden = np.stack(hidden)
        directions, choice = select_directions(hidden, records)
        self.assertTrue(all(v['layer'] == 2 for v in choice.values()))
        changed = hidden.copy()
        for i, record in enumerate(records):
            if record['pool'] == 'ood': changed[i] *= -50
        directions2, choice2 = select_directions(changed, records)
        for axis in AXES:
            np.testing.assert_array_equal(directions[axis], directions2[axis])
            self.assertEqual(choice[axis]['layer'], choice2[axis]['layer'])
        self.assertEqual(question_scores(hidden, directions, choice).shape, (len(records),))

    def test_calibration_does_not_enable_product_gate(self):
        questions = [{'id': str(i), 'group': f'topic-{i // 2}', 'answerable': bool(i % 2)} for i in range(300)]
        scores = np.array([int(q['answerable']) * 10 - 5 for q in questions])
        result = calibrate(scores, questions)
        self.assertFalse(result['enabled'])
        self.assertTrue(result['phase3_review_required'])
        self.assertIn('test_auc', result)

    def test_small_or_single_class_split_cannot_force_a_threshold(self):
        result = calibrate(np.ones(10), [{'group': 'one-category', 'answerable': True} for _ in range(10)])
        self.assertFalse(result['enabled'])
        self.assertEqual(result['status'], 'insufficient_grouped_split')

    def test_constant_steering_does_not_claim_a_causal_result(self):
        result = steering_summary([-2, -1, 0, 1, 2], [1, 1, 1, 1, 1])
        self.assertFalse(result['semantic_causal_claim'])
        self.assertFalse(result['monotone_readout'])

    def test_grant_reservations_survive_restart_and_refuse_twenty_fifth_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'budget.json'
            for _ in range(24): reserve_window(path)
            self.assertEqual(len(json.loads(path.read_text())['windows']), 24)
            with self.assertRaisesRegex(ValueError, 'ceiling reached'):
                reserve_window(path)


if __name__ == '__main__': unittest.main()
