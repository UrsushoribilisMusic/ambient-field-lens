"""Live /assist composition: real providers, amber-only verdict.

Reviewed-contract guest: reuses ``contracts`` (``Literal['verify']``,
score pinned to 0.0, bounded detail) and ``circuit.CircuitBreaker``
untouched. It does NOT reuse ``AssistService``: that stub deliberately
discards provider detail and always returns the calibration-pending card.
This module mirrors its protections (empty-frame deny, single-flight
semaphore, breaker, fail-closed) while returning a compact EVIDENCE
SUMMARY inside the 300-char amber detail.

Amber-only rules (frozen, see docs/live-assist-wiring.md):
- verdict is type-level 'verify'; step is always None; score is 0.0.
- No threshold exists, so no world check can pass: every check is reported
  as unverified with its evidence attached.
- Autonomous SAM masks are object CANDIDATES (ambiguous by design), never
  paper presence, pen fitment, calibration, or approval.
- Measured geometry is unaccepted, so footprint clearance stays unmeasured.
- Any provider failure, missing/expired/exhausted window, or binding
  mismatch returns an amber denial, never a step, never provider text.
"""
import asyncio
import base64
import sys
import time
import uuid
from dataclasses import dataclass

from circuit import CircuitBreaker
from contracts import AssistRequest, AssistResponse, deny
from providers import client
from providers.payloads import sha
from providers.sam import segment_paper


class WindowUnavailable(Exception):
    pass


# Coverage is a threshold on the top chunk's retrieval distance, not an
# emptiness check: the provider raises no_ross_evidence on empty (which
# surfaces as a 502 failure amber), so an empty chunk list never reaches
# composition. Calibrated 2026-10-30 (docs/verification/coverage-
# calibration-2026-10-30.json): 8 Miguel-supported questions score
# 0.311-0.741; the validated paper-position anchor scores 0.820 and the
# coffee absurd 0.787. 0.76 sits between covered max and the nearest
# non-covered observation. Two hypothesized near-misses (paper centering
# 0.668, pen touch 0.725, both COMMANDS.md) land covered-side: they need
# Miguel's read on whether that chunk actually answers them. Frozen from
# that receipt; never tuned to green.
COVERAGE_DISTANCE_MAX = 0.76
# Calibration cluster shown on the card next to the measured distance.
COVERAGE_N = 8
COVERAGE_MAX = 0.741


class Abandoned(Exception):
    """A timed-out worker reached a stage gate after abandonment. Never amber text."""


def _store():
    import modal
    return modal.Dict.from_name('afl-live', create_if_missing=True)


def read_window():
    """Capability envelope for the live demo window. Claimed call-first."""
    try:
        record = _store().get('active')
    except Exception:
        raise WindowUnavailable('Demo window store unreachable. Verify in the manual.')
    if not isinstance(record, dict):
        raise WindowUnavailable('No live demo window is open. Verify in the manual.')
    if record.get('expires_at', 0) <= time.time():
        raise WindowUnavailable('Live demo window expired. Verify in the manual.')
    return record


def _token_keys(record):
    wid = str(record.get('id', 'unrecorded'))
    return [f'{wid}:call-{i}' for i in range(int(record.get('max_calls', 0)))]


def _live_id(store):
    """Current window id, or None. Single read, no mutation."""
    try:
        live = store.get('active')
    except Exception:
        raise WindowUnavailable('Demo window store unreachable. Verify in the manual.')
    if not isinstance(live, dict):
        return None
    if live.get('expires_at', 0) <= time.time():
        return None
    return live.get('id')


def claim_call(record):
    """Consume one single-use token BEFORE providers run (budget-safe).

    Tokens are namespaced per window id and consumed with pop(), which is
    the store's own atomic take: each token can be spent once no matter
    how many instances race. Total spend can never exceed the tokens
    issued. The active row is NEVER written here — a stats put after a
    close would resurrect a dead window, and the row is only a display
    snapshot, not the budget authority.

    Close/replacement interleavings: the window id is re-validated AFTER
    the pop. A close or replace landing mid-claim sacrifices the popped
    token and refuses fail-closed (under-count). True single-authority
    serialization would need store transactions the Dict API does not
    offer; this is the documented best-available shape.
    """
    store = _store()
    if _live_id(store) != record.get('id'):
        raise WindowUnavailable('Live demo window is not open. Verify in the manual.')
    for key in _token_keys(record):
        try:
            store.pop(key)
        except Exception:
            continue
        if _live_id(store) != record.get('id'):
            raise WindowUnavailable('Live demo window was replaced. Verify in the manual.')
        return str(record.get('id', 'unrecorded'))
    if _live_id(store) != record.get('id'):
        raise WindowUnavailable('Live demo window is not open. Verify in the manual.')
    raise WindowUnavailable('Live demo window call budget spent. Verify in the manual.')


