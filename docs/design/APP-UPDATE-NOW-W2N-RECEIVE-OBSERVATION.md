# #72 W2n receive-observation specification — reviewed draft revision 3

Status: specification with a separately authorized
[isolated observer/local-check implementation](../../tests/prototypes/manual-update-w2n/README.md).
**Native N1/N2 and actual preload execution have not run.** The earlier
specification/D1 reviews themselves were documentation only.
The separately granted local implementation authorization has been used only
for the linked isolated code/local checks. Native execution remains deferred.
This specification does not authorize rerunning W2m or any other experiment.
Review baseline: `51a038e`. See the [review disposition](APP-UPDATE-NOW-W2N-REVIEW.md)
for resolved design gaps and remaining validation gates. D1's exact interface
and record layout are now specified in the [ABI v1 addendum](APP-UPDATE-NOW-W2N-ABI.md),
which is normative for function signatures, wire values, offsets and lifecycle.
This supersedes revision 2's statement that those details were unspecified.

## 1. Question and preserved baseline

Why did W2m's fixed-capacity M2 action receive leave an additional live pipe FD
while Python returned no SCM_RIGHTS tuple? Observe that same receive boundary,
not a second receive or a different receiver implementation.

Published baseline: W2m `5e0a287`, reviewed at `1a29eea` on
`prototype/issue72-w1`. The [source review](../../tests/prototypes/manual-update-w2m/SOURCE-REVIEW.md)
and [original native report](../../tests/prototypes/manual-update-w2m/evidence/linux-run.json)
remain immutable evidence. M2 received all 53 payload bytes with MSG_CTRUNC,
no MSG_TRUNC, valid raw credentials and zero authorized actions, but its receiver
inventory grew from six to seven. Returned tuples exposed no rights integer,
so the validator closed zero descriptors. Both M2 actors required forced owned
cleanup. W2m diagnostic_success=false, native M2=Fail, authentication
safety=Unproven, production readiness=false. W2n must never rewrite those results.

Reviewed upstream Linux/CPython and local libc source predict a valid rights
header fits in the 52-byte layout. The actual native control memory, returned
control length and running-build provenance were not captured. Missing final
padding alone is not an established explanation. W2n seeks a narrower boundary
observation, not a generic kernel/runtime vulnerability finding.

## 2. Scope and noninterference contract

Propose a separate test-only directory `tests/prototypes/manual-update-w2n/`,
containing an observer shared library, diagnostic orchestration, offline record
checker and documentation. Preserve W2m and its W2i helper byte-for-byte. The
future diagnostic may copy W2m actor orchestration to add observer setup,
arming and evidence export; it must retain the same action frame, transport,
credential/pidfd guards, validator and action counter. Name the diagnostic cases
N1/N2, but retain wire fixture attempts M1/M2 for direct comparison.

Use a receive-symbol interposer loaded **only into each owned server actor** via
an explicit child environment, not the runner, sender, installed SDE or a system
configuration. It must observe the installed Python socket path's actual libc
`recvmsg` invocation and call the resolved next implementation. No ctypes/raw
syscall receiver, ptrace, BPF, alternate recvmsg entrypoint, additional receive,
modified Python build or automatic fallback belongs to this proposal.

Behavior preservation is a contract to review and check, not a claim of timing
invisibility. Preloading and capture necessarily add code, memory and execution
time and can change reproduction. The resulting evidence applies to this
instrumented run; failure to reproduce does not disprove W2m.

For every intercepted call:

- Forward the identical socket FD, msghdr pointer, incoming field values and
  flags to the resolved next function exactly once. Never add retries.
- Never initialize, zero, repair or modify the caller's control/payload buffers,
  iovec, socket options or msghdr. In particular do not round 52 up to 56.
- Preserve the exact returned ssize_t and the `errno` observed immediately after
  the forwarded call, including an opaque/stale errno after success. Observer
  work must not overwrite it. Record success/error separately; successful errno
  is not required to be zero.
