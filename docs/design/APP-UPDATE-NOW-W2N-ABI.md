# #72 W2n D1: C/ctypes interface and serialized ABI v1

Status: **documentation only; no implementation, compilation or experiments**.
This specification closes the interface/layout documentation gap identified in
[revision-2 review](APP-UPDATE-NOW-W2N-REVIEW.md). It supplements the
[receive-observation specification](APP-UPDATE-NOW-W2N-RECEIVE-OBSERVATION.md),
which controls schedules, scope, ownership and outcome meanings. This is a test
observer ABI, not production authenticated IPC. No execution is authorized here.

## 1. Conventions and supported profile

Public functions use the platform C calling convention with exact-width integer
parameters. Wire records are byte arrays, **not exported native C structs**.
All multi-byte wire values are little-endian; signed values use two's complement.
Every reserved byte is zero. Unknown ABI versions, enum values, issue bits,
nonzero reserved bytes or inconsistent lengths invalidate evidence; never guess
an alternative layout. No pointer value or function address is serialized.

Only profile 1 is supported: Linux x86-64 little-endian LP64, CHAR_BIT=8,
sizeof(void*)=sizeof(size_t)=sizeof(ssize_t)=sizeof(long)=8,
sizeof(int)=sizeof(pid_t)=sizeof(uid_t)=sizeof(gid_t)=sizeof(socklen_t)=4.
Profile mismatch is Unsupported before action admission, not a fallback.

Constants: ABI version=1; ABI block=256 bytes; status=256; provider=512;
capture=1536; chunk=512; raw control/payload capture bounds=256 each;
action payload receive capacity=16384; N1 ancillary=256;
N2 ancillary=CMSG_SPACE(12)+CMSG_LEN(4)=32+20=52. The 256-byte capture bound
never changes the 16384-byte receive capacity. Case IDs 1/2 mean N1/N2 with
unchanged M1/M2 wire attempts. Phase ID is exactly 1 (action); generation is 0
before arm and exactly 1 after arm. One arm and one capture per server process.

Run ID is exactly 16 non-all-zero bytes supplied by the trusted orchestrator
before Hello; it identifies the fixture, not a secret or authentication claim.
Process identity, namespaces, loaded-file hashes and socket dev/inode remain
independently recorded in the parent trace. Wire PID alone is not OS instance
identity. Counters are unsigned 64-bit, saturating at UINT64_MAX; saturation
sets CounterOverflow and invalidates observation rather than wrapping.

## 2. Exact C API

These are declarations for future implementation, not code implemented by this
change. No other observer control export is permitted in ABI v1. The interposed
symbol itself retains the system recvmsg prototype.

```c
#include <stdint.h>
#include <sys/socket.h>

ssize_t recvmsg(int sockfd, struct msghdr *msg, int flags);

int32_t w2n_v1_setup(const uint8_t *run_id, uint32_t run_id_len,
                     uint32_t case_id, uint64_t phase_id);
int32_t w2n_v1_abi(uint8_t *out, uint32_t out_capacity);
int32_t w2n_v1_provider(uint8_t *out, uint32_t out_capacity);
int32_t w2n_v1_status(uint8_t *out, uint32_t out_capacity);
int32_t w2n_v1_arm(int32_t sockfd, uint64_t expected_entry_count);
int32_t w2n_v1_freeze(void);
int32_t w2n_v1_read(uint64_t generation, uint32_t offset,
                    uint32_t length, uint8_t *out, uint32_t out_capacity);
```

All control functions preserve the caller's errno and return the following
int32 status, never a recvmsg result. No Python errcheck converts a status into
an assumed syscall errno. A real recvmsg return/errno has its own capture fields.

