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

    def test_distance_gate_calibrated_from_receipt(self):
        self.assertEqual(live_backend.COVERAGE_DISTANCE_MAX, 0.76)
        self.assertEqual(live_backend.COVERAGE_N, 8)

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
        self.assertIn('No manual passage within the coverage threshold', response.detail)

    def test_world_failed_quotes_covered_passage(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        chunks = [dict(EVIDENCE['chunks'][0], distance=0.3,
                       text='The lock file keeps one job at a time.')]
        live_backend.client.retrieve = lambda q, f: dict(EVIDENCE, chunks=chunks)
        live_backend.segment_paper = lambda *a, **k: {'masks': []}
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 200)
        self.assertTrue(response.detail.startswith('WORLD CHECK FAILED:'))
        self.assertEqual(response.verdict, 'verify')
        self.assertIsNone(response.step)
        self.assertEqual(response.passage, 'The lock file keeps one job at a time.')

    def test_evidence_path_quotes_covered_passage(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        chunks = [dict(EVIDENCE['chunks'][0], distance=0.3, text='abc')]
        live_backend.client.retrieve = lambda q, f: dict(EVIDENCE, chunks=chunks)
        live_backend.segment_paper = lambda *a, **k: MASKS
        live_backend.client.grounding = lambda **k: SCORE
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 200)
        self.assertTrue(response.detail.startswith('Live check (amber):'))
        self.assertEqual(response.passage, 'abc')

    def test_passage_truncation_marked(self):
        long_text = 'x' * 700
        out = live_backend.passage_excerpt([{'text': long_text}])
        self.assertTrue(out.endswith(' […]'))
        self.assertLessEqual(len(out), 610)

    def test_not_covered_carries_no_passage(self):
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        far = [dict(EVIDENCE['chunks'][0], distance=0.9, id='far-chunk')]
        live_backend.client.retrieve = lambda q, f: dict(EVIDENCE, chunks=far)
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 200)
        self.assertTrue(response.detail.startswith('NOT COVERED:'))
        self.assertIsNone(response.passage)

    def test_not_covered_detail_carries_machine_tail(self):
        import re
        live_backend.read_window = lambda: dict(WINDOW)
        live_backend.claim_call = lambda record: 'w1'
        chunk_id = '8135308218c2c50dfd8b0aec8c0a48b25782d42098b2af9d4aa03fb2d71ccbb6'
        far = [dict(EVIDENCE['chunks'][0], distance=0.8199027180671692, id=chunk_id)]
        live_backend.client.retrieve = lambda q, f: dict(EVIDENCE, chunks=far)
        status, response = self.run_assist(request_with_image())
        self.assertEqual(status, 200)
        self.assertLessEqual(len(response.detail), 300)
        self.assertIn('d=0.820>0.760', response.detail)
        self.assertIn('8 covered max 0.741', response.detail)
        tail = re.search(r'top=([0-9a-f]{16,128})\s*$', response.detail)
        self.assertIsNotNone(tail)
        self.assertEqual(tail.group(1), chunk_id)

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
                self.on_pop = None
            def get(self, key):
                return stores.get(key)
            def put(self, key, value):
                stores[key] = value
            def contains(self, key):
                return key in stores
            def keys(self):
                return list(stores.keys())
            def pop(self, key):
                with self.lock:
                    if key not in stores:
                        raise KeyError(key)
                    value = stores.pop(key)
                    if self.on_pop is not None:
                        self.on_pop(key)
                    return value
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
        return saved, box

    def restore_modal(self, saved):
        import sys
        if saved is None:
            del sys.modules['modal']
        else:
            sys.modules['modal'] = saved

    def test_token_budget_survives_last_slot_race(self):
        import threading
        stores = {}
        saved, _box = self.fake_store(stores)
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
        saved, _box = self.fake_store(stores)
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

    def test_close_during_pop_kills_inflight_claim(self):
        stores = {}
        saved, box = self.fake_store(stores)
        try:
            shown = {'id': 'w9', 'expires_at': 9e9, 'max_calls': 1}
            live_backend.arm_tokens(shown)
            stores['active'] = dict(shown, calls_used=0)
            def close_on_pop(key):
                if key == 'w9:call-0':
                    stores['active'] = None
            box['dict'].on_pop = close_on_pop
            with self.assertRaises(live_backend.WindowUnavailable):
                live_backend.claim_call(dict(shown))
            # Dead window stays dead: no stats write resurrected it, and the
            # popped token is sacrificed (fail-closed under-count, no refill).
            self.assertIsNone(stores.get('active'))
            self.assertEqual(live_backend.remaining_calls('w9'), 0)
        finally:
            self.restore_modal(saved)

    def test_replace_during_pop_refuses_and_preserves_new_budget(self):
        stores = {}
        saved, box = self.fake_store(stores)
        try:
            old = {'id': 'w-old', 'expires_at': 9e9, 'max_calls': 1}
            new = {'id': 'w-new', 'expires_at': 9e9, 'max_calls': 1}
            live_backend.arm_tokens(old)
            live_backend.arm_tokens(new)
            stores['active'] = dict(old, calls_used=0)
            def replace_on_pop(key):
                if key == 'w-old:call-0':
                    stores['active'] = dict(new, calls_used=0)
            box['dict'].on_pop = replace_on_pop
            with self.assertRaises(live_backend.WindowUnavailable):
                live_backend.claim_call(dict(old))
            box['dict'].on_pop = None
            # The new window's budget is untouched and still usable.
            self.assertEqual(live_backend.remaining_calls('w-new'), 1)
            self.assertEqual(live_backend.claim_call(dict(new)), 'w-new')
        finally:
            self.restore_modal(saved)

    def test_cancelled_queued_caller_releases_nothing_and_cancel_drains(self):
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
        live_backend.client.grounding = lambda **k: SCORE
        service = LiveAssistService(limits=live_backend.LiveLimits(
            timeout_seconds=30, concurrency=1, queue_seconds=30))
        async def scenario():
            first = asyncio.create_task(service.assist(request_with_image()))
            for _ in range(1000):
                if entries.count('retrieve') == 1:
                    break
                await asyncio.sleep(0.01)
            queued = asyncio.create_task(service.assist(request_with_image()))
            await asyncio.sleep(0.2)
            self.assertTrue(service.slots.locked())
            queued.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await queued
            # The cancelled waiter never held the slot: still locked by first.
            self.assertTrue(service.slots.locked())
            release.set()
            status, body = await first
            self.assertEqual(status, 200)
            # Segment starts only after release; nothing overlapped the worker.
            self.assertEqual(entries.count('segment'), 1)
        asyncio.run(scenario())

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