- No allocation/free, file/socket open/close, logging I/O, environment lookup,
  symbol resolution, Python callback, sleep, lock acquisition or FD metadata
  syscall inside the receive wrapper. Snapshot work uses preallocated storage
  and bounded memory copies only. Keep the same return path for real-call
  failures. Preservation applies only to the supported, valid-instrumentation
  path; the exceptional observer-failure rule below must not be called preserved
  native behavior.
- Never act on a descriptor number found in a payload, raw snapshot or inventory.
  The existing validator alone processes Python-returned SCM_RIGHTS. The
  observer is not an additional cleanup or authorization mechanism.

Resolution, entry and errno rules:

- Complete symbol resolution and TLS warming before declaring the actor ready;
  do not resolve lazily on the first observed call. A resolution/initialization
  failure ends that owned actor before admission, rather than returning a fake
  recvmsg failure. No action receive is permitted in that state.
- Single-threaded actors must have no asynchronous handler that calls recvmsg or
  accesses observer state; no thread/async-signal safety claim is made. Review
  generated code and linkage for TLS/PLT/IFUNC helpers that might allocate or
  resolve lazily. If warming/provider inspection cannot support that constraint,
  classify the observer unsupported; do not silently weaken it.
- At entry save caller errno, perform only validated bounded preparation, then
  restore entry errno immediately before the real call. Save real-call errno
  immediately on return; restore it after all snapshot bookkeeping. Forward
  failures exactly, without interpreting stale success errno as a syscall error.
- An already-resolved observer that detects recursion or corrupted ownership
  must mark the run invalid and fail-stop its owned actor using a fixed process
  termination path. This exceptional termination is an allowed diagnostic abort,
  **not** exactly-once forwarding or preserved behavior. It is never an observed
  recvmsg result. Do not fabricate errno/return values, recurse indefinitely or
  continue N1/N2. Parent-held process handles account for the exit. A snapshot
  lost on this path is Incomplete, never Complete.

No production changes, application builds, package operations, privileged work,
registration, workflows, signing or release work are included.

## 3. Environment and prerequisites

Use a disposable managed Linux x86-64, little-endian LP64 process environment,
unprivileged UID/GID, single-threaded actors and zero effective capabilities.
Record real/effective/saved IDs, all capability sets, process start identities,
PID/user namespaces, OS/kernel/Python/libc descriptions and executable identities.
Do not certify Windows or booted Mint/service/desktop behavior from this host.

Require existing compiler/linker, installed headers, dynamic-loader facilities,
Python socket/ctypes support, /proc identity/FD inspection, pidfds, SOCK_SEQPACKET,
SO_PASSCRED, SCM_CREDENTIALS/RIGHTS and MSG_CMSG_CLOEXEC. Record native ABI sizes,
field offsets, alignment, CMSG_LEN/SPACE outputs and Python's corresponding
values; they must agree, including the fixed partial capacity 52. If not, stop
Blocked before N1. Do not install tools, elevate, change namespaces, create a
container or substitute mechanisms.

Record compiler invocation/version, observer source/binary hash, Python
executable and loaded `_socket`/libc file identities/hashes, and observer/symbol
provider paths/build IDs where available. Resolve the next recvmsg before
arming, record its actual loaded provider and require it be the intended libc
provider, not merely any address outside the observer. Reject an unexplained
interposer chain. Do not disable platform mediation/security or replace inherited
loader settings to force an acceptable provider; report unsupported coverage.
File hashes and build IDs identify artifacts, not their exact source or integrity
against an attacker with same-process modification privileges. Record
unavailable source/build provenance as Unknown; version strings or upstream tags
must not be treated as exact running-source attestation. Unknown provenance
limits causal attribution even if boundary observation succeeds.

Preloading supported by the actual process is a prerequisite, not an assumption.
An ignored preload, alternate symbol path or unverified target is Blocked before
native action schedules; no alternative instrumentation is automatically allowed.

## 4. Observer lifecycle and coverage verification

