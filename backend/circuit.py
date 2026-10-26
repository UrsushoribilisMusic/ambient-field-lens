"""Small per-process closed/open/half-open breaker, implemented in this repo."""
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Permit:
    generation: int
    probe: bool = False


class CircuitBreaker:
    def __init__(self, threshold=3, recovery_seconds=30.0, clock=time.monotonic):
        if threshold < 1 or recovery_seconds <= 0:
            raise ValueError('breaker limits must be positive')
        self.threshold = threshold
        self.recovery_seconds = recovery_seconds
        self.clock = clock
        self.failures = 0
        self.open_until = None
        self.probe_in_flight = False
        self.generation = 0
        self.lock = threading.Lock()

    def admit(self):
        with self.lock:
            if self.open_until is None:
                return Permit(self.generation)
            if self.clock() < self.open_until or self.probe_in_flight:
                return None
            self.probe_in_flight = True
            return Permit(self.generation, probe=True)

    def succeeded(self, permit):
        with self.lock:
            # A late success from a call admitted before the circuit opened
            # cannot override the cooldown. Only the half-open probe may close it.
            if permit.generation != self.generation:
                return
            if self.open_until is None or (permit.probe and self.probe_in_flight):
                self.failures = 0
                self.open_until = None
                self.probe_in_flight = False
                if permit.probe:
                    self.generation += 1

    def failed(self, permit):
        with self.lock:
            if permit.generation != self.generation:
                return
            self.failures += 1
            if self.failures >= self.threshold or self.probe_in_flight:
                self.open_until = self.clock() + self.recovery_seconds
                self.generation += 1
            self.probe_in_flight = False

    def state(self):
        with self.lock:
            if self.open_until is None:
                return 'closed'
            return 'open' if self.clock() < self.open_until else 'half-open'
