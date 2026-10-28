import copy
import unittest
import numpy as np
from test_paired import records
from trajectory_analysis import candidate_start, trajectory_indices, summarize_trajectory, ALL_POINTS


class TinyTokenizer:
    def decode(self, ids, **kwargs):
        return ''.join({0:'header', 1:' ', 2:'Do', 3:' this', 4:'.', 5:' wrong'}[i] for i in ids)


class TrajectoryTests(unittest.TestCase):
    def test_boundary_is_measured_and_no_candidate_tail_is_dropped(self):
        self.assertEqual(candidate_start(TinyTokenizer(), [0,1,2,3,4], 'Do this.'), 2)
        self.assertEqual(candidate_start(TinyTokenizer(), [0,2,3,4], 'Do this.'), 1)
        with self.assertRaises(ValueError):
            candidate_start(TinyTokenizer(), [0,2,3,5], 'Do this.')
        with self.assertRaises(ValueError):
            candidate_start(TinyTokenizer(), [2,3,4], 'Do this.')
    def test_position_offsets_are_causal_and_include_true_prefill(self):
        self.assertEqual(trajectory_indices(5), dict(true_prefill=0,early=1,mid=3,late=5))
        self.assertEqual(trajectory_indices(6)['mid'], 3)
        with self.assertRaises(ValueError): trajectory_indices(2)
    def test_test_scores_cannot_select_point_or_layer(self):
        r=records();s={p:np.zeros((36,2)) for p in ALL_POINTS}
        y=np.array([int(x['supported']) for x in r])
        s['mid'][:,1]=y
        before=summarize_trajectory(s,r)
        s['late'][24:,0]=y[24:]*100
        after=summarize_trajectory(s,r)
        self.assertEqual(before['selected_point'], 'mid')
        self.assertEqual(after['selected_point'], 'mid')
        self.assertEqual(after['selected_layer'], 1)
    def test_ties_choose_early_and_no_improvement_retires(self):
        r=records();s={p:np.zeros((36,1)) for p in ALL_POINTS}
        a=summarize_trajectory(s,r)
        self.assertEqual(a['selected_point'], 'early')
        self.assertEqual(a['decision'], 'retire')
        self.assertFalse(a['enabled'])
        self.assertFalse(a['beats_prior'])
    def test_true_prefill_is_a_control_not_a_trajectory_tuning_option(self):
        r=records();s={p:np.zeros((36,1)) for p in ALL_POINTS}
        s['true_prefill'][:,0]=[int(x['supported']) for x in r]
        a=summarize_trajectory(s,r)
        self.assertEqual(a['selected_point'], 'early')
        self.assertEqual(a['decision'], 'retire')
    def test_missing_point_fails_closed(self):
        with self.assertRaises(ValueError): summarize_trajectory({},records())

if __name__=='__main__':unittest.main()
