"""W1 in-memory framing/control surrogate; NEVER an authenticated native IPC implementation."""
import hashlib
import hmac
import json
import math
import re
import struct
from collections import OrderedDict

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
    base = {"type", "id", "attempt", "capability"}
    if kind == "CommitInstall":
        fields = base | {"readyEpoch", "version", "digest", "installed"}
    elif kind in {"PrepareLatestStable", "CancelPreparation", "GetStatus"}:
        fields = base
    else:
        raise Rejected("unknown command")
    if set(v) != fields:
        raise Rejected("unknown/missing fields")
    for key in ("id", "attempt"):
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
    """Authentication is an injected MODEL fact. It does not verify OS identities."""
    def __init__(self, attempt, capability, authenticated=False):
        self.attempt = attempt
        self.capability = capability
        self.authenticated = authenticated
        self.phase = "ready"
        self.epoch = 1
        self.version = "1.2.10"
        self.installed = "1.2.9"
        self.digest = "a" * 64
        self.events = 0
        self.effects = 0
        self.cache = OrderedDict()
        self.rate_second = None
        self.rate_count = 0

    def request(self, command, now=0):
        validate(command)
        if not self.authenticated:
            raise Rejected("model peer not authenticated")
        if command.get("attempt") != self.attempt or not hmac.compare_digest(command.get("capability", ""), self.capability):
            raise Rejected("foreign attempt/capability")
        if self.rate_second != int(now):
            self.rate_second, self.rate_count = int(now), 0
        self.rate_count += 1
        if self.rate_count > 10:
            raise Rejected("rate bound")
        payload = hashlib.sha256(json.dumps(command, sort_keys=True).encode()).digest()
        key = command["id"]
        if key in self.cache:
            previous, accepted = self.cache[key]
            if previous != payload:
                raise Rejected("conflicting command id")
            # Replaying a historical ACK is not a fresh instruction to close.
            return {"accepted": accepted, "state": self.phase,
                    "closeAuthorized": accepted and self.phase == "committed"}
        if len(self.cache) >= 32:
            raise Rejected("command cache bound")
        kind = command["type"]
        accepted = False
        if kind == "CommitInstall":
            expected = (self.epoch, self.version, self.digest, self.installed)
            actual = tuple(command[k] for k in ("readyEpoch", "version", "digest", "installed"))
            if self.phase != "ready" or actual != expected:
                raise Rejected("stale consent")
            self.phase = "committed"
            self.effects += 1
            accepted = True
        elif kind == "CancelPreparation":
            if self.phase not in {"ready", "preparing"}:
                raise Rejected("too late")
            self.phase = "canceled"
        elif kind == "GetStatus":
            pass
        elif kind == "PrepareLatestStable":
            raise Rejected("one modeled Ready attempt only")
        else:
            raise Rejected("hello is not a control command")
        self.cache[key] = (payload, accepted)
        self.events += 1
        return {"accepted": accepted, "state": self.phase,
                "closeAuthorized": accepted and self.phase == "committed"}


class FakeOutbound:
    """A single replaceable progress slot: a non-reading client never blocks a tick."""
    def __init__(self):
        self.latest = None
        self.ticks = 0

    def tick(self, snapshot):
        self.latest = snapshot
        self.ticks += 1