The future observer exports only fixed test setup/status/arm/snapshot functions.
They expose evidence, not executable commands, transaction capabilities or
expected acceptance bits. Captured kernel credentials are diagnostic evidence.
There is no arbitrary-path logging API. Python loads the already-preloaded
observer by its verified identity; a second independent library instance is not
acceptable. Exported status identifies the library instance and its storage.
Use the exact ctypes argtypes/restype and C signatures in the ABI v1 addendum;
default integer/pointer conversions are not acceptable. The fixed operations are
setup, ABI query, provider query, status, arm, freeze and capture read; no extra
control export is authorized by ABI v1.

The fixed interface has no generic memory-read or executor operation:

| Operation | Contract |
| --- | --- |
| Setup/status | Return bounded version/ABI/provider/instance data and saturating entry/exit/error counters; no recvmsg and no state reset. Initialization happens once before ready. |
| Arm | Accept only the selected socket FD and expected existing entry count; bind them to the already-established run/case/phase from setup. Reject rearm, malformed input, stale count or wrong state. No expected result, capacity override or attachment parameter. |
| Snapshot metadata / freeze | status supplies bounded lifecycle/size information. After the allowed pipeline stages, freeze sanitizes into the immutable 1536-byte record; OK means export available, not safe/valid. Before call completion freeze returns NotReady without polling. |
| Snapshot chunk | Copy exactly 512 bytes from offsets 0, 512 or 1024 of frozen generation 1, using a declared 512-byte caller buffer. Reject every other range/generation; never return internal pointers. All chunks bind to the same run/case/call. |

The in-process caller is trusted test Python, not a hostile-pointer C API. Setup
loads must prove their instance equals the interposed instance: a fixture-only
caller token set through the control interface must appear with its generation
in the actual wrapper's capture/status. Resolving a matching filename or querying
a second loaded copy alone is insufficient. The token cannot influence receive
acceptance.

1. Resolve and warm symbol/TLS/setup operations before the actor reports ready.
   Fail initialization explicitly if resolution/ABI checks fail. Do not silently
   claim observation while only forwarding calls.
2. Complete the normal credential Hello/reply while unarmed. Status must show
   an intercepted server Hello receive, no action capture and the expected
   process/library instance. This checks actual Python-path interception without
   adding a probe request. No extra native self-test schedule is authorized.
3. Before the action send, arm exactly once for the already accepted socket FD,
   verified by the diagnostic's descriptor identity, and a fixed run/case/phase
   identifier. Save the global entry count as the call-window start. Arming
   records identity; it cannot configure the expected receive result.
4. Record exactly one matching receive invocation in that arm window. A second
   entry, recursion, unexpected FD, missed entry, error/retry or saturated counter
   makes coverage invalid. Do not rearm, overwrite the first record or hide a
   retry. Ordinary invalid-shape/counter observations are recorded without
   changing the real call; recursive/corrupted observer entry uses the explicit
   exceptional abort rule, never a claimed forwarding success.
5. After Python's original validator and immediate-close checks, and after its
   receiver after-inventory, export the snapshot/status through the fixed setup
   interface. No snapshot retrieval/allocation occurs between validation and
   immediate EBADF checks. Export is non-consuming local memory access, not a new
   probe. The parent compares call counts and identities. The freeze operation
   sanitizes and fixes the record before the first chunk is exported; post-capture status may add a separate coverage-error
   indicator, never rewrite the captured bytes or counters.

Seeing a loaded library alone does not prove interception. N1 requires successful
call capture, intact credential data and agreement with Python's observation.
Status-query calls do not themselves invoke recvmsg. Counters and phase IDs must
show the captured call is the action, not Hello, a reply, or a control read.

## 5. Capture format, bounds and storage

Per server process, reserve at most **4096 bytes** for the capture arena plus
at most **512 bytes** of scalar state, for a maximum **4608 bytes** of observer
capture/state storage per server. The arena contains the immutable **1536-byte**
serialized capture, raw/sanitized arrays, masks, fixed query blocks and bounded
scratch; the ABI addendum accounts for 3584 bytes within this 4096-byte ceiling.
It is not 4096 bytes per copy. This does not bound
Python, loader or total process memory. No ring growth or overwrite. The record
contains:

- Format version, run/case/phase identifier, process identity token, arm sequence,
  entry/exit counts, call ID and observer status flags. Parent-held OS creation
  identities bind the token to the process; the token alone is not authentication.
