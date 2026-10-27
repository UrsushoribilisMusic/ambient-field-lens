"""Offline adapter fixtures plus optional real S03 archive replay, never calls."""
import asyncio
from dataclasses import replace
import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image

from readiness.adapters import (Adapted, AdapterError, Binding, Mode, adapt_model, adapt_sam,
                                canonical, reconstructed_request_hash, request_body_from_receipt, sha256)
from readiness.checks import (ApprovedProcedure, Calibration, Fitment, Footprint, Frame,
                              Mask, ProcedureStep, State, evaluate)


def fixture(model='fixture-observer', prompt_kind='structured_json'):
    stream = io.BytesIO()
    Image.new('RGB', (32, 24), 'white').save(stream, format='PNG')
    image = stream.getvalue()
    frame = Frame(sha256(image), 32, 24, 100., 'fixture-camera', 'fixture-rig', 'fixture-plane', 'fixture-pen', 'fixture-session')
    prompt = 'graph paper' if prompt_kind == 'concept' else 'fixture structured-observation request'
    metadata = {'mask_encoding': 'one_bit'} if model == 'sam-3.1' else {}
    receipt = canonical({'attempted_at': 101., 'model': model, 'image_sha256': frame.sha256,
                         'image_bytes': len(image), 'prompt': prompt, 'metadata': metadata})
    binding = Binding(frame, 'synthetic-provider', model, 'resp_fixture', 101., prompt,
                      prompt_kind, (('*', 'paper'),) if prompt_kind == 'concept' else (),
                      sha256(receipt), '', reconstructed_request_hash(image, json.loads(receipt)),
                      'reconstructed_from_saved_receipt', True, 'synthetic fixture, not real sensor evidence')
    return frame, binding, image, receipt


def model_response(data=None):
    if data is None:
        data = {'schema_version': 'drawing-observations-v1', 'objects': [
            {'role': 'pen', 'visibility': 'clear', 'observed_present': True},
            {'role': 'holder', 'visibility': 'clear', 'observed_present': True}],
            'fitment': {'visible': True, 'fitted': True}}
    return canonical({'id': 'resp_fixture', 'model': 'fixture-observer', 'status': 'completed',
                      'created_at': 102., 'completed_at': 102., 'error': None,
                      'output': [{'type': 'message', 'role': 'assistant',
                                  'content': [{'type': 'output_text', 'text': json.dumps(data)}]}]})


def empty_sam_response():
    response = {'id': 'resp_fixture', 'model': 'sam-3.1', 'created_at': 102.,
                'metadata': {'mask_encoding': 'one_bit'}, 'status': 'in_progress', 'error': None}
    part = {'type': 'output_text', 'text': '', 'annotations': []}
    message = {'id': 'msg_fixture', 'type': 'message', 'role': 'assistant', 'status': 'completed', 'content': [part]}
    lane = {'output_index': 0, 'content_index': 0, 'item_id': 'msg_fixture'}
    # Valid zero-match stream: one finalized empty text lane, no delta events.
    events = [{'type': 'response.created', 'sequence_number': 0, 'response': response},
              {'type': 'response.output_item.added', 'sequence_number': 1, 'output_index': 0,
               'item': {**message, 'status': 'in_progress', 'content': []}},
              {'type': 'response.content_part.added', 'sequence_number': 2, **lane, 'part': part},
              {'type': 'response.output_text.done', 'sequence_number': 3, **lane, 'text': ''},
              {'type': 'response.content_part.done', 'sequence_number': 4, **lane, 'part': part},
              {'type': 'response.output_item.done', 'sequence_number': 5, 'output_index': 0, 'item': message},
              {'type': 'response.completed', 'sequence_number': 6,
               'response': {**response, 'status': 'completed', 'completed_at': 102., 'output': [message]}}]
    return b''.join(b'data: ' + canonical(event) + b'\n\n' for event in events)


