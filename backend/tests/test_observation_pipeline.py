"""End-to-end envelope to deterministic checks; fixtures are not model accuracy."""
import asyncio
from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import unittest

from readiness.adapters import Adapted, Mode, adapt_model, sha256
from readiness.checks import Mask, State
from readiness.pipeline import run
from test_observation_adapters import fixture, model_response


class ObservationPipelineTests(unittest.TestCase):
    def setUp(self):
        self.frame, self.binding, self.image, self.receipt = fixture()

    def model(self, objects=None, fitment=None, mode=Mode.LIVE):
        data = None if objects is None else {'schema_version': 'drawing-observations-v1',
                                            'objects': objects, 'fitment': fitment}
        response = model_response(data)
        binding = replace(self.binding, response_sha256=sha256(response))
        return adapt_model(self.frame, binding, self.image, self.receipt, response, now=103., mode=mode)

    def masks(self, model):
        # In-memory synthetic masks; never counted as real SAM detections.
        p = replace(model.provenance, semantic_origin='synthetic_fixture')
        paper = Mask(self.frame.sha256, 32, 24, frozenset({(1, 1), (2, 1)}), 'paper', True,
                     provenance=replace(p, role='paper', object_id='paper'))
        pen = Mask(self.frame.sha256, 32, 24, frozenset({(1, 1)}), 'pen', True,
                   provenance=replace(p, role='pen', object_id='pen'))
        return Adapted((paper, pen), (), None, p)

    def states(self, result):
        return {check.name: check.state for check in result.checks}

    def test_raw_model_outputs_drive_checks_but_do_not_supply_product_verdict(self):
        model = self.model()
        result = run(self.frame, (model, self.masks(model)), now=103., mode=Mode.LIVE)
        states = self.states(result)
        self.assertEqual(len(states), 6)
        for key in ('paper_present', 'pen_holder_observable_presence', 'pen_fitted'):
            self.assertIs(states[key], State.PASS)
        for key in ('footprint_inside_paper', 'calibration_ready', 'approved_current_step'):
            self.assertIs(states[key], State.UNKNOWN)
        self.assertFalse(result.report()['live_ready'])
        self.assertEqual(result.report()['verdict'], 'amber')

    def test_missing_pen_and_occluded_holder_cannot_hide_behind_model_fitment(self):
        for visibility, present in [('clear', False), ('occluded', None)]:
            model = self.model([{'role': 'pen', 'visibility': visibility, 'observed_present': present},
                                {'role': 'holder', 'visibility': 'clear', 'observed_present': True}],
                               {'visible': True, 'fitted': True})
            states = self.states(run(self.frame, (model, self.masks(model)), now=103., mode=Mode.LIVE))
            self.assertIs(states['pen_holder_observable_presence'], State.FAIL)
            self.assertIs(states['pen_fitted'], State.PASS)  # Raw contradiction preserved.

    def test_masks_do_not_invent_missing_model_observations(self):
        masks = self.masks(self.model())
        result = run(self.frame, (masks,), now=103., mode=Mode.LIVE)
        self.assertIs(self.states(result)['pen_holder_observable_presence'], State.UNKNOWN)
        self.assertIs(self.states(result)['pen_fitted'], State.UNKNOWN)

    def test_valid_ambiguous_sam_objects_do_not_erase_separate_presence_observations(self):
        model = self.model()
        bundle = self.masks(model)
        paper, pen = bundle.masks
        first = replace(pen, ambiguous=True)
        second = replace(first, provenance=replace(first.provenance, object_id='other-pen'))
        bundle = replace(bundle, masks=(paper, first, second))
        result = run(self.frame, (model, bundle), now=103., mode=Mode.LIVE)
        self.assertFalse(result.evidence_errors)
        self.assertIs(self.states(result)['pen_holder_observable_presence'], State.PASS)
        self.assertIs(self.states(result)['pen_fitted'], State.UNKNOWN)
        self.assertEqual(result.evidence_summary['ambiguous_mask_roles'], ['pen'])

    def test_duplicates_and_mismatches_reject_aggregate_instead_of_selecting_a_pass(self):
        model = self.model()
        for other in [model, replace(model, provenance=replace(model.provenance, camera='different'))]:
            result = run(self.frame, (model, other, self.masks(model)), now=103., mode=Mode.LIVE)
            self.assertTrue(result.evidence_errors)
            self.assertTrue(result.report()['evidence_summary']['aggregate_inputs_rejected'])
            self.assertTrue(all(c.state is State.UNKNOWN for c in result.checks))

    def test_stale_live_and_archive_in_live_mode_rejected(self):
        live = self.model()
        archive = self.model(mode=Mode.ARCHIVE)
        for bundle, now in [(live, 107.), (archive, 103.)]:
            result = run(self.frame, (bundle,), now=now, mode=Mode.LIVE)
            self.assertTrue(result.evidence_errors)
            self.assertTrue(all(c.state is State.UNKNOWN for c in result.checks))

    def test_archival_modes_and_record_provenance_cannot_be_mixed(self):
        model = self.model(mode=Mode.ARCHIVE)
        other = replace(model, observations=(replace(model.observations[0], provenance=None),))
        result = run(self.frame, (other,), now=103., mode=Mode.ARCHIVE)
        self.assertIn('mixed_record_provenance', result.evidence_errors)
        mismatch = replace(self.frame, surface_pose='moved')
        result = run(mismatch, (model,), now=103., mode=Mode.ARCHIVE)
        self.assertIn('frame_context_mismatch', result.evidence_errors)

    def test_no_evidence_is_six_unknown_not_a_blanket_pass(self):
        result = run(self.frame, (), now=103., mode=Mode.LIVE)
        self.assertEqual(len(result.checks), 6)
        self.assertTrue(all(c.state is State.UNKNOWN for c in result.checks))


@unittest.skipUnless(os.environ.get('AFL_S03_DIAGNOSTIC_DIR'), 'private S03 artifacts required')
class RealPipelineReplayTests(unittest.TestCase):
    def test_actual_s03_envelopes_reach_pipeline_without_clock_refresh(self):
        diagnostic = Path(os.environ['AFL_S03_DIAGNOSTIC_DIR'])
        spec = importlib.util.spec_from_file_location('pipeline_replay', Path(__file__).resolve().parents[2] / 'tools/replay_observation_adapters.py')
        replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(replay)
        frame, binding, image, receipt, response = replay.load_s03(diagnostic, diagnostic.parent / 'S03-restored-baseline.capture.json')
        bundle = asyncio.run(replay.adapt_sam(frame, binding, image, receipt, response,
                                              now=1793047200., mode=Mode.ARCHIVE))
        result = run(frame, (bundle,), now=bundle.provenance.response_completed_at, mode=Mode.ARCHIVE)
        self.assertEqual(result.evidence_errors, ())
        self.assertEqual(result.evidence_summary['mask_pixels'], {'paper': [12971], 'pen': [1642]})
        self.assertTrue(all(c.state is State.UNKNOWN for c in result.checks))
        self.assertFalse(result.report()['live_ready'])
