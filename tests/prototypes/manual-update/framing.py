"""W1 in-memory framing/control surrogate; NEVER an authenticated native IPC implementation."""
import hashlib
import hmac
import json
import math
import re
import struct
from timing import Budget

MAX_FRAME = 16384
MAX_CHUNK = 4096
MAX_DEPTH = 8
MAX_STRING = 2048
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
VERSION = re.compile(r"(?:0|[1-9][0-9]{0,8})(?:\.(?:0|[1-9][0-9]{0,8})){2}\Z")


class Rejected(ValueError):
    pass


def integer(text):
    if len(text) > 20:
        raise Rejected("integer bound")
    value = int(text)
    if not -(2**63) <= value < 2**63:
        raise Rejected("integer bound")
    return value


def no_number(_):
    raise Rejected("non-integer numeric value")


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected("duplicate key")
        result[key] = value
    return result


def decode(body):
    text = body.decode("utf-8", errors="strict")
    quoted = escaped = False
    depth = 0
    for ch in text:
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise Rejected("depth bound")
        elif ch in "]}":
            depth -= 1
    value = json.loads(text, object_pairs_hook=object_pairs, parse_int=integer,
                       parse_float=no_number, parse_constant=no_number)
    if not isinstance(value, dict):
        raise Rejected("object required")
    validate(value)
    return value


def validate(v):
    if any(not isinstance(k, str) or len(k) > MAX_STRING or
           (isinstance(x, str) and len(x) > MAX_STRING) for k, x in v.items()):
        raise Rejected("string bound")
    kind = v.get("type")
    if not isinstance(kind, str):
        raise Rejected("command type must be a string")
    if kind == "Hello":
        if set(v) != {"type", "protocol"} or type(v["protocol"]) is not int or v["protocol"] != 1:
            raise Rejected("unsupported hello")
        return
    identifier = "queryId" if kind == "GetStatus" else "commandId"
    base = {"type", identifier, "attempt", "capability"}
    if kind == "CommitInstall":
        fields = base | {"readyEpoch", "version", "digest", "installed"}
    elif kind in {"PrepareLatestStable", "CancelPreparation", "GetStatus"}:
        fields = base
    else:
        raise Rejected("unknown command")
    if set(v) != fields:
        raise Rejected("unknown/missing fields")
    for key in (identifier, "attempt"):
        if not isinstance(v[key], str) or not UUID.fullmatch(v[key]):
            raise Rejected("invalid identifier")
    if not isinstance(v["capability"], str) or not HEX.fullmatch(v["capability"]):
        raise Rejected("invalid capability")
    if kind == "CommitInstall":
        if type(v["readyEpoch"]) is not int or not 0 < v["readyEpoch"] < 2**63:
            raise Rejected("epoch bound")
        if not isinstance(v["digest"], str) or not HEX.fullmatch(v["digest"]):
            raise Rejected("digest bound")
        for key in ("version", "installed"):
            if not isinstance(v[key], str) or not VERSION.fullmatch(v[key]):
                raise Rejected("version bound")


def encode(value):
    body = json.dumps(value, separators=(",", ":"), allow_nan=False).encode()
    return struct.pack("!I", len(body)) + body


class Framer:
    def __init__(self):
        self.buffer = bytearray()
        self.started = None
        self.closed = False
        self.high_water = 0
        self.last_time = 0

    def feed(self, data, now):
        if self.closed:
            raise Rejected("closed")
        try:
            if type(now) not in (int, float) or not math.isfinite(now) or now < self.last_time:
                raise Rejected("invalid clock")
            self.last_time = now
            if not isinstance(data, (bytes, bytearray)):
                raise Rejected("byte input required")
            if len(data) > MAX_CHUNK:
                raise Rejected("read chunk bound")
            if self.started is not None and now - self.started >= 5:
                raise Rejected("frame timeout")
            if data and not self.buffer:
                self.started = now
            self.buffer.extend(data)
            self.high_water = max(self.high_water, len(self.buffer))
            messages = []
            while len(self.buffer) >= 4:
                size = struct.unpack("!I", self.buffer[:4])[0]
                if not 0 < size <= MAX_FRAME:
                    raise Rejected("frame length")
                if len(self.buffer) < size + 4:
                    break
                messages.append(decode(bytes(self.buffer[4:size + 4])))
                del self.buffer[:size + 4]
                self.started = now if self.buffer else None
            if len(self.buffer) > MAX_FRAME + 4:
                raise Rejected("buffer bound")
            return messages
        except (ValueError, UnicodeError, RecursionError, struct.error) as exc:
            self.closed = True
            self.buffer.clear()
            raise Rejected(str(exc)) from exc

    def eof(self):
        self.closed = True
        if self.buffer:
            self.buffer.clear()
            raise Rejected("truncated frame")