class ModelAdapterTests(unittest.TestCase):
    def setUp(self):
        self.frame, self.binding, self.image, self.receipt = fixture()
        self.response = model_response()
        self.binding = replace(self.binding, response_sha256=sha256(self.response))

    def adapt(self, response=None, binding=None, frame=None, image=None, receipt=None, now=103., mode=Mode.LIVE):
        return adapt_model(frame or self.frame, binding or self.binding,
                           self.image if image is None else image, self.receipt if receipt is None else receipt,
                           self.response if response is None else response, now=now, mode=mode)

    def test_explicit_observations_and_fitment_have_full_shared_provenance(self):
        bundle = self.adapt()
        self.assertEqual(len(bundle.observations), 2)
        self.assertTrue(bundle.fitment.fitted)
        self.assertEqual(bundle.fitment.tool, self.frame.tool)
        self.assertEqual(bundle.provenance.response_sha256, sha256(self.response))
        self.assertEqual(bundle.provenance.frame_sha256, sha256(self.image))
        self.assertEqual(bundle.provenance.request_digest_basis, 'reconstructed_from_saved_receipt')
        self.assertEqual(bundle.observations[0].provenance.semantic_origin, 'structured_model_observation')
        self.assertEqual(bundle.fitment.provenance.camera, self.frame.camera)
        self.assertIs(bundle.require_live(self.frame, now=103.), bundle)

    def test_stale_future_or_unverified_capture_is_rejected(self):
        for now in [99., 106., float('nan')]:
            with self.subTest(now=now), self.assertRaises(AdapterError):
                self.adapt(now=now)
        with self.assertRaisesRegex(AdapterError, 'capture_clock_unverified'):
            self.adapt(binding=replace(self.binding, capture_clock_verified=False))

    def test_captured_request_bytes_are_verified_without_claiming_reconstruction(self):
        request=json.dumps(request_body_from_receipt(self.image,json.loads(self.receipt))).encode()
        binding=replace(self.binding,request_sha256=sha256(request),request_digest_basis='captured_request_bytes')
        bundle=adapt_model(self.frame,binding,self.image,self.receipt,self.response,now=103.,request_bytes=request)
        self.assertEqual(bundle.provenance.request_digest_basis,'captured_request_bytes')
        for bad in [None,request+b' ',canonical({'model':'other'})]:
            with self.subTest(length=None if bad is None else len(bad)),self.assertRaises(AdapterError):
                adapt_model(self.frame,binding,self.image,self.receipt,self.response,now=103.,request_bytes=bad)

    def test_all_frame_identity_components_are_bound(self):
        changes = [dict(sha256='f'*64), dict(width=31), dict(camera='other'), dict(rig='other'),
                   dict(surface_pose='moved'), dict(tool='other'), dict(controller_session='reboot'), dict(captured_at=99.)]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(AdapterError):
                self.adapt(frame=replace(self.frame, **change))

    def test_corrupt_or_wrong_artifacts_are_rejected(self):
        for change in [dict(image=b'not an image'), dict(receipt=self.receipt+b' '),
                       dict(response=self.response+b' '), dict(binding=replace(self.binding, request_sha256='0'*64))]:
            with self.subTest(change=list(change)), self.assertRaises(AdapterError):
                self.adapt(**change)

    def test_provider_identity_and_terminal_state_are_checked_after_digest(self):
        for change in [dict(id='other'), dict(model='other'), dict(status='in_progress'),
                       dict(error={'message': 'do not echo me'}), dict(completed_at=1040.), dict(created_at=90.)]:
            value=json.loads(self.response); value.update(change); raw=canonical(value)
            with self.subTest(change=change), self.assertRaises(AdapterError) as result:
                self.adapt(response=raw, binding=replace(self.binding,response_sha256=sha256(raw)))
            self.assertNotIn('do not echo me', str(result.exception))

    def test_image_dimensions_and_orientation_are_verified_not_trusted(self):
        wrong = replace(self.frame, width=31)
        with self.assertRaisesRegex(AdapterError, 'image_dimensions'):
            self.adapt(frame=wrong, binding=replace(self.binding, frame=wrong))
        stream=io.BytesIO(); image=Image.new('RGB',(32,24)); exif=image.getexif(); exif[274]=6
        image.save(stream,format='JPEG',exif=exif); data=stream.getvalue()
        f=replace(self.frame,sha256=sha256(data)); receipt=json.loads(self.receipt)
        receipt.update(image_sha256=f.sha256,image_bytes=len(data)); receipt=canonical(receipt)
        binding=replace(self.binding,frame=f,receipt_sha256=sha256(receipt),request_sha256=reconstructed_request_hash(data,json.loads(receipt)))
        with self.assertRaisesRegex(AdapterError, 'orientation'):
            self.adapt(frame=f,image=data,receipt=receipt,binding=binding)

    def test_model_cannot_supply_verdict_or_unknown_fields(self):
        data=json.loads(json.loads(self.response)['output'][0]['content'][0]['text']);data['verdict']='green';raw=model_response(data)
        with self.assertRaisesRegex(AdapterError, 'schema'):
            self.adapt(response=raw,binding=replace(self.binding,response_sha256=sha256(raw)))

    def test_bad_roles_visibility_booleans_and_hidden_fitment_are_rejected(self):
        for change in ['duplicate','wrong_role','wrong_boolean','wrong_visibility','hidden_fitment']:
            data=json.loads(json.loads(self.response)['output'][0]['content'][0]['text'])
            if change=='duplicate':data['objects'][1]['role']='pen'
            elif change=='wrong_role':data['objects'][0]['role']='paper'
            elif change=='wrong_boolean':data['objects'][0]['observed_present']='yes'
            elif change=='wrong_visibility':data['objects'][0]['visibility']='confident'
            else:data['fitment']['visible']=False
            raw=model_response(data)
            with self.subTest(change=change),self.assertRaises(AdapterError):
                self.adapt(response=raw,binding=replace(self.binding,response_sha256=sha256(raw)))

    def test_unknown_observations_remain_unknown_without_fabricated_fitment(self):
        data={'schema_version':'drawing-observations-v1','objects':[{'role':'pen','visibility':'unknown','observed_present':None}],'fitment':None}
        raw=model_response(data);bundle=self.adapt(response=raw,binding=replace(self.binding,response_sha256=sha256(raw)))
        self.assertEqual(len(bundle.observations),1)
        self.assertIsNone(bundle.observations[0].observed_present)
        self.assertIsNone(bundle.fitment)

    def test_contradictory_model_fitment_pass_is_vetoed_by_presence_failure(self):
        data=json.loads(json.loads(self.response)['output'][0]['content'][0]['text'])
        data['objects'][0].update(visibility='occluded',observed_present=None)
        raw=model_response(data);bundle=self.adapt(response=raw,binding=replace(self.binding,response_sha256=sha256(raw)))
        paper=Mask(self.frame.sha256,32,24,frozenset({(5,5),(6,6)}),'paper',True)
        pen=replace(paper,kind='pen'); footprint=Footprint(self.frame.sha256,self.frame.camera,self.frame.rig,self.frame.surface_pose,frozenset({(5,5)}),True,2,2)
        calibration=Calibration(102,True,True,self.frame.controller_session,self.frame.tool,self.frame.surface_pose,True)
        step=ProcedureStep('fixture','v1','current','fixture step','source')
        result=evaluate(self.frame,paper,pen,bundle.fitment,footprint,calibration,step,ApprovedProcedure(step,True),
                        now=103,pen_observation=bundle.observations[0],holder_observation=bundle.observations[1])
        checks={check.name:check.state for check in result.checks}
        self.assertEqual(checks['pen_fitted'],State.PASS)
        self.assertEqual(checks['pen_holder_observable_presence'],State.FAIL)
        self.assertEqual(result.verdict,'amber')
        self.assertTrue(bundle.warnings)

    def test_archival_outputs_cannot_be_admitted_live_or_refreshed(self):
        bundle=self.adapt(now=10000.,mode=Mode.ARCHIVE)
        self.assertEqual(bundle.provenance.frame_captured_at,100.)
        with self.assertRaisesRegex(AdapterError,'archival_records_not_live'):
            bundle.require_live(self.frame,now=10000.)

    def test_live_bundle_rejects_stale_admission_or_mixed_records(self):
        bundle=self.adapt()
        with self.assertRaises(AdapterError):bundle.require_live(self.frame,now=106.)
        bad=replace(bundle.observations[0],frame_sha256='f'*64)
        with self.assertRaisesRegex(AdapterError,'mixed_record_provenance'):
            replace(bundle,observations=(bad,)).require_live(self.frame,now=103.)