| Code | Name | Meaning |
| --- | --- | --- |
| 0 | OK | Operation completed exactly as specified. This is not safety acceptance. |
| 1 | NotReady | No completed call available to freeze/read, or lifecycle prerequisite not yet reached. No polling/receive occurs. |
| 2 | BadArgument | Null required buffer, wrong run-ID length/zero ID, invalid case/phase or negative FD. |
| 3 | BadState | Duplicate setup/arm, illegal lifecycle or unavailable frozen generation. |
| 4 | Unsupported | ABI/provider/loader prerequisite unsupported; no alternate mechanism. |
| 5 | InitializationFailed | Constructor resolution or setup failed; no action admission. |
| 6 | BadRange | Wrong output capacity, chunk length, offset or overflow risk. |
| 7 | BadGeneration | read generation differs from the one immutable frozen capture. |

For overlapping invalid inputs, validate in this order: null required pointer /
scalar syntax (BadArgument), declared output capacity and read length/offset
(BadRange), initialization/profile availability, lifecycle readiness, then frozen
generation. No buffer dereference occurs before those checks. read before Frozen
is NotReady; duplicate setup/arm is BadState. A nonnegative but unselected FD is
not checked by an observer syscall: parent trace verifies selection before arm.

On any nonzero status, output buffers remain untouched and no arm/capture/reset
is performed. NotReady does not invalidate the observer. Other control errors
set the sticky ControlMisuse issue bit, except Unsupported/InitializationFailed,
which retain their initialization failure flags. They must stop the diagnostic,
not be corrected by retries. An error may update status/issue accounting but
never previously captured or frozen bytes. No reset/clear API exists.

All three block-query functions can be called before setup once initialization
is complete. They return OK only when the entire defined block is available;
Unsupported/InitializationFailed leave output untouched. status remains available
in InitFailed and returns OK with failure flags/state when its fixed block can
be serialized. A successful ABI query exposes measured values; any mismatch
with profile 1 is still Unsupported for admission, even though serialization
succeeded. No function fabricates profile-1 values on a different ABI.

The caller is trusted in-process test Python: valid live input/output allocations
are its obligation. This API cannot validate arbitrary native addresses. Pointer
aliasing with internal observer storage is forbidden; no internal pointer is
returned. Insufficient caller capacity is not partial success. ABI/status require
out_capacity=256; provider requires 512; read requires 512. Success copies all
specified bytes, with no NUL terminator appended. Functions must validate scalar
arguments before dereferencing buffers; setup copies exactly 16 input bytes.

### Exact ctypes declarations

Use an already-preloaded, identity-verified library handle obtained without
loading a second instance (RTLD_NOLOAD with the verified path). These assignments
are normative documentation, not an executed Python program.

```python
U8P = ctypes.POINTER(ctypes.c_uint8)
lib.w2n_v1_setup.argtypes = [U8P, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint64]
lib.w2n_v1_abi.argtypes = [U8P, ctypes.c_uint32]
lib.w2n_v1_provider.argtypes = [U8P, ctypes.c_uint32]
lib.w2n_v1_status.argtypes = [U8P, ctypes.c_uint32]
lib.w2n_v1_arm.argtypes = [ctypes.c_int32, ctypes.c_uint64]
lib.w2n_v1_freeze.argtypes = []
lib.w2n_v1_read.argtypes = [ctypes.c_uint64, ctypes.c_uint32,
                           ctypes.c_uint32, U8P, ctypes.c_uint32]
lib.w2n_v1_setup.restype = ctypes.c_int32
lib.w2n_v1_abi.restype = ctypes.c_int32
lib.w2n_v1_provider.restype = ctypes.c_int32
lib.w2n_v1_status.restype = ctypes.c_int32
lib.w2n_v1_arm.restype = ctypes.c_int32
lib.w2n_v1_freeze.restype = ctypes.c_int32
lib.w2n_v1_read.restype = ctypes.c_int32
```

Use ctypes.CDLL with use_errno=False and no errcheck. The normative restype is
c_int32 for each function, not ctypes' implicit default. Validate Python integer
ranges before ctypes conversion (especially negative/overflowing unsigned values)
and pass live c_uint8 arrays, not c_char_p, Python strings or packed Structure
objects. A successful control call does not establish a valid capture: parse the
returned block and inspect lifecycle, issue and coverage fields independently.

## 3. Lifecycle and coverage

