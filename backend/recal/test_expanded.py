import copy,unittest
import numpy as np
from test_paired import records
from expanded_analysis import expand,validate,report
from paired_analysis import fit_score


def base():
    r=records();names=['calibration','port','pressure','approval','locking','narration']
    for row in r:
        row['group']=names[int(row['group'])];row['frame_sha256']='frame'+row['pair_id'];row['frame_asset']='saved.jpg'
        row['text']='Manual excerpt: '+str(row['supported'])+'\nQuestion: '+row['question']
    return {'records':r}


class ExpansionTests(unittest.TestCase):
    def test_counts_and_human_reviewed_inheritance(self):
        b=base();r=expand(b);validate(r,b['records']);self.assertEqual(len(r),84)
        self.assertEqual(sum(x['partition']=='novel_wording' for x in r),48)
    def test_no_new_fact_frame_label_or_candidate_can_enter(self):
        b=base();r=expand(b)
        for field in ['candidate','text','frame_sha256','supported','fold','question']:
            bad=copy.deepcopy(r);bad[-1][field]='changed'
            with self.subTest(field=field),self.assertRaises(ValueError):validate(bad,b['records'])
    def test_legacy_controls_cannot_be_rewritten(self):
        b=base();r=expand(b);r[0]['candidate']='other'
        with self.assertRaises(ValueError):validate(r,b['records'])
    def test_new_test_features_cannot_fit_the_direction(self):
        r=expand(base());x=np.random.default_rng(7).normal(size=(84,5))
        _,before=fit_score(x,r);x[36:]*=-300
        _,after=fit_score(x,r);np.testing.assert_array_equal(before,after)
    def test_primary_cohort_is_new_wording_not_old_test(self):
        r=expand(base());s=np.array([float(x['supported']) for x in r]);s[24:36]*=-1
        out=report(s,r,27)
        self.assertEqual(out['novel_wording_test']['auc'],1.)
        self.assertEqual(out['novel_wording_test']['pairs'],24)
        self.assertEqual(out['legacy_test_control']['pairs'],6)
        self.assertEqual(out['legacy_test_control']['auc'],0.)
        self.assertEqual(out['novel_wording_test']['topic_clusters'],2)
        self.assertFalse(out['enabled']);self.assertEqual(out['fixed_layer'],27)

if __name__=='__main__':unittest.main()
