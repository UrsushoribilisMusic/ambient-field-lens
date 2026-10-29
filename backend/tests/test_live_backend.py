"""Live amber-only composition regressions; providers faked, no GPU/network."""
import asyncio
import base64
from io import BytesIO
import unittest

from PIL import Image

from contracts import AssistRequest
import live_backend
from live_backend import LiveAssistService, WindowUnavailable, evidence_detail


def image_b64(size=(64, 64)):
    out = BytesIO()
    Image.new('RGB', size, color='white').save(out, format='JPEG')
    return base64.b64encode(out.getvalue()).decode()


def request_with_image():
    return AssistRequest(query='Can I draw this here?', image_jpeg_base64=image_b64())


EVIDENCE = {'chunks': [{'id': 'ross-manual#c12'}, {'id': 'ross-manual#c13'}],
            'context': 'ctx', 'context_sha256': 'x', 'frame_sha256': 'y'}
MASKS = {'masks': [{'id': 'mask-1'}, {'id': 'mask-2'}]}
SCORE = {'score': 0.62, 'frame_sha256': 'y'}
WINDOW = {'id': 'w1', 'expires_at': 9e9, 'calls_used': 0, 'max_calls': 4}


class LiveBackendTests(unittest.TestCase):
    def setUp(self):
        self.saved = {}
        for name in ('read_window', 'claim_call', 'segment_paper'):
            self.saved[name] = getattr(live_backend, name)
        self.saved['retrieve'] = live_backend.client.retrieve
        self.saved['grounding'] = live_backend.client.grounding

    def tearDown(self):
        for name in ('read_window', 'claim_call', 'segment_paper'):
            setattr(live_backend, name, self.saved[name])
        live_backend.client.retrieve = self.saved['retrieve']
        live_backend.client.grounding = self.saved['grounding']

    def run_assist(self, request):
        return asyncio.run(LiveAssistService().assist(request))

    def test_happy_path_stays_amber_with_evidence(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        live_backend.client.retrieve = lambda q, f: EVIDENCE
        live_backend.segment_paper = lambda *a, **k: MASKS
        live_backend.client.grounding = lambda **k: SCORE
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 200)
        self.assertEqual(response.verdict, 'verify')
        self.assertIsNone(response.step)
        self.assertEqual(response.score, 0.0)
        self.assertIn('ross-manual#c12', response.detail)
        self.assertIn('0.620', response.detail)
        self.assertLessEqual(len(response.detail), 300)

    def test_no_frame_is_amber_without_window(self):
        def fail():
            raise AssertionError('window must not be read without a frame')
        live_backend.read_window = fail
        request = AssistRequest(query='Can I draw this here?')
        status, response = self.run_assist(request)
        self.assertEqual(status, 200)
        self.assertEqual(response.verdict, 'verify')

    def test_missing_window_is_503_amber(self):
        def missing():
            raise WindowUnavailable('No live demo window is open.')
        live_backend.read_window = missing
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 503)
        self.assertEqual(response.verdict, 'verify')
        self.assertIsNone(response.step)

    def test_no_masks_is_amber_guidance(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        live_backend.client.retrieve = lambda q, f: EVIDENCE
        live_backend.segment_paper = lambda *a, **k: {'masks': []}
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 200)
        self.assertEqual(response.verdict, 'verify')
        self.assertIn('No paper candidate', response.detail)

    def test_provider_failure_is_502_amber_without_text(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        def boom(q, f):
            raise RuntimeError('secret-internal-trace-123')
        live_backend.client.retrieve = boom
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 502)
        self.assertEqual(response.verdict, 'verify')
        self.assertNotIn('secret-internal-trace-123', response.detail)

    def test_claim_call_uses_put_protocol(self):
        import sys
        stores = {}
        class FakeDict:
            def get(self, key):
                return stores.get(key)
            def put(self, key, value):
                stores[key] = value
        class FakeModal:
            class Dict:
                @staticmethod
                def from_name(name, create_if_missing=False):
                    assert create_if_missing
                    return FakeDict()
        saved = sys.modules.get('modal')
        sys.modules['modal'] = FakeModal()
        try:
            window_id = live_backend.claim_call(dict(WINDOW))
        finally:
            if saved is None:
                del sys.modules['modal']
            else:
                sys.modules['modal'] = saved
        self.assertEqual(window_id, 'w1')
        self.assertEqual(stores['active']['calls_used'], 1)

    def test_evidence_detail_accepts_live_tuples(self):
        from live_backend import evidence_detail
        detail = evidence_detail(masks=[('mask-abc', object()), ('m2', object())],
                                 chunk_ids=['c1'], score=0.5)
        self.assertIn('mask-abc', detail)
        self.assertLessEqual(len(detail), 300)

    def test_evidence_detail_bounded(self):
        detail = evidence_detail(masks=[{'id': 'm' * 50}] * 10,
                                 chunk_ids=['c' * 60] * 5, score=0.12345)
        self.assertLessEqual(len(detail), 300)
        self.assertIn('unverified', detail)


if __name__ == '__main__':
    unittest.main()