Constructor work resolves/warms the intended libc target and bounded provider
metadata before ready, as required by the main specification. Initial state is
Unconfigured=0, generation=0, accepted_fd=-1. Any initialization failure is
InitFailed=7, prohibits setup/arm and preserves failure status. ABI/provider/status
queries are allowed before setup once constructor work has completed.

- setup succeeds once from Unconfigured with zero entry/exit counters and no
  issues, installs run/case/phase and transitions to Ready=1. Earlier recvmsg
  entries produce BadState instead. It does not clear existing counters/issues.
  Call it before any fixture Hello. Unexpected earlier entries invalidate
  admission.
- In Ready, the ordinary server Hello receive must increment total entries/exits
  by exactly one with last_fd equal to the accepted socket. Record status before
  and after the existing Hello, with the same run token. No extra probe receive
  or action snapshot is added. Arm admission requires totals 1/1 and no issues.
- arm succeeds once from Ready, for the externally verified accepted FD and
  expected_entry_count exactly equal to current total entries (1). It stores
  that baseline, sets generation=1 and transitions to Armed=2. It performs no
  FD syscall, so socket object identity is supplied by parent trace checks.
- The one matching wrapper entry moves Armed→InCall=3. The normal real return
  moves InCall→CapturedRaw=4, records raw capture availability and saves
  entry/exit/arm-window counts. A real error still captures return=-1 and errno,
  but has Incomplete quality absent another instrumentation violation, and no
  output-buffer interpretation. Before freeze,
  quality is Incomplete (or Invalid for an already-known violation), never Valid
  before sanitization. Wrong FD,
  multiple entries, invalid shape or changed pointer sets issue bits and prevents
  Complete classification; supported calls are still forwarded once.
- freeze is legal from CapturedRaw after the original Python validation/closure/
  after-inventory stages, or the documented exception finalization path. It
  sanitizes private raw storage, assembles immutable generation 1 and transitions
  to Frozen=5. A malformed snapshot still freezes an Invalid partial record;
  freeze returns OK because the export exists, not because the observation passed.
  Calling freeze again in Frozen returns OK with identical bytes. It is NotReady
  before a completed call and never waits or invokes recvmsg.
- read is legal only in Frozen, with generation=1, length=512, capacity=512 and
  offset exactly 0, 512 or 1024. Each copies that exact capture range. Repeating a
  read is idempotent; it cannot rearm, recapture or mutate metadata. Before frozen
  use NotReady; an invalid generation uses BadGeneration once Frozen.

Normal successful action totals are entries=2, exits=2, window entries/exits=1/1,
call_id=2, arm baseline=1. Counts are actual wrapper observations, not values
manufactured to satisfy the expected schedule. Status contains the run token
installed by the interface and updated counts from the actual wrapper, binding
the interface storage instance to that interception. The process never rearms.

Any later entry after CapturedRaw/Frozen forwards once on the supported path but
sets MultipleEntry in **live status**, not immutable capture; it invalidates the
whole observation. Final status must be checked after capture retrieval before
claiming Complete. A frozen earlier record never overrides a later live issue.
An exceptional recursion/ownership-corruption abort is distinct from native
forwarding: fixed observer exit status **125**, no false recvmsg result. Parent
must classify it Invalid/Incomplete, not an installer exit code or a native
counterexample. Exit 125 alone does not prove its cause; retained evidence and
ownership are still required. Process death can lose the snapshot.

State 6 is reserved (reject if received). InitFailed=7 is the only other state.
No Failed state permits silent reset or a second run in the same server process.

## 4. ABI capability block: 256 bytes

All scalar fields below are u32 except the eight-byte magic. Native offsets are
reported for comparison, not permission to parse memory with guessed layouts.
Profile 1 requires every listed expected value; unknown/mismatch is Unsupported.
Profile 0 is a defined non-admissible capability report, not a second layout.
Other profile values are invalid. Observed capability values must not be rewritten
to expected constants to conceal a mismatch.

