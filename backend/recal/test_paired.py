import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from paired_analysis import fit_score, choose_layer, summarize, validate_records
from budget import reserve_window


def records():
    rs=[]
    for g in range(6):
        for i in range(3):
            for support in (True,False):
                rs.append(dict(id=f'{g}-{i}-{support}',pair_id=f'{g}-{i}',group=str(g),
                    fold=('fit','validation','test')[g//2],supported=support,
                    question=f'q{g}-{i}',candidate='step',text=str(support)))
    return rs


class PairedTests(unittest.TestCase):
    def test_pairs_cannot_cross_folds_or_lose_members(self):
        r=records();validate_records(r)
        for corrupt in ['fold','question']:
            bad=copy.deepcopy(r);bad[0][corrupt]='other'
            with self.assertRaises(ValueError):validate_records(bad)
        with self.assertRaises(ValueError):validate_records(r[:-1])
    def test_camera_pair_must_use_the_same_frame(self):
        r=records()
        for row in r:row['frame_sha256']='original'
        validate_records(r)
        r[0]['frame_sha256']='changed'
        with self.assertRaisesRegex(ValueError,'frame_sha256'):validate_records(r)
    def test_validation_selects_layer_not_heldout_test(self):
        r=records();s=np.zeros((36,3))
        for i,row in enumerate(r):s[i,1]=int(row['supported'])
        a=choose_layer(s,r);s[24:,2]=np.array([int(x['supported']) for x in r[24:]])*100
        self.assertEqual(choose_layer(s,r),a)
    def test_no_test_features_fit_direction(self):
        r=records();x=np.random.default_rng(1).normal(size=(36,4));x[:,0]+=[int(a['supported']) for a in r]
        _,d=fit_score(x,r);x[12:]*=-1000
        _,changed=fit_score(x,r);np.testing.assert_array_equal(d,changed)
    def test_ties_are_half_and_result_never_enables_gate(self):
        result=summarize(np.zeros((36,2)),records())
        self.assertEqual(result['pair_accuracy'],.5);self.assertEqual(result['paired_sign_test_two_sided_p'],1)
        self.assertFalse(result['enabled']);self.assertEqual(result['selected_layer'],0)
    def test_sign_test_reports_topic_independence_not_six_independent_paraphrases(self):
        r=records();scores=np.array([[int(x['supported'])] for x in r],dtype=float)
        result=summarize(scores,r)
        self.assertEqual(result['paired_sign_test_two_sided_p'],.03125)
        self.assertEqual(result['topic_sign_test_two_sided_p'],.5)
        self.assertIn('correlated',result['pair_sign_test_caveat'])
    def test_old_reservations_migrated_not_erased(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'ledger.json';p.write_text(json.dumps({'ceiling_usd':20.,'cpu_and_build_reserve_usd':2.,'windows':[{'id':'old','reserved_usd':4.}]}))
            new=reserve_window(p);j=json.loads(p.read_text())
            self.assertEqual(j['ceiling_usd'],100.);self.assertEqual(j['windows'][0]['id'],'old')
            self.assertEqual(len(j['windows']),2)
    def test_jvp_matches_dense_autodiff_and_finite_difference(self):
        try:import torch
        except ImportError:self.skipTest('Run JVP test also in torch-capable CPU environment')
        from jacobian_lens import project_jacobian
        torch.manual_seed(8)
        norm=torch.nn.RMSNorm(5,eps=1e-5).double();head=torch.randn(9,5,dtype=torch.double)
        a=torch.randn(5,dtype=torch.double);x=torch.randn(3,5,dtype=torch.double)
        actual=project_jacobian(norm,head,a,x)
        dense=torch.autograd.functional.jacobian(lambda z:head@norm(z),a)
        torch.testing.assert_close(actual,(x-a)@dense.T,atol=1e-9,rtol=1e-8)
        eps=1e-5;direction=x[0]-a
        fd=(head@norm(a+eps*direction)-head@norm(a-eps*direction))/(2*eps)
        torch.testing.assert_close(actual[0],fd,atol=1e-7,rtol=1e-6)
        self.assertEqual(actual.shape,(3,9))
        self.assertTrue((actual[:,8].abs()>0).any()) # includes last vocab coordinate

if __name__=='__main__':unittest.main()
