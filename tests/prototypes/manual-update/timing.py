"""Synthetic clock; no OS time, sleeping, I/O, or claims about real scheduler fairness."""
from dataclasses import dataclass


@dataclass
class Budget:
    ready_at: float = 0
    eligibility_at: float = 0
    committed_at: float | None = None
    boot: str = "prototype-boot"
    suspended: bool = False
    intent: bool = False

    def commit(self, now, boot="prototype-boot"):
        if self.suspended or boot != self.boot or now - self.ready_at >= 300 or now < self.ready_at:
            return "expired"
        if now - self.eligibility_at > 10:
            return "refresh_before_admission"
        self.committed_at = now
        return "committed"

    def before_spawn(self, now, drained=True):
        if self.committed_at is None:
            return "not_committed"
        if self.intent:
            return "retain_uncertain_intent"  # never erase intent on a deadline
        elapsed = now - self.committed_at
        if elapsed >= 45 or (not drained and elapsed >= 30):
            return "deferred"
        if not drained:
            return "waiting"
        if now - self.eligibility_at > 10:
            return "deferred_stale_eligibility"
        return "may_write_intent"