| Offset | Field | Required value |
| --- | --- | --- |
| 0 | magic, 8 bytes | ASCII `W2NABIv1` |
| 8 | version | 1 |
| 12 | block_bytes | 256 |
| 16 | native_profile | 1 required; 0 explicitly means unsupported measured profile |
| 20 | char_bits | 8 |
| 24 | sizeof_void_pointer | 8 |
| 28 | sizeof_size_t | 8 |
| 32 | sizeof_ssize_t | 8 |
| 36 | sizeof_int | 4 |
| 40 | sizeof_long | 8 |
| 44 | sizeof_msghdr | 56 |
| 48 | alignof_msghdr | 8 |
| 52 | offsetof_msg_name | 0 |
| 56 | offsetof_msg_namelen | 8 |
| 60 | offsetof_msg_iov | 16 |
| 64 | offsetof_msg_iovlen | 24 |
| 68 | offsetof_msg_control | 32 |
| 72 | offsetof_msg_controllen | 40 |
| 76 | offsetof_msg_flags | 48 |
| 80 | sizeof_iovec | 16 |
| 84 | alignof_iovec | 8 |
| 88 | offsetof_iov_base | 0 |
| 92 | offsetof_iov_len | 8 |
| 96 | sizeof_cmsghdr | 16 |
| 100 | alignof_cmsghdr | 8 |
| 104 | offsetof_cmsg_len | 0 |
| 108 | offsetof_cmsg_level | 8 |
| 112 | offsetof_cmsg_type | 12 |
| 116 | sizeof_ucred | 12 |
| 120 | offsetof_ucred_pid | 0 |
| 124 | offsetof_ucred_uid | 4 |
| 128 | offsetof_ucred_gid | 8 |
| 132 | cmsg_len_0 | 16 |
| 136 | cmsg_space_0 | 16 |
| 140 | cmsg_len_12 | 28 |
| 144 | cmsg_space_12 | 32 |
| 148 | cmsg_len_4 | 20 |
| 152 | cmsg_space_4 | 24 |
| 156 | partial_capacity | 52 |
| 160 | max_control_capture | 256 |
| 164 | action_payload_capacity | 16384 |
| 168 | max_payload_capture | 256 |
| 172 | sizeof_pid_t | 4 |
| 176 | sizeof_uid_t | 4 |
| 180 | sizeof_gid_t | 4 |
| 184 | capture_bytes | 1536 |
| 188 | chunk_bytes | 512 |
| 192 | native_endianness | 1 (little) |
| 196 | sizeof_socklen_t | 4 |
| 200 | alignof_ucred | 4 |
| 204–255 | reserved, 52 bytes | All zero |

## 5. Live status block: 256 bytes

| Offset | Type / bytes | Field |
| --- | --- | --- |
| 0 | bytes[8] | ASCII `W2NSTAT1` |
| 8 | u32 | version=1 |
| 12 | u32 | block_bytes=256 |
| 16 | u32 | lifecycle state (§3) |
| 20 | u32 | resolution: 0 unresolved, 1 target resolved/provider recorded, 2 failed |
| 24 | u64 | sticky issue_bits (§8) |
| 32 | u32 | case_id; 0 before setup |
| 36 | u32 | reserved=0 |
| 40 | u64 | phase_id; 0 before setup, then 1 |
| 48 | bytes[16] | run_id; zero before setup |
| 64 | u32 | cached actor PID, nonzero |
| 68 | i32 | accepted_fd; -1 before arm |
| 72 | u64 | generation; 0/1 |
| 80 | u64 | total_entries |
| 88 | u64 | total_exits |
| 96 | u64 | arm_entry_baseline; 0 before arm |
| 104 | u64 | window_entries; 0 before arm |
| 112 | u64 | window_exits; 0 before arm |
| 120 | i32 | last intercepted FD; -1 before any entry |
| 124 | u32 | frozen_bytes; 0 before freeze, then 1536 |
| 128 | u64 | last real-return call_id; 0 before any return |
| 136 | u32 | capture_quality; 0 before capture, otherwise §7 |
| 140 | u32 | reserved=0 |
| 144–255 | bytes[112] | reserved=0 |

