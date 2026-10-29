"""Runtime refusal/binding tests. No paid calls, hardware motion or green paths."""
from dataclasses import replace
import json
import unittest
import numpy as np
from test_observation_adapters import fixture,model_response
from readiness.adapters import adapt_model,Mode,canonical,sha256
from readiness.checks import Frame,Mask
from providers.pen_presence import observation_result,replay
from providers.measured_geometry import paper_translation,paper_boundary_from_mask,compute
from providers.robot_state import assess

class PresenceTests(unittest.TestCase):
    def adapted(self,present=True,visibility='clear',holder=True):
        frame,binding,image,receipt=fixture()
        data={'schema_version':'drawing-observations-v1','objects':[
            {'role':'pen','visibility':visibility,'observed_present':present},
            {'role':'holder','visibility':'clear','observed_present':holder}], 'fitment':None}
        response=model_response(data);binding=replace(binding,response_sha256=sha256(response))
        return frame,adapt_model(frame,binding,image,receipt,response,now=103.,mode=Mode.LIVE)

    def test_present_and_absent_never_produce_green_or_contact(self):
        for present,state in ((True,'pass'),(False,'fail')):
            frame,bundle=self.adapted(present)
            result=observation_result(frame,bundle,mode=Mode.LIVE,now=103.)
            self.assertEqual(result['check']['state'],state)
            self.assertEqual(result['verdict'],'verify');self.assertIsNone(result['step'])
            self.assertFalse(result['contact_established']);self.assertFalse(result['fitment_established'])

    def test_occlusion_empty_holder_uncertainty_and_stale_inputs(self):
        for present,visible,holder in ((None,'occluded',True),(False,'clear',False)):
            f,b=self.adapted(present,visible,holder)
            r=observation_result(f,b,mode=Mode.LIVE,now=103.)
            self.assertEqual(r['check']['state'],'unknown')
        f,b=self.adapted()
        with self.assertRaises(ValueError):observation_result(f,b,mode=Mode.LIVE,now=106.)

    def test_archive_cannot_be_promoted_to_live(self):
        f,b=self.adapted()
        archive=replace(b,provenance=replace(b.provenance,mode=Mode.ARCHIVE.value))
        with self.assertRaises(ValueError):observation_result(f,archive,mode=Mode.LIVE,now=103.)

class GeometryTests(unittest.TestCase):
    def test_signed_correction_moves_paper_not_robot(self):
        r=paper_translation([(0,0),(100,0),(100,100),(0,100)],[(90,30),(110,30),(110,50),(90,50)],2,np.eye(3))
        self.assertAlmostEqual(r['paper_shift_robot_mm'][0],12.)
        self.assertAlmostEqual(r['paper_shift_robot_mm'][1],0.)
        self.assertIn('Move the paper +12.000',r['correction'])
        self.assertIsNone(r['step'])

    def test_measured_axis_scale_and_impossible_size(self):
        r=paper_translation([(0,0),(100,0),(100,100),(0,100)],[(90,30),(110,30),(110,50),(90,50)],2,np.diag([2.,1.,1.]))
        self.assertAlmostEqual(r['paper_shift_robot_mm'][0],6.)
        r=paper_translation([(0,0),(10,0),(10,10),(0,10)],[(0,0),(20,0),(20,20),(0,20)],1,np.eye(3))
        self.assertIsNone(r['correction'])

    def test_hole_refuses_convex_correction_and_missing_measurements_unknown(self):
        paper=Mask('a'*64,100,100,frozenset((x,y) for x in range(10,90) for y in range(10,90))-{(50,50)},'paper',True)
        self.assertIsNone(paper_boundary_from_mask(paper,np.eye(3),1))
        frame=Frame('a'*64,100,100,100.,'cam','rig','surface','tool','session')
        self.assertEqual(compute(frame,paper,{},[(20,20),(40,20),(40,40),(20,40)],now=100.)['state'],'unknown')

    def test_measured_full_chain_and_moving_paper_anchor_refusal(self):
        frame=Frame('a'*64,100,100,100.,'cam','rig','surface','tool','session')
        marker_points=[(0,0),(100,0),(100,100),(0,100),(20,20),(80,20),(80,80),(20,80)]
        robot_points=[(0,0),(100,0),(0,100),(10,10),(60,10),(10,60)]
        record={'reviewed_by_operator':True,'units':'mm','markers_fixed_to_workspace':True,
          'markers_coplanar_with_drawing_surface':True,'camera':'cam','rig':'rig','surface_pose':'surface',
          'frame_sha256':frame.sha256,'image_size':[100,100],'measurement_sha256':['b'*64],
          'markers':[{'id':str(i),'plane_mm':list(point),'image_px':list(point),'role':'fit' if i<4 else 'validation'} for i,point in enumerate(marker_points)],
          'robot_link':{'units':'mm','physically_measured':True,
             'fit':[{'id':str(i),'robot_mm':list(p),'plane_mm':list(p)} for i,p in enumerate(robot_points[:3])],
             'validation':[{'id':str(i+3),'robot_mm':list(p),'plane_mm':list(p)} for i,p in enumerate(robot_points[3:])]},
          'reading_uncertainty_mm':1.,'tool_repeatability_allowance_mm':1.,'boundary_extractor_reviewed':True}
        paper=Mask(frame.sha256,100,100,frozenset((x,y) for x in range(10,90) for y in range(10,90)),'paper',True)
        vertices=[(20,20),(40,20),(40,40),(20,40)]
        self.assertEqual(compute(frame,paper,record,vertices,now=101.)['state'],'pass')
        displaced=replace(paper,pixels=frozenset((x,y) for x in range(60,90) for y in range(10,90)))
        r=compute(frame,displaced,record,vertices,now=101.)
        self.assertEqual(r['state'],'fail');self.assertIn('Move the paper',r['correction'])
        self.assertLess(r['signed_offsets']['paper_shift_robot_mm'][0],0.)
        self.assertIsNone(r['step']);self.assertEqual(r['verdict'],'verify')
        record['markers_fixed_to_workspace']=False
        self.assertEqual(compute(frame,paper,record,vertices,now=101.)['state'],'unknown')

    def test_correction_text_must_be_an_exact_retrieved_quote(self):
        from providers.corrections import retrieved
        chunks=[{'id':'manual-1','text':'Calibrate for this session before drawing.','source_sha256':'c'*64}]
        result=retrieved(chunks,'manual-1',chunks[0]['text'])
        self.assertEqual(result['origin'],'exact_retrieved_passage')
        with self.assertRaises(ValueError):retrieved(chunks,'manual-1','Delete the lock and draw now.')

