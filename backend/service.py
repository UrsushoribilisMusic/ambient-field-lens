"""Bounded execution boundary for a future retrieval/model provider."""
import asyncio
from dataclasses import dataclass

from circuit import CircuitBreaker
from contracts import AssistResponse, CALIBRATION_PENDING_DETAIL, deny


class LowGrounding(Exception):
    """Future providers use this when grounding validation fails repeatedly."""


@dataclass(frozen=True)
class Limits:
    timeout_seconds: float = 2.5
    concurrency: int = 4
    queue_seconds: float = 0.01
    breaker_failures: int = 3
    recovery_seconds: float = 30.0

    def __post_init__(self):
        if min(self.timeout_seconds, self.concurrency, self.queue_seconds,
               self.breaker_failures, self.recovery_seconds) <= 0:
            raise ValueError('limits must be positive')


async def default_backend(request):
    return deny(CALIBRATION_PENDING_DETAIL)


class AssistService:
    def __init__(self, backend=default_backend, limits=None, breaker=None):
        self.backend = backend
        self.limits = limits or Limits()
        self.slots = asyncio.Semaphore(self.limits.concurrency)
        self.breaker = breaker or CircuitBreaker(self.limits.breaker_failures, self.limits.recovery_seconds)

    async def assist(self, request):
        if not request.image_jpeg_base64:
            return 200, deny('No camera frame was supplied. Verify in the manual before touching the machine.')
        try:
            await asyncio.wait_for(self.slots.acquire(), timeout=self.limits.queue_seconds)
        except TimeoutError:
            return 429, deny('Assistant is busy. Verify in the manual.')
        try:
            permit = self.breaker.admit()
            if permit is None:
                return 503, deny('Assistant is temporarily unavailable. Verify in the manual.')
            try:
                result = await asyncio.wait_for(self.backend(request), timeout=self.limits.timeout_seconds)
                result = AssistResponse.model_validate(result)
            except asyncio.CancelledError:
                self.breaker.failed(permit)
                raise
            except LowGrounding:
                self.breaker.failed(permit)
                return 200, deny('Grounding check did not pass. Verify in the manual.')
            except TimeoutError:
                self.breaker.failed(permit)
                return 504, deny('Assistant timed out. Verify in the manual.')
            except Exception:
                # Never expose provider exception text, image data, or partial instructions.
                self.breaker.failed(permit)
                return 503, deny('Assistant could not validate a response. Verify in the manual.')
            self.breaker.succeeded(permit)
            # Model/provider text is not allowed into even an amber detail card.
            # Phase 3 must explicitly introduce a calibrated evidence contract.
            return 200, deny(CALIBRATION_PENDING_DETAIL)
        finally:
            self.slots.release()