Status is a consistent single-threaded sample, never a pointer into mutable
memory. Copy the whole status once per trace barrier. Reading it does not reset,
wait, receive, freeze or sanitize. Resolution=1 is not independent provider
attestation; validate the provider block against parent-recorded loaded files.
No field is an authorization outcome or current authentication assertion.

## 6. Provider block: 512 bytes

Constructor/setup inspection resolves metadata before admission; the receive
wrapper performs no dladdr/stat/readlink/open work. Missing required metadata
makes the provider Unsupported. Do not truncate a long name/path to fit.

| Offset | Type / bytes | Field |
| --- | --- | --- |
| 0 | bytes[8] | ASCII `W2NPROV1` |
| 8 | u32 | version=1 |
| 12 | u32 | block_bytes=512 |
| 16 | u32 | path_bytes; 1..384 |
| 20 | u32 | flags: bit0 dladdr metadata, bit1 file identity, bit2 target outside observer, bit3 symbol name known; required mask=15 |
| 24 | u64 | next provider st_dev |
| 32 | u64 | next provider st_ino |
| 40 | u64 | resolved target offset from provider ELF load base, not a raw address |
| 48 | u64 | observer file st_dev |
| 56 | u64 | observer file st_ino |
| 64 | u32 | symbol_name_bytes; 1..48 |
| 68 | u32 | cached actor PID |
| 72–79 | bytes[8] | reserved=0 |
| 80–127 | bytes[48] | symbol name, exactly length bytes then zero fill |
| 128–511 | bytes[384] | absolute resolved provider file path, exactly length bytes then zero fill |

Names/paths are filesystem/symbol bytes with no embedded NUL; serialize as hex,
not assumed UTF-8. Parent must verify the resolved next symbol is the intended
libc recvmsg implementation (document any libc alias), provider dev/inode and
actual file hashes, and no unexplained interposer chain. It must not disable
platform mediation to obtain a match. ELF/source provenance may remain Unknown;
these metadata do not certify upstream source identity or malicious-writer safety.

## 7. Frozen capture: 1536 bytes

Header bytes 0..511; sanitized control 512..767; control mask 768..1023;
payload 1024..1279; payload mask 1280..1535. All header offsets are exact.
A mask byte is exactly 0 (redacted/unavailable) or 1 (visible observed byte).
Every hidden or unused data byte is zero. Masking does not change the original
caller buffer. A zero data value with mask=1 is observed, not redacted.

| Offset | Type / bytes | Field |
| --- | --- | --- |
| 0 | bytes[8] | ASCII `W2NCAP01` |
| 8 | u32 | version=1 |
| 12 | u32 | block_bytes=1536 |
| 16 | u32 | header_bytes=512 |
| 20 | u32 | quality: 1 Valid, 2 Invalid, 3 Incomplete; 0 NoCapture is never a readable capture |
| 24 | u64 | issue_bits at capture/freeze (§8) |
| 32 | u32 | case_id=1/2 |
| 36 | u32 | reserved=0 |
| 40 | u64 | phase_id=1 |
| 48 | bytes[16] | run_id |
| 64 | u32 | cached actor PID |
| 68 | i32 | socket FD |
| 72 | u64 | generation=1 |
| 80 | u64 | call_id, actual global entry sequence |
| 88 | u64 | arm_entry_baseline |
| 96 | u64 | total_entries at real-call return |
| 104 | u64 | total_exits including this real return |
| 112 | u64 | window_entries at real-call return |
| 120 | u64 | window_exits including this real return |
| 128 | i32 | incoming recvmsg flags |
| 132 | i32 | returned native msg_flags; zero if unavailable |
| 136 | i32 | entry errno |
| 140 | i32 | real-call exit errno |
| 144 | i64 | real-call ssize_t return |
| 152 | u64 | original control capacity |
| 160 | u64 | returned native msg_controllen; zero if unavailable |
| 168 | u32 | captured control span bytes; 0..256 |
| 172 | u32 | captured payload span bytes; 0..256 |
| 176 | u64 | original iov count |
| 184 | u64 | original single iov capacity; zero if unsupported/unavailable |
| 192 | u64 | returned iov count; zero if unavailable |
| 200 | u64 | returned single iov capacity; zero if unavailable |
| 208 | u32 | equality mask: bit0 forwarded msghdr pointer, bit1 unchanged control pointer, bit2 unchanged iov pointer, bit3 unchanged iov_base, bit4 unchanged FD/flags/input lengths on forwarding; full required mask=31 |
| 212 | u32 | sanitizer: 1 Valid, 2 Invalid, 3 Unavailable |
| 216 | u32 | number of control mask bytes equal to 1 |
| 220 | u32 | number of payload mask bytes equal to 1 |
| 224 | u32 | first bad control-byte offset; UINT32_MAX if none or not applicable |
| 228 | u32 | complete verified cmsg headers counted; 0..16 |
| 232 | i32 | last unarmed intercepted FD, as Hello linkage |
| 236 | u32 | native_profile=1 |
| 240 | u64 | availability bits (§8) |
| 248–511 | bytes[264] | reserved=0 |
| 512–767 | bytes[256] | sanitized control memory in native byte order |
| 768–1023 | bytes[256] | control visibility mask |
| 1024–1279 | bytes[256] | complete observed fixed payload, or visible bounded partial observation |
| 1280–1535 | bytes[256] | payload visibility mask |