- Socket FD, incoming flags and msghdr input lengths. Record pointer/field
  equality checks privately as needed to verify argument forwarding; publish
  identity tokens/equality results rather than unrelated address-space data.
- Incoming control capacity, returned native msg_controllen, returned msg_flags,
  ssize_t result and post-call errno. Distinguish native from Python values.
- A bounded snapshot of the returned control memory (maximum **256 bytes**) and
  the complete fixed action payload (maximum **256 bytes**). Normal socket
  payload capacity stays **16,384**, not 256. The action fixture is much smaller;
  an unexpected larger result makes capture incomplete and stops the diagnostic.
- Input/output iovec lengths and counts and control-pointer consistency. The
  supported fixture has one payload iovec; other shapes are unsupported.

Supported memory contract: the caller is the verified test Python socket path,
not arbitrary native code. A single existing readable msghdr and iovec must own
buffers whose lifetimes extend through return. Record original control pointer,
iovec pointer/count, iov_base and capacity before forwarding. Only the original
buffers may be copied, and only after successful return with unchanged pointer /
iovec identity and supported lengths. A bounds check does not prove pointer
readability; unknown caller memory, thread mutation, async mutation or an invalid
shape cannot be made safe by guessing. Do not install a SIGSEGV recovery handler.
A crash yields Incomplete and owned cleanup, not a repaired record.

Save input capacity/pointers before forwarding. On success copy no more than
min(returned control length, original capacity, 256); do not trust an excessive
returned length to expand memory access. An excessive value is a recorded
invalid observation and a stop condition. If the control pointer unexpectedly
changes, do not dereference the replacement. On a negative return, record errno
and scalars but do not inspect undefined output memory or infer FD delivery.
Payload copying is separately capped by the nonnegative return value, original
iovec capacity and 256-byte capture bound, with overflow-safe conversions. A
returned payload size above either allowed bound is invalid; never trust an
output iovec length to authorize copying. An input capacity above the supported
256-byte ancillary bound is recorded as unsupported without inspecting that
buffer. No pre-call read of the uninitialized control buffer is allowed.

Native control padding can contain uninitialized bytes. Keep the bounded raw
memory snapshot only in the static private actor record. After the original
validator, immediate-close checks and after-inventory, perform redaction within
the observer's fixed storage **before any chunk API exposes bytes**. Do not send
unredacted storage through ctypes/Python and rely on later publication filtering.
Use one checked, allocation-free sanitizing pass over known field offsets:

- Accept only in-range, complete headers with supported ABI sizes. Read fields
  through bounded copies, not unaligned struct-pointer casts; check additions
  and alignment rounding for overflow before advancing.
- Preserve only identified header fields and complete data bytes for known
  SOL_SOCKET SCM_CREDENTIALS (12 bytes) / SCM_RIGHTS (whole native int values).
  Mask alignment/struct padding, unused bytes and unknown control data. Preserve
  a byte-level visibility mask; zero-filled evidence is explicitly Redacted,
  not alleged syscall output. Unknown types or malformed/incomplete data make
  the observation Invalid and stop; expose at most already-verified fields.
- A final cmsg may end at CMSG_LEN without its trailing CMSG_SPACE padding.
  Missing trailing padding is not by itself a malformed header. Do not invent
  a next header beyond the returned/control-capacity bound.
- Raw `msg_controllen` remains separately recorded. It does not guarantee all
  padding/unused bytes were kernel-written. Raw storage is inaccessible through
  exports and is cleared after sanitized generation is frozen; clearing touches
  observer storage only, not Python's original control buffer.

An independent offline parser of the sanitized export checks header offsets,
lengths, mask consistency, native integer layout and data spans. It cannot use
Python's tuple list, the actor's parsed list or libc CMSG_NXTHDR as its sole
oracle. Report mask-approved cmsg fields, credential tuples and complete FD
integers, with unknown/redacted regions explicit. Two parsers are not independent
native executions and cannot recover hidden bytes; capture/redaction correctness
remains an instrumentation obligation. Neither parser closes FDs or authorizes
action. Never accept a mask that hides known header/data inconsistencies.