def remaining_calls(window_id, store=None):
    """Count unspent tokens. Display only; the pop is the authority."""
    store = store or _store()
    try:
        return sum(1 for k in store.keys()
                   if isinstance(k, str) and k.startswith(f'{window_id}:call-'))
    except Exception:
        return -1


def arm_tokens(record, store=None):
    """Issue single-use call tokens for a window. Never refills spent ones.

    Issuance is recorded under a per-window marker: re-arming an issued
    window is a no-op, so a spent token can never come back. Replacing a
    window means a new id, hence a new namespace.
    """
    store = store or _store()
    wid = str(record.get('id', 'unrecorded'))
    try:
        if store.contains(f'{wid}:issued'):
            return
        for key in _token_keys(record):
            store.put(key, True)
        store.put(f'{wid}:issued', int(record.get('max_calls', 0)))
    except Exception:
        raise WindowUnavailable('Demo window store unreachable. Verify in the manual.')


def note_progress(stage):
    """Best-effort stage marker for the operator's own Mac. Names only."""
    try:
        _store().put('stage', {'stage': stage, 'at': time.time()})
    except Exception:
        pass


def note_failure(stage, kind):
    """Best-effort debug note for the operator's own Mac. Type only."""
    try:
        _store().put('last_error', {'stage': stage, 'type': kind, 'at': time.time()})
    except Exception:
        pass


def mask_label(mask):
    """Live SAM masks are (ident, Mask) tuples; fakes may be dicts."""
    if isinstance(mask, dict):
        return str(mask.get('id', '?'))[:8]
    if isinstance(mask, (tuple, list)):
        return str(mask[0])[:8] if mask else '?'
    return str(mask)[:8]


PASSAGE_MAX = 600


def passage_excerpt(chunks):
    """Top chunk text as a labeled excerpt, or None. Only ever called
    after the coverage gate passed, so the quoted chunk is the one the
    detail tail cites. Truncation is marked; never silently cut. The cut
    backs off past an unterminated code span or fence so markdown clients
    never inherit unbalanced markers."""
    if not chunks or not isinstance(chunks[0], dict):
        return None
    text = chunks[0].get('text')
    if not isinstance(text, str) or not text.strip():
        return None
    text = text.strip()
    if len(text) <= PASSAGE_MAX:
        return text
    cut = text[:PASSAGE_MAX]
    if cut.count('```') % 2 == 1:
        cut = cut.rsplit('```', 1)[0]
    elif cut.count('`') % 2 == 1:
        cut = cut.rsplit('`', 1)[0]
    return cut.rstrip() + ' […]'


def evidence_detail(*, masks, chunk_ids, score):
    """Compact evidence summary, contract-bounded to 300 chars."""
    mask_ids = ','.join(mask_label(m) for m in masks[:3])
    chunks = ','.join(str(c)[:24] for c in chunk_ids[:2])
    score_text = f'{score:.3f}' if isinstance(score, (int, float)) else 'unavailable'
    detail = (f'Live check (amber): paper candidates {len(masks)} [{mask_ids}]; '
              f'manual chunks [{chunks}]; grounding {score_text} uncalibrated, '
              f'no threshold; pen/fitment/calibration/footprint unverified. '
              f'Verify in the manual.')
    return detail[:300]


@dataclass(frozen=True)
class LiveLimits:
    # The phone quits at 180s; the slot must always free first, or a tap
    # during the drain earns a 60s queue and a 429 for nothing. Measured
    # round trip is 12-100s, so 150 loses nothing and bounds the lockout.
    timeout_seconds: float = 150.0
    concurrency: int = 1
    queue_seconds: float = 60.0
    breaker_failures: int = 3
    recovery_seconds: float = 30.0