Quality Valid means the observer's capture/sanitization path is structurally
valid, **not** that the command is authentic, accepted, leak-free or production
ready. MSG_CTRUNC is expected in N2 and does not itself set an observer issue.
Live status issues after freezing still invalidate observation even with an
older Valid header.

A real error return is preserved as -1 and exit errno, with output flags/control/
iov fields unavailable (zero with availability bits clear), arrays, span/visibility
counts and header count zero, sanitizer Unavailable and quality Incomplete.
Availability is exactly bits 0,4,5 (=49); equality bits can attest only forwarded
pointer/arguments (bits 0,4 =17), with no claims about undefined returned buffers.
Original input metadata remains recorded where safe. If an instrumentation
violation also exists, Invalid quality takes precedence over Incomplete; no
Valid quality is possible on a real error. The availability mask still describes
what was actually recorded, not what a desired outcome would require. Do not inspect undefined
output fields or reuse an earlier Hello's data. A successfully returned excessive
length is recorded as its actual scalar but copied only within original bounds;
it sets the relevant issue and makes quality Invalid. If invalid pointer/shape
prevents safe copying, affected span/count/mask fields are zero, not guessed.

Control sanitization follows the main specification: copy only complete supported
header fields/data with checked offsets and mask padding. SCM_CREDENTIALS is
exactly 12 bytes, SCM_RIGHTS is a whole number of four-byte signed FD integers,
with no inferred partial integer. Unknown types, duplicate credentials, more
than two rights integers, negative rights or invalid headers make sanitizer
Invalid; retain only already-verified fields. Never close based on these raw
integers. A valid final length-20 header at offset 32 requires no final padding
beyond byte 51. The offline parser reconstructs cmsgs independently from mask-
approved native bytes, not from Python's tuples. Native header/data bytes remain
little-endian profile-1 values; wire header fields are separately encoded LE.

## 8. Bit definitions, unavailable data and consistency

Issue bits are u64, sticky and never clear. bit n means 1 shifted left by n.
Only the following bits are defined; all others must be zero.

| Bit | Name | Meaning |
| --- | --- | --- |
| 0 | Initialization | Resolver/constructor failed |
| 1 | UnsupportedProfile | ABI/provider/loader requirements unavailable |
| 2 | ControlMisuse | Invalid control API argument/state/range/generation |
| 3 | MultipleEntry | More than one armed-window entry or any post-capture entry |
| 4 | WrongFD | Armed entry FD differs from selected endpoint |
| 5 | Recursion | Exceptional observer re-entry; abort, no invented native return |
| 6 | InputShape | Unsupported/null original msghdr/iovec/buffer/length shape |
| 7 | PointerChanged | Returned pointer/iovec identity changed; unsafe spans not read |
| 8 | ControlOversize | Returned control length exceeds original/256 bound |
| 9 | PayloadOversize | Return exceeds original iov/256 capture bound |
| 10 | RealCallError | Native receive returned -1; preserve errno and stop |
| 11 | SanitizerInvalid | Malformed/unknown control data or invalid mask/layout |
| 12 | CounterOverflow | Saturating counter exhausted |
| 13 | OwnershipCorrupt | Exceptional observer-state ownership failure; abort |