Keep setup/status/capture exports bounded so each existing private control line
remains at most **4096 bytes**. The 1536-byte frozen native snapshot is retrieved in three exact 512-byte
chunks, with run/case/call/generation, sample index, offset and total length; no
unbounded base64/hex line or dynamic queue. Chunk retrieval must be repeatable
and immutable, not trigger another capture. Verify all expected ranges are
present exactly once, non-overlapping and at the same generation/size; reject
missing/duplicate/foreign chunks rather than silently filling gaps. Set total
saved W2n report size to
at most **128 KiB** across both cases. Reserve at least **4 KiB** of that budget
for terminal outcome/overflow/ownership reporting; do not fill the whole budget
and then lose the failure reason. Before a size-limited record is appended,
check its encoded size. On overflow omit that whole record, mark evidence
Incomplete in the reserved terminal record, and stop. Never silently truncate
and report completion. Store in fresh run-owned 0700 roots, with 0600 evidence
files created exclusively without following links. Separate preserved evidence
from ephemeral socket/observer-build roots. No real capabilities or secrets are
used or published.

## 6. Two schedules and barriers

Exactly one N1 and, only if N1 passes, one N2. No stress loop, capacity scan,
automatic retry, uninstrumented rerun or additional native negative control.

Common order:

1. Observer initialized; actor ownership and ABI verified; listener/client options
   recorded before connect. Complete trusted enrollment and Hello/reply with
   both credential directions, retained pidfds and interception counters.
2. N2 only: sender creates one run-owned pipe; record both endpoint identities,
   access modes and descriptor settings. Receiver creates no transfer pipe.
3. Arm the server observer for its accepted endpoint. Obtain armed status before
   permitting the sender. Capture fresh sender/receiver baselines, with observer
   setup already complete so it cannot masquerade as an FD inventory change.
4. Sender submits one complete explicit-credential action. Capture actual send
   result, credential request, payload hash and attachments. Parent then permits
   evaluation; no sleep establishes ordering.
5. The observer surrounds that receive. Python returns its normal tuple, runs
   the unchanged validator and action logic, immediately checks any enumerated
   FD closures, and captures its receiver after-inventory. Export the immutable
   native record before evaluating evidence pass/fail relationships. Diagnostic
   orchestration needs a fixed finalization path that attempts only memory export
   even when the original Python receive/validation path raises. It must preserve
   the original exception and any already-observed acceptance/effect, not replace
   them with an export error. Do not rerun receive, repeat validation, open a new
   FD inventory or query sender status on that path. If capture/closure/inventory
   stages were not reached, report them Not collected and observation Incomplete.
   Dead/crashed actors may make an in-memory snapshot unrecoverable; do not
   promise evidence survival across process death or add an out-of-scope logger.
6. Parent correlates the evidence. On any stop condition, take no new probe or
   sender-status observation; preserve the already captured record and perform
   owned cleanup. Missing later observations remain explicitly Not collected.
   If no stop condition occurs, obtain sender post-receive validity and final
   actor-instance observations, then orderly stop/reap and remove fixtures.

| Case | Wire fixture / capacities | Required healthy or diagnostic observation |
| --- | --- | --- |
| N1 healthy | M1 action, no rights, payload 16,384 / ancillary 256 | Exactly one captured receive; complete fixed payload; matching native/Python credentials, flags and result; no truncation; one fixed action; stable inventories and orderly cleanup. |
| N2 fixed M2 shape | M2 action, explicit own credentials plus both pipe ends; payload 16,384 / ancillary CMSG_SPACE(sizeof(ucred)) + CMSG_LEN(sizeof(int)) = 52 | Exactly one captured receive, complete payload and actual MSG_CTRUNC without MSG_TRUNC; zero authorized actions and truncation-specific rejection. Preserve actual native headers, Python tuples, descriptor lifecycle and any inventory mismatch. |

Do not require a desired rights-header layout to manufacture N2 completion.
Well-bounded differing native metadata is the subject of the diagnostic; malformed,
ambiguous or uncorrelated data is an invalid observation, not a passing explanation.

