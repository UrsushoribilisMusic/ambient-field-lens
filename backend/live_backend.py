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


def read_window():
    """Capability envelope for the live demo window. Claimed call-first."""
    import modal
    try:
        record = modal.Dict.from_name('afl-live', create_if_missing=True).get('active')
    except Exception:
        raise WindowUnavailable('Demo window store unreachable. Verify in the manual.')
    if not isinstance(record, dict):
        raise WindowUnavailable('No live demo window is open. Verify in the manual.')
    if record.get('expires_at', 0) <= time.time():
        raise WindowUnavailable('Live demo window expired. Verify in the manual.')
    used = int(record.get('calls_used', 0))
    if used >= int(record.get('max_calls', 0)):
        raise WindowUnavailable('Live demo window call budget spent. Verify in the manual.')
    return record


def claim_call(record):
    """Consume one window call BEFORE providers run (budget-safe)."""
    import modal
    record['calls_used'] = int(record.get('calls_used', 0)) + 1
    modal.Dict.from_name('afl-live', create_if_missing=True).put('active', record)
    return str(record.get('id', 'unrecorded'))


def note_progress(stage):
    """Best-effort stage marker for the operator's own Mac. Names only."""
    try:
        import modal
        modal.Dict.from_name('afl-live', create_if_missing=True).put(
            'stage', {'stage': stage, 'at': time.time()})
    except Exception:
        pass


def note_failure(stage, kind):
    """Best-effort debug note for the operator's own Mac. Type only."""
    try:
        import modal
        modal.Dict.from_name('afl-live', create_if_missing=True).put(
            'last_error', {'stage': stage, 'type': kind, 'at': time.time()})
    except Exception:
        pass


def mask_label(mask):
    """Live SAM masks are (ident, Mask) tuples; fakes may be dicts."""
    if isinstance(mask, dict):
        return str(mask.get('id', '?'))[:8]
    if isinstance(mask, (tuple, list)):
        return str(mask[0])[:8] if mask else '?'
    return str(mask)[:8]


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
    timeout_seconds: float = 300.0
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
        try:
            permit = self.breaker.admit()
            if permit is None:
                return 503, deny('Assistant is temporarily unavailable. Verify in the manual.')
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.compose, request),
                    timeout=self.limits.timeout_seconds)
            except WindowUnavailable as exc:
                self.breaker.succeeded(permit)
                return 503, deny(str(exc))
            except TimeoutError:
                self.breaker.failed(permit)
                return 504, deny('Live check timed out. Verify in the manual.')
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

    def compose(self, request):
        """One frame through retrieval, SAM, Glimmer. Sync; run in a thread."""
        import tempfile
        stage = 'window'
        try:
            record = claim_call(read_window())
            image = base64.b64decode(request.image_jpeg_base64, validate=True)
            frame = sha(image)
            request_id = uuid.uuid4().hex[:16]
            stage = 'retrieve'
            note_progress(stage)
            evidence = client.retrieve(request.query, frame)
            chunks = evidence.get('chunks', [])
            if not chunks:
                # Prefix contract (docs/live-assist-wiring.md): the app
                # derives COVERAGE ✗ from this prefix. World state unknown:
                # retrieval runs before any frame is inspected.
                return deny('NOT COVERED: Manual returned no passage for this '
                            'question. Verify in the manual before touching '
                            'the machine.')
            stage = 'segment'
            note_progress(stage)
            segmentation = segment_paper(image, request_id=request_id,
                                         output_root=tempfile.mkdtemp(prefix='afl-live-'),
                                         box=None)
            masks = segmentation.get('masks', [])
            if not masks:
                # Prefix contract: the app derives WORLD ✗ from this prefix.
                # Coverage holds here (chunks were retrieved above).
                return deny('WORLD CHECK FAILED: No paper candidate in this '
                            'frame. Reposition the paper fully in view. '
                            'Verify in the manual.')
            stage = 'ground'
            note_progress(stage)
            score = client.grounding(
                request_id=request_id, question=request.query, evidence=evidence,
                image_jpeg_base64=request.image_jpeg_base64, frame_sha256=frame,
                window_id=record)
            stage = 'detail'
            return deny(evidence_detail(
                masks=masks,
                chunk_ids=[c.get('id', '?') for c in chunks],
                score=score.get('score') if isinstance(score, dict) else None))
        except Exception as exc:
            # Debug note carries the stage and exception TYPE only: never
            # provider text, image data, or partial steps. Best-effort.
            note_failure(stage, type(exc).__name__)
            raise


def create_live_service():
    return LiveAssistService()


if __name__ == '__main__':  # pragma: no cover - import check only
    assert isinstance(AssistRequest, type) and isinstance(LiveAssistService, type)
