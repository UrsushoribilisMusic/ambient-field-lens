import copy,json,unittest
from pathlib import Path
from visual_review import digest_manifest,validate_draft,validate_human_review


class VisualReviewTests(unittest.TestCase):
    def setUp(self):
        self.m=json.loads((Path(__file__).resolve().parents[2]/'docs/verification/visual-pair-manifest-2026-10-28.json').read_text())
    def review_fixture(self):
        # Synthetic unit-test input, never written to a real human review artifact.
        return {'manifest_digest':digest_manifest(self.m),'reviewer_name':'Miguel (unit-test fixture)',
          'independently_reviewed':True,'footprint_scope_approved':True,
          'pairs':[{'id':p['id'],'manual_only_answerable':False,'image_evidence_sufficient':True,
            'member_labels':{m['id']:m['author_proposed_label'] for m in p['members']}} for p in self.m['pairs']]}
    def test_draft_is_unreviewed_and_has_no_scoring_authority(self):
        self.assertTrue(validate_draft(self.m));self.assertIsNone(self.m['human_reviewer'])
        self.assertFalse(self.m['scoring_enabled']);self.assertFalse(self.m['gpu_authorized'])
    def test_review_cannot_be_assumed_or_partial(self):
        r=self.review_fixture();r['independently_reviewed']=False
        with self.assertRaises(ValueError):validate_human_review(self.m,r)
        r=self.review_fixture();r['pairs'].pop()
        with self.assertRaises(ValueError):validate_human_review(self.m,r)
    def test_manual_only_pair_is_rejected_not_scored(self):
        r=self.review_fixture();r['pairs'][0]['manual_only_answerable']=True
        with self.assertRaisesRegex(ValueError,'manual-only'):validate_human_review(self.m,r)
    def test_unknown_or_insufficient_evidence_blocks_entire_set(self):
        r=self.review_fixture();r['pairs'][2]['member_labels']['VG03-A']=None
        with self.assertRaises(ValueError):validate_human_review(self.m,r)
        r=self.review_fixture();r['pairs'][2]['image_evidence_sufficient']=False
        with self.assertRaises(ValueError):validate_human_review(self.m,r)
    def test_digest_and_same_family_folds_cannot_change(self):
        r=self.review_fixture();self.m['pairs'][0]['question']+=' changed'
        with self.assertRaisesRegex(ValueError,'bound'):validate_human_review(self.m,r)
        self.m['pairs'][1]['fold']='validation'
        with self.assertRaisesRegex(ValueError,'leakage'):validate_draft(self.m)
    def test_reviewed_labels_still_do_not_launch_gpu_or_green(self):
        result=validate_human_review(self.m,self.review_fixture())
        self.assertFalse(result['gpu_launched']);self.assertFalse(result['live_green_enabled'])

if __name__=='__main__':unittest.main()