## 7. Correlation and independent outcome fields

Bind all observations to run, server process start identity, arm/call ID,
accepted socket FD/device/inode, sender instance, one sent request and the fixed
canonical payload hash. A second consumed record invalidates correlation.
Compare native result/flags/control span with Python result/flags/tuple bytes;
compare native complete FD integers with Python-exposed integers and independently
observed new FIFO descriptors matching the sender's dev/inode/access flags.
Descriptor numbers are process-local; do not compare sender and receiver numbers
as object identity. Preserve unique typed before/after inventories without
silently collapsing duplicates. Never infer a missing descriptor integer from
payload identity or guess it from a header fragment.

Report separate fields, not a combined pass count:

| Field | Meaning |
| --- | --- |
| `observation_result` | Complete / Blocked / Invalid / Incomplete: was the same-call capture verified, bounded, correlated and preserved? |
| `metadata_relation` | NativeRightsPresentPythonAbsent / NativeRightsAbsentInventoryAdded / NativePythonAgree / OtherBoundedOutcome / Unknown. These describe observations, not blame or root cause. |
| `cleanup_result` | Pass / Fail / Unproven for immediate closure and stable receiver inventory. Forced process teardown never upgrades this field. |
| `authorization_result` | N1 expected one action; N2 expected zero. Preserve any N2 acceptance/effect as CounterexampleDetected even if other evidence fails. |
| `ownership_cleanup_result` | Accounted / Incomplete: explicit actor reaping, fixture disposition and unchanged settings, including forced cleanup. |
| `authentication_safety` | Unproven, or CounterexampleDetected for an observed unauthorized action; never Safe because this diagnostic completes. |
| `production_readiness` | Always false. |

N1 must meet every healthy requirement to admit N2. N2 observation_result can be
Complete with cleanup_result=Fail when its captured, correlated leak reproduces
and owned teardown is fully accounted. This is diagnostic evidence completion,
not primitive safety success. Observation Complete requires valid coverage,
full bounded correlation and preserved required records; successful owned
teardown is reported separately and is additionally required before declaring
the overall diagnostic session accounted. Observation Complete can coexist with
ownership_cleanup_result=Incomplete, but then overall session completion is false.
A partial native snapshot may remain useful with observation Invalid/Incomplete;
never discard it just because a later integrity or cleanup check fails.
If the metadata agrees and immediate FD closure
passes, record non-reproduction in the instrumented run; W2m remains Fail.

Native rights data present but Python data absent localizes the discrepancy to
after the recorded forwarding boundary, subject to observer verification. If the
native export contains no rights header while a later inventory gains a
matching live FD, the discrepancy spans that boundary and the later inventory;
it does **not** prove when the FD was installed, since no independent inventory
was taken at the exact forwarding return. Record this as a relation requiring
further attribution, not proof of a kernel-side cause. Neither proves exact
kernel/libc/interpreter causation or eliminates instrumentation effects. Missing provenance remains a stated limitation.

## 8. Cleanup, restoration and stop rules

Retain the reviewed ownership model: two direct actors per case, trusted
out-of-band identities, pidfds, known Popen handles, single-threaded operation
and no descendants. Only registered owned handles may be signaled; a still
unreaped direct child may use the reviewed fallback if pidfd setup failed.
Record wait result/PID, exit code, reaped state and forced flag. Never signal
unknown processes or delete unrelated/replaced paths.

The observer must not close FDs missing from Python's tuples. No inventory-based
cleanup patch is allowed. A reproduced live extra FD ends only through accounted
actor teardown in this gate; retain Fail for immediate closure. No process/host
setting should change. Record runner inventories/subreaper before/after and
explicitly account for any temporary observer/build handles. Remove ephemeral
roots only after known-actor completion and root/socket/build identities match;
keep bounded evidence under its separately owned evidence root. Refuse uncertain
cleanup and report retained locations instead of broad deletion.

