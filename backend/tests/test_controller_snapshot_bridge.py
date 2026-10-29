"""CPU-only local calls to Modal function bodies; no deployments or requests."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

@unittest.skipUnless(importlib.util.find_spec('modal'),'optional Modal SDK required for local function-body checks')
class BridgeTests(unittest.TestCase):
    def setUp(self):
        import providers.modal_runtime as runtime
        self.runtime=runtime;self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=patch.object(runtime,'BASE',Path(self.tmp.name));self.base.start();self.addCleanup(self.base.stop)
        self.volume=patch.object(runtime,'artifacts',Mock());self.volume.start();self.addCleanup(self.volume.stop)
        self.clock=patch.object(runtime.time,'time',return_value=101.);self.clock.start();self.addCleanup(self.clock.stop)
        self.request={'robot_id':'fixture-robot','snapshot':{'schema':'ross-controller-evidence-v1','observed_at':100.,
            'physical_calibration_verified':False,'controller_session_verified':False}}

    def test_store_read_never_refreshes_observation_or_certifies_physical_state(self):
        stored=self.runtime.put_controller_snapshot.local(self.request)
        self.assertTrue(stored['accepted_for_storage_only']);self.assertFalse(stored['physical_calibration_verified'])
        value=self.runtime.get_controller_snapshot.local({'robot_id':'fixture-robot'})
        self.assertEqual(value['snapshot']['observed_at'],100.);self.assertTrue(value['fresh'])
        with patch.object(self.runtime.time,'time',return_value=110.):
            value=self.runtime.get_controller_snapshot.local({'robot_id':'fixture-robot'})
            self.assertFalse(value['fresh']);self.assertEqual(value['snapshot']['observed_at'],100.)

    def test_stale_unsafe_ids_and_forged_readiness_flags_rejected(self):
        with self.assertRaises(ValueError):self.runtime.put_controller_snapshot.local({**self.request,'robot_id':'../escape'})
        for changes in ({'observed_at':0.},{'physical_calibration_verified':True}):
            with self.assertRaises(ValueError):self.runtime.put_controller_snapshot.local(
                {**self.request,'snapshot':{**self.request['snapshot'],**changes}})
        self.runtime.put_controller_snapshot.local(self.request)
        path=Path(self.tmp.name)/'controller-fixture-robot.json';v=json.loads(path.read_text())
        v['snapshot']['observed_at']=101.;path.write_text(json.dumps(v))
        with self.assertRaises(ValueError):self.runtime.get_controller_snapshot.local({'robot_id':'fixture-robot'})

if __name__=='__main__':unittest.main()
