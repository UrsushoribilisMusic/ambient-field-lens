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

    def test_gate_prefixes(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        live_backend.client.retrieve = lambda q, f: EVIDENCE
        live_backend.segment_paper = lambda *a, **k: {'masks': []}
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 200)
        self.assertTrue(response.detail.startswith('WORLD CHECK FAILED:'))

    def test_no_chunks_prefix(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        live_backend.client.retrieve = lambda q, f: {'chunks': []}
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 200)
        self.assertEqual(response.verdict, 'verify')
        self.assertTrue(response.detail.startswith('NOT COVERED:'))

    def test_distance_gate_off_by_default(self):
        self.assertIsNone(live_backend.COVERAGE_DISTANCE_MAX)

    def test_distance_gate_fires_above_cutoff(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        far = [dict(EVIDENCE['chunks'][0], distance=0.9, id='far-chunk')]
        live_backend.client.retrieve = lambda q, f: dict(EVIDENCE, chunks=far)
        saved = live_backend.COVERAGE_DISTANCE_MAX
        live_backend.COVERAGE_DISTANCE_MAX = 0.5
        try:
            status, response = self.run_assist(request_with_image())
        finally:
            live_backend.COVERAGE_DISTANCE_MAX = saved
        self.assertEqual(status, 200)
        self.assertTrue(response.detail.startswith('NOT COVERED:'))
        self.assertIn('close enough', response.detail)

    def test_distance_gate_passes_below_cutoff(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        near = [dict(EVIDENCE['chunks'][0], distance=0.1, id='near-chunk')]
        live_backend.client.retrieve = lambda q, f: dict(EVIDENCE, chunks=near)
        live_backend.segment_paper = lambda *a, **k: {'masks': []}
        saved = live_backend.COVERAGE_DISTANCE_MAX
        live_backend.COVERAGE_DISTANCE_MAX = 0.5
        try:
            status, response = self.run_assist(request_with_image())
        finally:
            live_backend.COVERAGE_DISTANCE_MAX = saved
        self.assertEqual(status, 200)
        self.assertFalse(response.detail.startswith('NOT COVERED:'))

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

    def fake_store(self, stores):
        import sys
        import threading
        class FakeDict:
            def __init__(self):
                self.lock = threading.Lock()
            def get(self, key):
                return stores.get(key)
            def put(self, key, value):
                stores[key] = value
            def contains(self, key):
                return key in stores
            def pop(self, key):
                with self.lock:
                    if key not in stores:
                        raise KeyError(key)
                    return stores.pop(key)
        box = {}
        class FakeModal:
            class Dict:
                @staticmethod
                def from_name(name, create_if_missing=False):
                    assert create_if_missing
                    if 'dict' not in box:
                        box['dict'] = FakeDict()
                    return box['dict']
        saved = sys.modules.get('modal')
        sys.modules['modal'] = FakeModal()
        return saved

    def restore_modal(self, saved):
        import sys
        if saved is None:
            del sys.modules['modal']
        else:
            sys.modules['modal'] = saved

    def test_token_budget_survives_last_slot_race(self):
        import threading
        stores = {}
        saved = self.fake_store(stores)
        try:
            record = {'id': 'w9', 'expires_at': 9e9, 'max_calls': 1}
            live_backend.arm_tokens(record)
            stores['active'] = dict(record, calls_used=0)
            barrier = threading.Barrier(2)
            results = []
            def attempt():
                barrier.wait()
                try:
                    live_backend.claim_call(dict(record))
                    results.append('ok')
                except live_backend.WindowUnavailable:
                    results.append('spent')
            threads = [threading.Thread(target=attempt) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        finally:
            self.restore_modal(saved)
        self.assertEqual(sorted(results), ['ok', 'spent'])

    def test_tokens_never_refill(self):
        stores = {}
        saved = self.fake_store(stores)
        try:
            record = {'id': 'w9', 'expires_at': 9e9, 'max_calls': 1}
            live_backend.arm_tokens(record)
            stores['active'] = dict(record, calls_used=0)
            self.assertEqual(live_backend.claim_call(dict(record)), 'w9')
            live_backend.arm_tokens(record)
            with self.assertRaises(live_backend.WindowUnavailable):
                live_backend.claim_call(dict(record))
        finally:
            self.restore_modal(saved)

    def test_timeout_holds_slot_and_starts_no_new_stage(self):
        import asyncio
        import threading
        entries = []
        release = threading.Event()
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        def slow_retrieve(q, f):
            entries.append('retrieve')
            release.wait(timeout=5)
            return dict(EVIDENCE)
        live_backend.client.retrieve = slow_retrieve
        live_backend.segment_paper = lambda *a, **k: entries.append('segment') or MASKS
        service = LiveAssistService(limits=live_backend.LiveLimits(
            timeout_seconds=0.05, concurrency=1, queue_seconds=0.05))
        async def run():
            first = asyncio.ensure_future(service.assist(request_with_image()))
            await asyncio.sleep(0.2)
            # Worker is past timeout, still inside retrieve: slot held, no
            # new paid stage may start, second request cannot overlap.
            second = await service.assist(request_with_image())
            release.set()
            return await first, second
        (status1, _), (status2, _) = asyncio.run(run())
        self.assertEqual(status1, 504)
        self.assertIn(status2, (429, 503, 504))
        self.assertEqual(entries, ['retrieve'])

    def test_default_timeout_frees_slot_before_phone_quits(self):
        self.assertLessEqual(live_backend.LiveLimits().timeout_seconds, 150.0)

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
