"""Provider input and physical-veto tests; synthetic fixtures, not a research round."""
import base64
import io
import unittest
import numpy as np
from PIL import Image
from providers.clearance import containment_clearance,measured_registration_error_mm
from providers.payloads import validate,sha
from readiness.checks import Mask

class ProviderTests(unittest.TestCase):
    def setUp(self):
        image=io.BytesIO();Image.new('RGB',(32,24)).save(image,format='JPEG');self.image=image.getvalue()
        self.frame=sha(self.image)
        self.payload={'request_id':'test','question':'Can I draw here?','context':'Approved setup text.',
            'image_jpeg_base64':base64.b64encode(self.image).decode(),'frame_sha256':self.frame,'window_id':'window'}
        self.mask=Mask(self.frame,100,100,frozenset((x,y) for x in range(10,90) for y in range(10,90)),'paper',True)
        self.vertices=[(35,35),(55,35),(55,55),(35,55)]
        self.kw=dict(frame_sha256=self.frame,registration_error_mm=3.,reading_uncertainty_mm=2.,robot_allowance_mm=5.,geometry_reviewed=True)

    def test_prefill_payload_requires_exact_frame_and_context(self):
        self.assertEqual(validate(self.payload),self.image)
        for change in ({'frame_sha256':'0'*64},{'context':''},{'score':.99},{'question':'x'*1001}):
            with self.subTest(change=list(change)),self.assertRaises(ValueError):validate({**self.payload,**change})

    def test_well_placed_paper_has_positive_mm_clearance(self):
        result=containment_clearance(self.mask,self.vertices,np.eye(3),**self.kw)
        self.assertEqual(result['state'],'pass')
        self.assertGreater(result['clearance_mm'],result['required_clearance_mm'])
        self.assertEqual(result['registration_error_mm'],3.)
        self.assertEqual(result['reading_uncertainty_mm'],2.)
        self.assertIsNone(result['step'])

    def test_displaced_paper_fails_without_any_step(self):
        displaced=Mask(self.frame,100,100,frozenset((x,y) for x in range(60,90) for y in range(10,90)),'paper',True)
        result=containment_clearance(displaced,self.vertices,np.eye(3),**self.kw)
        self.assertEqual(result['state'],'fail')
        self.assertEqual(result['reason'],'drawing_footprint_outside_paper_boundary')
        self.assertIsNone(result['step'])

    def test_mask_hole_cannot_pass_by_testing_only_corners(self):
        hole=Mask(self.frame,100,100,self.mask.pixels-{(45,45)},'paper',True)
        result=containment_clearance(hole,self.vertices,np.eye(3),**self.kw)
        self.assertEqual(result['state'],'fail')

    def test_missing_uncertainty_wrong_frame_and_marginal_clearance_are_unknown(self):
        for change in ({'reading_uncertainty_mm':None},{'registration_error_mm':float('nan')},
                       {'frame_sha256':'x'},{'geometry_reviewed':False},{'robot_allowance_mm':100.}):
            result=containment_clearance(self.mask,self.vertices,np.eye(3),**{**self.kw,**change})
            self.assertEqual(result['state'],'unknown')
            self.assertIsNone(result['step'])

    def test_mm_registration_error_uses_inverse_mapping(self):
        world=np.array([[0,0],[100,0],[100,100],[0,100]],float)
        pixels=world*2+np.array([2,0])
        h=np.diag([2.,2.,1.])
        self.assertAlmostEqual(measured_registration_error_mm(h,world,pixels),1.)

if __name__=='__main__':unittest.main()