class SamEmptyTests(unittest.IsolatedAsyncioTestCase):
    async def test_zero_matches_is_valid_but_does_not_invent_presence_or_fitment(self):
        frame,binding,image,receipt=fixture('sam-3.1','concept');raw=empty_sam_response();binding=replace(binding,response_sha256=sha256(raw))
        bundle=await adapt_sam(frame,binding,image,receipt,raw,now=103.)
        self.assertEqual(bundle.masks,())
        self.assertEqual(bundle.observations,())
        self.assertIsNone(bundle.fitment)

    async def test_incomplete_wrong_identity_and_event_copy_disagreement_rejected(self):
        frame,binding,image,receipt=fixture('sam-3.1','concept');raw=empty_sam_response()
        for value in [raw.split(b'\n\n')[0]+b'\n\n',raw.replace(b'resp_fixture',b'resp_other')]:
            with self.subTest(value_length=len(value)),self.assertRaises(AdapterError):
                await adapt_sam(frame,replace(binding,response_sha256=sha256(value)),image,receipt,value,now=103.)
        with self.assertRaisesRegex(AdapterError,'saved_event_artifacts_disagree'):
            await adapt_sam(frame,replace(binding,response_sha256=sha256(raw)),image,receipt,raw,now=103.,saved_events_json=b'[]')