class Controller:
    """All peer, process and gate identities below are injected MODEL facts."""
    def __init__(self, attempt, capability, authenticated=False):
        self.attempt, self.capability = attempt, capability
        self.authenticated = authenticated
        self.phase, self.epoch = "ready", 1
        self.version, self.installed, self.digest = "1.2.10", "1.2.9", "a" * 64
        self.incarnation, self.channel, self.process = "supervisor-1", "channel-1", "gui-1"
        self.events = self.effects = 0
        self.cache = {}  # accepted mutation payloads only, at most three action slots
        self.actions = {}
        self.rate_times = []  # sliding one-second window, at most ten accepted frames
        self.budget = Budget()
        self.operation = True
        self.admission = False
        self.query_pending = None  # one coalesced response, no query history

    def response(self, correlation, accepted, now, control=False):
        deadline = None if self.budget.committed_at is None else self.budget.committed_at + 30
        return dict(effectAccepted=accepted, state=self.phase, eventSequence=self.events,
                    closeAuthorized=bool(control and accepted and self.phase == "committed"
                        and self.operation and self.admission and deadline is not None
                        and now < deadline and not self.budget.suspended),
                    attempt=self.attempt, incarnation=self.incarnation, channel=self.channel,
                    process=self.process, readyEpoch=self.epoch, digest=self.digest,
                    correlation=correlation, drainDeadline=deadline, boot=self.budget.boot)

    def request(self, command, now=0):
        validate(command)
        if not self.authenticated:
            raise Rejected("model peer not authenticated")
        if command.get("attempt") != self.attempt or not hmac.compare_digest(command.get("capability", ""), self.capability):
            raise Rejected("foreign attempt/capability")
        self.tick(now)
        self.rate_times = [at for at in self.rate_times if now - at < 1]
        if len(self.rate_times) >= 10:
            raise Rejected("rate bound")
        self.rate_times.append(now)
        kind = command["type"]
        if kind == "GetStatus":
            if self.query_pending is not None:
                raise Rejected("query outstanding")
            self.query_pending = self.response(command["queryId"], False, now)
            return self.query_pending
        key = command["commandId"]
        payload = hashlib.sha256(json.dumps(command, sort_keys=True).encode()).digest()
        if key in self.cache:
            previous, original_kind = self.cache[key]
            if previous != payload:
                raise Rejected("conflicting command id")
            return self.response(key, True, now, original_kind == "CommitInstall")
        if kind in self.actions:
            raise Rejected("AlreadyAccepted")
        if kind == "CommitInstall":
            expected = (self.epoch, self.version, self.digest, self.installed)
            actual = tuple(command[k] for k in ("readyEpoch", "version", "digest", "installed"))
            if self.phase != "ready" or actual != expected or not self.operation:
                raise Rejected("stale consent")
            if self.budget.commit(now) != "committed":
                raise Rejected("expired or stale eligibility")
            self.phase, self.admission = "committed", True
            self.effects += 1
        elif kind == "CancelPreparation":
            if self.phase not in {"ready", "preparing"}:
                raise Rejected("too late")
            self.phase, self.operation = "canceled", False
        elif kind == "PrepareLatestStable":
            raise Rejected("one modeled Ready attempt only")
        else:
            raise Rejected("hello is not a control command")
        self.cache[key] = (payload, kind)
        self.actions[kind] = key
        self.events += 1
        return self.response(key, True, now, kind == "CommitInstall")

    def tick(self, now, boot=None):
        """Explicit scheduling barrier; no client read is needed for timeouts."""
        valid = self.budget.valid_clock(now, self.budget.boot if boot is None else boot)
        expired = self.phase == "ready" and (not valid or now - self.budget.ready_at >= 300)
        deferred = self.phase == "committed" and (not valid or now - self.budget.committed_at >= 30)
        if expired or deferred:
            self.phase = "expired" if expired else "deferred"
            self.operation = self.admission = False
            self.budget.stopped = True
            self.events += 1
        if not valid:
            raise Rejected("invalid clock")

    def consume_status(self):
        if self.query_pending is None:
            return None
        query_id = self.query_pending["correlation"]
        self.query_pending = None
        return self.response(query_id, False, self.budget.last_time)


class Bridge:
    """Synthetic client checks; shared clock, OS peer and process liveness injected."""
    def __init__(self, controller, command_id):
        self.bindings = {k: getattr(controller, v) for k, v in
                         (("attempt", "attempt"), ("incarnation", "incarnation"),
                          ("channel", "channel"), ("process", "process"),
                          ("readyEpoch", "epoch"), ("digest", "digest"))}
        self.bindings.update(correlation=command_id, boot=controller.budget.boot)
        self.highest = 0
        self.terminal = False
        self.invalidated = False
        self.last_time = 0

    def accepts(self, reply, now, live=True, mapped=True, suspended=False):
        if (type(now) not in (int, float) or not math.isfinite(now)
                or now < self.last_time):
            self.invalidated = True
            return False
        self.last_time = now
        if not live or not mapped or suspended:
            self.invalidated = True
        if self.invalidated or not isinstance(reply, dict):
            return False
        # Observe authenticated status/progress independently of commit correlation.
        if any(type(reply.get(k)) is not type(v) or reply.get(k) != v
               for k, v in self.bindings.items() if k != "correlation"):
            return False
        sequence = reply.get("eventSequence")
        if type(sequence) is not int or sequence < self.highest:
            return False
        self.highest = sequence
        self.terminal |= reply.get("state") in {"deferred", "canceled", "expired", "recovery", "updated", "paused", "failed"}
        deadline = reply.get("drainDeadline")
        return bool(not self.terminal and reply.get("correlation") == self.bindings["correlation"]
                    and reply.get("state") == "committed"
                    and reply.get("effectAccepted") is True and reply.get("closeAuthorized") is True
                    and type(deadline) in (int, float) and math.isfinite(deadline) and now < deadline)


class FakeOutbound:
    """A single replaceable progress slot: a non-reading client never blocks a tick."""
    def __init__(self):
        self.latest = None
        self.ticks = 0

    def tick(self, snapshot):
        self.latest = snapshot
        self.ticks += 1