Unavailable symbols/init mean no native call was captured; status/partial
initialization metadata must not be represented as a fabricated capture. No
capture represents a recursion/ownership abort that did not return.

Availability bits (u64 at capture offset 240) have these meanings:

| Bit | Meaning |
| --- | --- |
| 0 | Real call returned (success or error); result and exit errno recorded |
| 1 | Output msg_flags available from successful real return |
| 2 | Output msg_controllen available from successful real return |
| 3 | Output iovec identity/count fields safely observed |
| 4 | Entry errno recorded |
| 5 | Exit errno recorded |
| 6 | Full returned control span fits supported bounds and was copied privately |
| 7 | Full returned payload fits supported bounds and was copied privately |

Absent scalar values must be zero with their availability bit clear. Entry errno
and return fields are valid only for a captured real call; legitimate zero errno
is distinguished from missing data by these bits. Entry errno uses bit4; exit
errno uses bit5; ssize_t result uses bit0. No additional implicit sentinel exists.
A supported successful capture requires availability=255, equality=31, zero
issues and sanitizer Valid. Redacted control padding is compatible with bit6:
that bit describes private bounded copying, not public visibility of every byte.

For a sanitizer location error, first bad offset is within 0..captured control
span inclusive (the end boundary can identify a missing header/data byte).
Use UINT32_MAX for no control-location error; never reinterpret it as an index.

Cross-check counted visibility against mask arrays; counts cannot exceed spans;
mask bytes outside spans must be zero. Header count cannot require a data span
outside actual returned length. Zero-length rights data is Invalid for these
fixtures. A normal complete N1/N2 payload mask is 1 for the entire fixed frame
and 0 afterward; compare all visible bytes, length prefix and hash with the one
sender record. Source-level equality bits are self-reported instrumentation
checks, not independent evidence of kernel behavior. Wrapper/source/linkage
review and actual Hello/action interception remain required.

## 9. Export framing and evidence budget

ABI/status/provider functions return whole blocks, not chunks of internal state.
Python obtains one immutable local copy per trace barrier; capture uses three
512-byte reads at offsets 0/512/1024. All blocks use this exact JSON control-line
schema, with no additional or duplicate keys:

`kind`, `version`, `run`, `case`, `sample`, `block`, `generation`, `call`,
`total`, `offset`, `n`, `hex`.

kind is `w2n-block`; version=1; run is 32 lowercase hex characters for the 16-byte
run ID; case is integer 1/2. sample is the parent-assigned trace-barrier index
(nonnegative u32, at most 63), binding status samples to explicit barriers.
block is `abi`, `provider`, `status` or `capture`. generation and call are
canonical unsigned decimal **strings**, at most 20 digits, no leading zero
except `0`, avoiding downstream JSON integer precision loss. For capture they
equal its frozen header. For status they equal generation/last real-return call
in that status block. ABI/provider use `0`/`0` because their bytes predate arm. For pre-setup/failed-init
status, the binary run/case/phase fields are zero while the envelope uses the
parent's planned run/case. Once setup succeeds, binary run/case must match the
envelope exactly. This exception is limited to Unconfigured/InitFailed status,
never a frozen capture. Parent trace metadata identifies the provider/library
files; the observer block's path bytes are preserved as hex, not interpreted as
an arbitrary path the observer may open through this API.

