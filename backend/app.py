"""Phase 1 HTTP boundary. All decisions and error envelopes default to amber."""
import asyncio
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from contracts import AssistRequest, AssistResponse, MAX_BODY_BYTES, deny
from service import AssistService
import gap_report


def amber_response(status, detail):
    return JSONResponse(status_code=status, content=deny(detail).model_dump(),
                        headers={'Cache-Control': 'no-store'})


class RequestBoundary:
    """Bound actual streamed bytes before FastAPI parses or buffers JSON."""
    def __init__(self, app, max_bytes=MAX_BODY_BYTES, read_timeout=3.0):
        self.app, self.max_bytes, self.read_timeout = app, max_bytes, read_timeout

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'] != '/assist' or scope['method'] != 'POST':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        media = headers.get(b'content-type', b'').split(b';', 1)[0].strip().lower()
        if media != b'application/json' or headers.get(b'content-encoding', b'identity') != b'identity':
            return await amber_response(415, 'Send uncompressed JSON. Verify in the manual.')(scope, receive, send)
        try:
            length = int(headers.get(b'content-length', b'0'))
        except ValueError:
            return await amber_response(400, 'Invalid request framing. Verify in the manual.')(scope, receive, send)
        if length < 0 or length > self.max_bytes:
            return await amber_response(413, 'Request exceeds the size limit. Verify in the manual.')(scope, receive, send)
        body = bytearray()
        deadline = time.monotonic() + self.read_timeout
        try:
            while True:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                message = await asyncio.wait_for(receive(), timeout=remaining)
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b'')
                if len(body) + len(chunk) > self.max_bytes:
                    return await amber_response(413, 'Request exceeds the size limit. Verify in the manual.')(scope, receive, send)
                body.extend(chunk)
                if not message.get('more_body', False):
                    break
        except TimeoutError:
            return await amber_response(408, 'Request upload timed out. Verify in the manual.')(scope, receive, send)
        replayed = False

        async def replay():
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {'type': 'http.request', 'body': bytes(body), 'more_body': False}

        await self.app(scope, replay, send)


def create_app(service=None):
    app = FastAPI(title='Ambient Field Lens — default-deny assist')
    app.state.assist_service = service or AssistService()
    app.add_middleware(RequestBoundary)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Pydantic's normal error output includes the submitted input; omit it.
        return amber_response(422, 'Invalid query or JPEG frame. Verify in the manual.')

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return amber_response(exc.status_code, 'Request could not be accepted. Verify in the manual.')

    @app.get('/healthz')
    async def healthz():
        return {'ok': True, 'gate': 'default-deny', 'phase': 1,
                'circuit': app.state.assist_service.breaker.state()}

    @app.post('/assist', response_model=AssistResponse)
    async def assist(request: AssistRequest):
        status, response = await app.state.assist_service.assist(request)
        return JSONResponse(status_code=status, content=response.model_dump(),
                            headers={'Cache-Control': 'no-store'})

    @app.post('/report_gap')
    async def report_gap_route(request: Request):
        # Separate route, own shape: always 200 with {"ok"} so the phone
        # never has to parse an amber envelope here. All shaping and
        # fail-closed validation lives in gap_report; this is transport.
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=200,
                                content={'ok': False, 'error': 'bad_json'},
                                headers={'Cache-Control': 'no-store'})
        if not isinstance(body, dict):
            return JSONResponse(status_code=200,
                                content={'ok': False, 'error': 'bad_json'},
                                headers={'Cache-Control': 'no-store'})
        # Sync + sleeps on retry: worker thread, never the loop.
        ok, error = await asyncio.to_thread(
            gap_report.report_gap,
            body.get('question'), body.get('answer'),
            body.get('retrieved_chunk_ids'), body.get('top1_distance'),
            body.get('comment'))
        content = {'ok': ok}
        if not ok:
            content['error'] = error
        return JSONResponse(status_code=200, content=content,
                            headers={'Cache-Control': 'no-store'})

    return app


app = create_app()