class LiveAssistService:
    """Single-flight live composition. Amber-only by construction."""

    def __init__(self, limits=None, breaker=None):
        self.limits = limits or LiveLimits()
        self.slots = asyncio.Semaphore(self.limits.concurrency)
        self.breaker = breaker or CircuitBreaker(self.limits.breaker_failures,
                                                 self.limits.recovery_seconds)

    async def assist(self, request):
        if not request.image_jpeg_base64:
            return 200, deny('No camera frame was supplied. Verify in the manual '
                             'before touching the machine.')
        try:
            await asyncio.wait_for(self.slots.acquire(), timeout=self.limits.queue_seconds)
        except TimeoutError:
            return 429, deny('Assistant is busy. Verify in the manual.')
        # The slot stays held until the worker thread has actually drained:
        # a timed-out thread keeps running, so releasing early would let the
        # next request overlap paid provider stages. The worker checks the
        # deadline event before every paid stage and starts no new one after
        # abandonment; the join below bounds the drain by provider timeouts.
        import threading
        deadline = threading.Event()
        try:
            permit = self.breaker.admit()
            if permit is None:
                return 503, deny('Assistant is temporarily unavailable. Verify in the manual.')
            worker = asyncio.get_running_loop().run_in_executor(
                None, self.compose, request, deadline)
            try:
                response = await asyncio.wait_for(
                    asyncio.shield(worker), timeout=self.limits.timeout_seconds)
            except WindowUnavailable as exc:
                self.breaker.succeeded(permit)
                return 503, deny(str(exc))
            except TimeoutError:
                deadline.set()
                self.breaker.failed(permit)
                await self._drain(worker)
                return 504, deny('Live check timed out. Verify in the manual.')
            except asyncio.CancelledError:
                deadline.set()
                self.breaker.failed(permit)
                await self._drain(worker)
                raise
            except Exception as exc:
                # Server-side stage log carries the exception TYPE only: never
                # provider text, image data, or partial steps (fail-closed).
                print('live-assist-failure:', type(exc).__name__, flush=True,
                      file=sys.stderr)
                self.breaker.failed(permit)
                return 502, deny('Live check failed. Verify in the manual.')
            self.breaker.succeeded(permit)
            return 200, response
        finally:
            self.slots.release()

    @staticmethod
    async def _drain(worker):
        """Retain admission until the worker actually stops.

        Repeated cancellation only re-waits: the loop exits when the worker
        thread exits, never by releasing early. Bounded by provider
        timeouts (SAM transport 90 s); an unbounded provider block is a
        documented residual risk, not a slot leak by design.
        """
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except BaseException:
                continue
        try:
            worker.result()
        except BaseException:
            pass

    def compose(self, request, deadline=None):
        """One frame through retrieval, SAM, Glimmer. Sync; run in a thread.

        `deadline` is set when the caller abandons the worker (timeout).
        Every paid stage gate-checks it first: an abandoned worker starts
        no new provider stage, then exits so the held slot can drain.
        """
        import tempfile
        import threading
        dead = deadline or threading.Event()
        def gated(name):
            if dead.is_set():
                raise Abandoned()
            note_progress(name)
            return name
        stage = 'window'
        try:
            record = claim_call(read_window())
            image = base64.b64decode(request.image_jpeg_base64, validate=True)
            frame = sha(image)
            request_id = uuid.uuid4().hex[:16]
            stage = gated('retrieve')
            evidence = client.retrieve(request.query, frame)
            chunks = evidence.get('chunks', [])
            if not chunks:
                # Unreachable via the current provider (empty raises
                # no_ross_evidence, which lands in the 502 failure path).
                # Retained as the fail-closed default if a future provider
                # ever returns empty: no passage, no coverage.
                return deny('NOT COVERED: Manual returned no passage for this '
                            'question. Verify in the manual before touching '
                            'the machine.')
            distance = chunks[0].get('distance') if isinstance(chunks[0], dict) else None
            if (COVERAGE_DISTANCE_MAX is not None
                    and isinstance(distance, (int, float))
                    and distance > COVERAGE_DISTANCE_MAX):
                # Prefix contract (docs/live-assist-wiring.md): the app
                # derives COVERAGE ✗ from this prefix and offers the gap
                # report from its tail. World state unknown: retrieval runs
                # before any frame is inspected. The tail carries the top
                # chunk id and the measured distance for the report; the app
                # may hide the tail on screen but must post it verbatim.
                top_id = chunks[0].get('id', '?') if isinstance(chunks[0], dict) else '?'
                return deny(
                    'NOT COVERED: No manual passage within the coverage '
                    'threshold (d=%.3f>%.3f; %d covered max %.3f). Verify '
                    'in the manual. top=%s'
                    % (distance, COVERAGE_DISTANCE_MAX, COVERAGE_N,
                       COVERAGE_MAX, top_id))
            stage = gated('segment')
            segmentation = segment_paper(image, request_id=request_id,
                                         output_root=tempfile.mkdtemp(prefix='afl-live-'),
                                         box=None)
            masks = segmentation.get('masks', [])
            if not masks:
                # Prefix contract: the app derives WORLD ✗ from this prefix.
                # Coverage holds here (chunks were retrieved above), so the
                # card also quotes the covered passage: quotation, not
                # endorsement — the verdict stays verify either way.
                return deny('WORLD CHECK FAILED: No paper candidate in this '
                            'frame. Reposition the paper fully in view. '
                            'Verify in the manual.',
                            passage=passage_excerpt(chunks))
            stage = gated('ground')
            score = client.grounding(
                request_id=request_id, question=request.query, evidence=evidence,
                image_jpeg_base64=request.image_jpeg_base64, frame_sha256=frame,
                window_id=record)
            stage = 'detail'
            return deny(evidence_detail(
                masks=masks,
                chunk_ids=[c.get('id', '?') for c in chunks],
                score=score.get('score') if isinstance(score, dict) else None),
                passage=passage_excerpt(chunks))
        except Exception as exc:
            # Debug note carries the stage and exception TYPE only: never
            # provider text, image data, or partial steps. Best-effort.
            note_failure(stage, type(exc).__name__)
            raise


def create_live_service():
    return LiveAssistService()


if __name__ == '__main__':  # pragma: no cover - import check only
    assert isinstance(AssistRequest, type) and isinstance(LiveAssistService, type)