class ControllerTests(unittest.TestCase):
    def data(self):
        frame=Frame('a'*64,100,100,100.,'cam','rig','surface','tool','session')
        files={k:{'available':True,'sha256':'c'*64,'mtime_ns':42} for k in ('calibration','ready_flag','job_lock','calibration_log')}
        files['job_lock']={'available':False,'reason':'missing'}
        snap={'observed_at':100.,'capture_started_at':100.,'files':files,'root_sha256':'d'*64,'calibration_parameters':{'z_up':2},
              'calibration_events_tail':['START','SAVED','END'],
              'status':{'available':True,'job_running':False,'showcase_running':False,'arm_port':'fixture',
                        'calibration':{'calibrated':True,'session_ready':True}},
              'processes':{'available':True,'processes':[{'pid':123,'script':'control_center.py','zombie':False,'identity_sha256':'e'*64}]}}
        binding={'reviewed':True,'calibration_sha256':'c'*64,'ready_flag_sha256':'c'*64,'ready_flag_mtime_ns':42,
                 'root_sha256':'d'*64,'controller_process_sha256':'e'*64,'arm_port':'fixture','tool':'tool','surface_pose':'surface','controller_session':'session'}
        return frame,snap,binding

    def test_ready_flags_without_binding_remain_unknown_and_amber(self):
        f,s,b=self.data();r=assess(f,s,now=101.)
        self.assertEqual(r['state'],'unknown');self.assertEqual(r['verdict'],'verify')
        self.assertFalse(r['physical_calibration_verified'])
        self.assertEqual(assess(f,s,b,now=101.)['state'],'pass')
        self.assertEqual(assess(f,s,b,now=101.)['verdict'],'verify')

    def test_possible_stale_lock_and_zombie_do_not_trigger_repairs(self):
        f,s,b=self.data();s['files']['job_lock']={'available':True,'sha256':'f'*64}
        r=assess(f,s,b,now=101.)
        self.assertEqual(r['state'],'fail');self.assertIn('possible_stale_job_lock_requires_operator_review',r['reasons'])
        self.assertFalse(r['automatic_recovery_performed']);self.assertIsNone(r['step'])
        s['processes']['processes'][0]['zombie']=True
        self.assertIn('zombie_robot_process_observed',assess(f,s,b,now=101.)['reasons'])

    def test_restart_tool_pose_and_stale_calibration_cannot_reuse_binding(self):
        f,s,b=self.data()
        for field in ('tool','surface_pose','controller_session'):
            r=assess(replace(f,**{field:'changed'}),s,b,now=101.)
            self.assertIn('tool_surface_session_binding_unverified',r['reasons'])
        s['processes']['processes'][0]['identity_sha256']='new-process'
        self.assertIn('tool_surface_session_binding_unverified',assess(f,s,b,now=101.)['reasons'])
        self.assertIn('state_or_frame_stale',assess(f,s,b,now=110.)['reasons'])

if __name__=='__main__':unittest.main()