Total bytes are 256/512/256/1536 respectively. offset is a multiple of 512;
n=min(512,total-offset), n>0; hex is exactly 2*n lowercase hex digits. ABI/status
have one 256-byte envelope, provider one 512-byte envelope, capture three 512-byte
envelopes at the same sample/call/generation. Every field is range/type checked;
booleans are not integers. A line including newline must be <=2048 bytes, which
fits the existing 4096-byte private control limit. Do not coalesce envelopes into
a larger control response. Per-case parent barrier count is <=64. This framing
is for trusted fixture evidence, not a new authenticated protocol.

Assemble by (run,case,sample,block,generation,call); require exact totals and
complete non-overlapping ranges, with one occurrence per expected range. Repeated
idempotent C read calls must not add duplicate persisted envelopes; no retries
are part of native schedules. Contradictory status/error records are preserved
as failure, never filtered out because a capture looked Valid. Hash the final
assembled sanitized capture externally; this is corruption detection, not a
MAC/authentication assertion. Original native padding is never exported or hashed
as if it were known kernel data.

Internal budget: 1536 capture + 512 private raw arrays + 256 ABI + 256 status +
512 provider + 512 bounded sanitizer/export scratch = **3584 bytes**, within
the 4096-byte capture arena. Separate scalar state is <=512 bytes; total observer
capture/state storage remains <=4608. Raw arrays are cleared before readable
frozen export. No hidden second raw record or variable-sized provider string.
This does not bound Python allocations, loader internals or total process RSS.

Saved report remains <=128 KiB across both cases, with at least 4 KiB reserved
for terminal overflow/outcome/ownership records. Bound encoded bytes before
append; omit an overflowing whole record, record Incomplete in the reserve and
stop. Fresh private roots/exclusive 0600 files and identity-checked cleanup stay
as in the main specification. File persistence failure makes evidence Incomplete;
never claim Complete from a transient record the parent did not preserve.

## 10. Consistency review and remaining gates

Documentation review found and resolved the following interface-level issues:

- No exported native structs: exact bytes/widths/offsets separate host ABI from
  wire encoding and avoid implicit ctypes pointer truncation or C padding.
- API OK is not capture/safety acceptance. freeze can export an invalid record;
  output statuses, quality, issues and outcome judgments remain distinct.
- Snapshot capture and sanitization are separate lifecycle transitions; raw
  storage cannot be read through chunk API before sanitization. Immutable read
  generation cannot hide a later live coverage issue.
- The existing Hello proves same-instance observation before one action arm;
  expected counts are checks on actual counters, never synthesized evidence.
- Failed calls expose no guessed output memory; exceptions/aborts may lose
  capture. No fallback syscall or inventory-based closure is introduced.
- The 52-byte final-unpadded header, masks, three capture chunks and total arena
  arithmetic fit all selected bounds. No case alters socket receive capacities.

**D1 is resolved at documentation level.** Exact signatures, statuses, lifecycle,
ctypes widths, byte offsets, masks and chunk framing are specified. This is not
implementation evidence. Future local checks must exercise the definitions,
unknown/reserved values, overflow/unaligned spans, partial headers/integers,
control misuse, result/errno preservation, generation/chunk corruption and
post-freeze status invalidation, without equating them to native verification.

Documentation QA checked complete, non-overlapping field coverage for the
256/256/512/1536-byte blocks, exact three-chunk coverage, arena arithmetic and
relative links. These are document checks, not local observer tests or native
experiments; no executable observer code exists from this task.

The unverified gates remain: existing toolchain/profile/provider feasibility;
observer source/linkage review for no hidden allocation/lazy binding/locks/I/O;
implementation/local-check correctness; actual healthy N1 interception before
N2; complete ownership cleanup and evidence persistence. No implementation or
execution permission is supplied by closing D1. If authorized later, the next
smallest unit is isolated observer and local checks only; N1/N2 remain deferred
until that implementation is reviewed and separately authorized.

W2m remains native M2 Fail, diagnostic_success=false and authentication safety
Unproven. W2h's counterexample, W2i–W2l's limits, B01–B06 and all outcome
separations remain unchanged. Implementation, experiments, all other W2/W3,
elevation, registration, package operations, build dispatch and release
preparation remain deferred. No publication or PR belongs to this task.