Stop before N1 on unavailable primitives, compiler, ABI, trusted symbol/provider
verification or preload support; classify Blocked. Stop N2 admission on any N1
failure, missed coverage or non-normal healthy cleanup. During either case stop
on observer recursion/overflow/multiple entries, unexpected input shape,
forwarding mismatch, failed/short send or receive, missing correlation, MSG_TRUNC,
absent required N2 MSG_CTRUNC, malformed/oversized control metadata, identity or
ownership change, deadline/resource violation, unauthorized action or incomplete
evidence/cleanup. Use the existing five-second test-only per-operation watchdog,
with no retries or production-timeout claim. The observer itself does not call a
clock or implement a new timer in the receive wrapper; bounded code is reviewed
and the parent owns deadline enforcement. A parent timeout enters owned cleanup;
if the actor must die before exporting, record observation Incomplete.

A reproduced N2 inventory mismatch is a terminal **anticipated diagnostic
finding**, not permission to continue probing. Preserve its already captured
native/Python record, classify cleanup Fail, and enter owned teardown immediately.
Other well-bounded metadata differences are classified once, not used to retune
or rerun. Any uncertainty keeps the relevant outcome Unproven/Incomplete.

## 9. Review gate and later QA proposal

Before implementation authorization, review feasibility of actual symbol
interception, instance identity, errno/argument preservation, single-call
coverage, memory bounds, padding redaction, chunked export, snapshot survival
through stopped evidence handling and cleanup without changing W2m semantics.
Do not implement around an unresolved item by silently changing the receiver.

If later authorized, local synthetic/mocked checks should cover malformed
headers/length overflow, partial integers, redaction masks, duplicate/foreign call
IDs, chunk loss, multiple entries, missing interception, errno/result forwarding,
rejection/cleanup distinction and preserved counterexamples. Label these local
checks separately from N1/N2 native evidence. Compilation of an isolated observer
would be part of that later experiment authorization, not an application build.
No compile, local test suite or experiment belongs to this review step.

## 10. Remaining gates before authorization and execution

This revision resolves design ambiguities; it does not supply empirical
feasibility. A later authorization must distinguish implementing the observer
and local checks from admitting native N1/N2. Implementation must not automatically
proceed to native schedules when a gate is still unmet.

| Gate | Current evidence / required disposition |
| --- | --- |
| Documentation / interface gate | D1 resolved in the reviewed ABI v1 addendum: exact C/ctypes signatures, statuses, lifecycle, fixed blocks/offsets, masks, chunk framing and resource accounting. This is a specification decision, not empirical implementation or native evidence. |
| Toolchain / provider feasibility | Subsequent local checks use the existing compiler and measure its header ABI. Actual intended-libc provider, preloading and same-instance interception through Hello remain unverified; otherwise Blocked, not an alternate receiver. |
| Observer implementation review | Isolated code is now built and locally reviewed; the compiled wrapper has one indirect target call and exceptional exit paths. Independent review remains next. No actual loader/provider path has run; mocks cannot prove native interception. |
| Memory/export integrity | Local mocks/fixtures cover pointer/length changes, unpadded headers, overflow, unsupported controls, masks, chunks, bounded reporting and immutable export. This is not native descriptor cleanup or integrated actor evidence. |
| Failure/ownership handling | Mocked local abort/error branches are checked. Stop-aware native actor/export/persistence/ownership integration is not implemented or run. Crash snapshot loss stays explicit; no native fault injection is added. |
| Native observation | Not run. N1 must meet all healthy conditions before N2. Capturing N2 is not a repair or permission for another diagnostic. Authentication safety and production readiness stay unproven/false. |

Recommendation: publish the reviewed documentation if requested. D1 is closed
at documentation level; no additional interface decision is deferred to code.
The isolated observer/local checks now exist under separate user authorization;
the next step is independent review of that code and evidence. Authorize N1/N2
only after that review and explicit acceptance of remaining native prerequisites.
Closing D1 did not itself check runtime/provider feasibility.

W2h's counterexample, W2i–W2l's limited results and W2m's stopped cleanup failure
remain unchanged. B01–B06 remain open. All other W2/W3, production implementation,
elevation, registration, package operations, build dispatch and release
preparation remain deferred. No GitHub publication or PR belongs to this draft.
