"""Model-free HTTP and failure-boundary regressions; no GPU or external API."""
import asyncio
import base64
from io import BytesIO
import unittest

import httpx
from PIL import Image

from app import RequestBoundary, create_app
from circuit import CircuitBreaker
from contracts import AssistRequest, AssistResponse, MAX_BODY_BYTES, deny
from service import AssistService, Limits, LowGrounding


def image_b64(format='JPEG', size=(16, 16)):
    out = BytesIO()
    Image.new('RGB', size, color='white').save(out, format=format)
    return base64.b64encode(out.getvalue()).decode()


JPEG = image_b64()


class EndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = create_app()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose()

    def amber(self, response, status):
        self.assertEqual(response.status_code, status)
        body = response.json()
        self.assertEqual(body['verdict'], 'verify')
        self.assertIsNone(body['step'])
        self.assertEqual(body['score'], 0)
        self.assertEqual(response.headers['cache-control'], 'no-store')

    async def test_health_and_valid_frame_default_deny(self):
        self.assertEqual((await self.client.get('/healthz')).json()['gate'], 'default-deny')
        self.amber(await self.client.post('/assist', json={'query': 'Identify this component', 'image_jpeg_base64': JPEG}), 200)

    async def test_missing_frame_never_calls_provider(self):
        async def should_not_run(req):
            self.fail('provider ran without a frame')
        self.app.state.assist_service = AssistService(should_not_run)
        self.amber(await self.client.post('/assist', json={'query': 'Identify this component'}), 200)

    async def test_query_bounds_and_strict_types(self):
        for value in ['', '   ', 'x'*2001, 42, None, 'bad\x00query']:
            with self.subTest(value_type=type(value).__name__):
                self.amber(await self.client.post('/assist', json={'query': value}), 422)

    async def test_client_cannot_supply_verdict_score_or_step(self):
        for extra in [{'verdict': 'verified'}, {'score': 1}, {'step': 'Start motor'}]:
            self.amber(await self.client.post('/assist', json={'query': 'Identify', **extra}), 422)

    async def test_malformed_base64_png_and_truncated_jpeg_rejected(self):
        for frame in ['not base64!', image_b64('PNG'), base64.b64encode(b'not an image').decode(),
                      base64.b64encode(base64.b64decode(JPEG)[:-30]).decode()]:
            self.amber(await self.client.post('/assist', json={'query': 'Identify', 'image_jpeg_base64': frame}), 422)

    async def test_pixel_budget_checked_before_full_decode(self):
        self.amber(await self.client.post('/assist', json={'query': 'Identify', 'image_jpeg_base64': image_b64(size=(2049, 2048))}), 422)

    async def test_wrong_content_type_and_compressed_payload_rejected(self):
        self.amber(await self.client.post('/assist', content='{}', headers={'Content-Type': 'text/plain'}), 415)
        self.amber(await self.client.post('/assist', json={'query': 'Identify'}, headers={'Content-Encoding': 'gzip'}), 415)

    async def test_malformed_json_does_not_echo_payload(self):
        response = await self.client.post('/assist', content='{"private_query": "CONFIDENTIAL', headers={'Content-Type': 'application/json'})
        self.amber(response, 422)
        self.assertNotIn('CONFIDENTIAL', response.text)

    async def test_body_length_and_actual_chunked_bytes_bounded(self):
        self.amber(await self.client.post('/assist', content=b'{}', headers={'Content-Type': 'application/json', 'Content-Length': str(MAX_BODY_BYTES+1)}), 413)
        async def chunks():
            for _ in range(4):
                yield b'x' * (1024*1024)
        self.amber(await self.client.post('/assist', content=chunks(), headers={'Content-Type': 'application/json'}), 413)

    async def test_forged_green_output_and_nan_are_rejected(self):
        results = [dict(verdict='verified', step='Start motor', score=1, detail=''),
                   AssistResponse.model_construct(verdict='verified', step='Start motor', score=1),
                   dict(verdict='verify', step='Start motor', score=0, detail=''),
                   dict(verdict='verify', step=None, score=float('nan'), detail='')]
        for result in results:
            async def backend(req):
                return result
            self.app.state.assist_service = AssistService(backend)
            self.amber(await self.client.post('/assist', json={'query': 'Identify', 'image_jpeg_base64': JPEG}), 503)

    async def test_provider_exception_is_redacted(self):
        async def backend(req):
            raise RuntimeError('SECRET upstream credential')
        self.app.state.assist_service = AssistService(backend)
        response = await self.client.post('/assist', json={'query': 'Identify', 'image_jpeg_base64': JPEG})
        self.amber(response, 503)
        self.assertNotIn('SECRET', response.text)

    async def test_provider_cannot_hide_an_instruction_in_amber_detail(self):
        async def backend(req):
            return deny('UNSAFE: Start the motor immediately.')
        self.app.state.assist_service = AssistService(backend)
        for _ in range(4):
            response = await self.client.post('/assist', json={'query': 'Identify', 'image_jpeg_base64': JPEG})
            self.amber(response, 200)
            self.assertNotIn('UNSAFE', response.text)

    async def test_provider_timeout_is_amber(self):
        async def backend(req):
            await asyncio.Event().wait()
        self.app.state.assist_service = AssistService(backend, Limits(timeout_seconds=.01))
        self.amber(await self.client.post('/assist', json={'query': 'Identify', 'image_jpeg_base64': JPEG}), 504)

    async def test_low_grounding_opens_breaker_and_skips_provider(self):
        calls = 0
        async def backend(req):
            nonlocal calls
            calls += 1
            raise LowGrounding()
        self.app.state.assist_service = AssistService(backend)
        for _ in range(3):
            self.amber(await self.client.post('/assist', json={'query': 'Identify', 'image_jpeg_base64': JPEG}), 200)
        self.amber(await self.client.post('/assist', json={'query': 'Identify', 'image_jpeg_base64': JPEG}), 503)
        self.assertEqual(calls, 3)

    async def test_slow_upload_deadline(self):
        app = create_app()
        # Exercise the same receive boundary with an injected short deadline.
        boundary = RequestBoundary(app, read_timeout=.01)
        async def receive():
            await asyncio.Event().wait()
        messages = []
        async def send(message):
            messages.append(message)
        await boundary({'type': 'http', 'path': '/assist', 'method': 'POST',
                        'headers': [(b'content-type', b'application/json')]}, receive, send)
        self.assertEqual(messages[0]['status'], 408)


class ExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrency_rejection_and_release(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def backend(req):
            entered.set()
            await release.wait()
            return deny('Verify in manual.')
        service = AssistService(backend, Limits(concurrency=1, queue_seconds=.001))
        req = AssistRequest(query='Identify', image_jpeg_base64=JPEG)
        first = asyncio.create_task(service.assist(req))
        await entered.wait()
        self.assertEqual((await service.assist(req))[0], 429)
        release.set()
        self.assertEqual((await first)[0], 200)
        self.assertEqual((await service.assist(req))[0], 200)

    async def test_cancelled_provider_releases_slot(self):
        entered = asyncio.Event()
        async def backend(req):
            entered.set()
            await asyncio.Event().wait()
        service = AssistService(backend, Limits(concurrency=1))
        req = AssistRequest(query='Identify', image_jpeg_base64=JPEG)
        first = asyncio.create_task(service.assist(req))
        await entered.wait()
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        async def recovered(req):
            return deny('Verify in manual.')
        service.backend = recovered
        self.assertEqual((await service.assist(req))[0], 200)


class BreakerTests(unittest.TestCase):
    def test_one_probe_and_late_results_cannot_override_cooldown(self):
        now = [0.0]
        breaker = CircuitBreaker(threshold=1, recovery_seconds=30, clock=lambda: now[0])
        first, late = breaker.admit(), breaker.admit()
        breaker.failed(first)
        breaker.succeeded(late)
        self.assertEqual(breaker.state(), 'open')
        self.assertIsNone(breaker.admit())
        now[0] = 31
        probe = breaker.admit()
        breaker.succeeded(late)
        self.assertIsNone(breaker.admit())
        breaker.succeeded(probe)
        self.assertEqual(breaker.state(), 'closed')
        breaker.failed(late)
        self.assertEqual(breaker.state(), 'closed')

    def test_failed_probe_reopens(self):
        now = [0.0]
        breaker = CircuitBreaker(threshold=1, recovery_seconds=30, clock=lambda: now[0])
        breaker.failed(breaker.admit())
        now[0] = 31
        breaker.failed(breaker.admit())
        self.assertEqual(breaker.state(), 'open')


if __name__ == '__main__':
    unittest.main()