S03=os.environ.get('AFL_S03_DIAGNOSTIC_DIR')


@unittest.skipUnless(S03,'Set AFL_S03_DIAGNOSTIC_DIR to replay private S03 artifacts; never calls provider')
class RealS03ReplayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('replay_adapters',Path(__file__).resolve().parents[2]/'tools/replay_observation_adapters.py')
        self.replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.replay)
        self.root=Path(S03)
        self.frame,self.binding,self.image,self.receipt,self.response=self.replay.load_s03(self.root,self.root.parent/'S03-restored-baseline.capture.json')
        self.now=self.binding.request_started_at+10

    async def adapt(self,frame=None,binding=None,response=None,mode=Mode.ARCHIVE,**kwargs):
        return await adapt_sam(frame or self.frame,binding or self.binding,self.image,self.receipt,
                               self.response if response is None else response,now=self.now,mode=mode,**kwargs)

    async def test_real_s03_decodes_two_correctly_offset_masks_and_preserves_semantic_origin(self):
        bundle=await self.adapt(saved_events_json=(self.root/'events.json').read_bytes())
        masks={m.kind:m for m in bundle.masks}
        self.assertEqual({k:len(v.pixels) for k,v in masks.items()},{'paper':12971,'pen':1642})
        self.assertTrue(all(105 <= x < 473 and 346 <= y < 409 for x,y in masks['paper'].pixels))
        self.assertEqual(masks['paper'].provenance.semantic_origin,'manual_box_prompt')
        self.assertEqual(masks['paper'].provenance.object_bounds,(105,346,473,409))
        self.assertEqual(masks['paper'].provenance.spatial_transform,'identity_only')
        self.assertFalse(masks['paper'].provenance.capture_clock_verified)
        self.assertEqual(bundle.observations,())
        self.assertIsNone(bundle.fitment)

    async def test_real_s03_is_stale_in_live_mode_and_archive_is_not_live(self):
        with self.assertRaisesRegex(AdapterError,'stale_or_future_frame'):
            await self.adapt(mode=Mode.LIVE)
        bundle=await self.adapt()
        with self.assertRaisesRegex(AdapterError,'archival_records_not_live'):bundle.require_live(self.frame,now=self.now)

    async def test_real_s03_wrong_frame_roles_and_stream_dimensions_rejected(self):
        for change in [dict(camera='other'),dict(width=895),dict(tool='changed')]:
            with self.subTest(change=change),self.assertRaises(AdapterError):await self.adapt(frame=replace(self.frame,**change))
        with self.assertRaises(AdapterError):await self.adapt(binding=replace(self.binding,object_roles=(('99','paper'),)))
        raw=self.response.replace(b'w=896',b'w=897')
        with self.assertRaises(AdapterError):await self.adapt(response=raw,binding=replace(self.binding,response_sha256=sha256(raw)))

    async def test_real_s03_reordered_events_and_changed_payload_rejected_atomically(self):
        events=json.loads((self.root/'events.json').read_text());events[1],events[2]=events[2],events[1]
        raw=b''.join(b'data: '+canonical(e)+b'\n\n' for e in events)
        with self.assertRaises(AdapterError):await self.adapt(response=raw,binding=replace(self.binding,response_sha256=sha256(raw)))
        with self.assertRaises(AdapterError):await self.adapt(response=self.response+b' ')

    async def test_real_s03_mask_budget_rejects_entire_adaptation(self):
        with patch('readiness.adapters.MAX_MASK_RASTER_PIXELS',1),self.assertRaisesRegex(AdapterError,'budget'):
            await self.adapt()

    async def test_real_s03_replay_has_six_evaluations_one_amber_no_network(self):
        report=await self.replay.replay(self.root,self.root.parent/'S03-restored-baseline.capture.json',self.now)
        self.assertEqual(len(report['evaluations']),6)
        self.assertEqual(report['verdict'],'amber')
        self.assertEqual(report['network_calls'],0)
        self.assertFalse(report['geometry_accepted'])


if __name__=='__main__':unittest.main()
