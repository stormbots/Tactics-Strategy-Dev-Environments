"""Revision-3 synthetic budgets; no OS clock, scheduling or durability proof."""
import math
from dataclasses import dataclass


@dataclass
class Budget:
    ready_at: float = 0
    eligibility_at: float = 0
    committed_at: float | None = None
    drained_at: float | None = None
    boot: str = "prototype-boot"
    suspended: bool = False
    intent: bool = False
    last_time: float = 0

    def valid_clock(self, now, boot):
        valid = (type(now) in (int, float) and math.isfinite(now)
                 and now >= self.last_time and boot == self.boot and not self.suspended)
        if valid:
            self.last_time = now
        return valid

    def commit(self, now, boot="prototype-boot"):
        if not self.valid_clock(now, boot) or now - self.ready_at >= 300 or now < self.ready_at:
            return "expired"
        if self.committed_at is not None:
            return "already_committed"  # retries never renew the reservation
        if not 0 <= now - self.eligibility_at <= 10:
            return "refresh_before_admission"
        self.committed_at = now  # models the instant A is actually acquired
        return "committed"

    def before_spawn(self, now, drained=True, boot="prototype-boot", paused=False, integrity=True):
        valid = self.valid_clock(now, boot)
        if self.committed_at is None:
            return "not_committed"
        if not valid or paused or not integrity:
            return "retain_uncertain_intent" if self.intent else "deferred"
        elapsed = now - self.committed_at
        if self.drained_at is None and drained and elapsed < 30:
            self.drained_at = now
        if elapsed >= 45 or self.drained_at is None and elapsed >= 30:
            return "retain_uncertain_intent" if self.intent else "deferred"
        if self.drained_at is None:
            return "waiting"
        return "may_spawn" if self.intent else "may_write_intent"
