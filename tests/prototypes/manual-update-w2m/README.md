# W2m: unprivileged Linux ancillary-truncation partial-descriptor diagnostic

**Stopped on an unexpected outcome. Native acceptance criteria NOT met.**
Diagnostic success: **false**. Primitive result: **Incomplete/Fail/Blocked**
(the executed M2 case is **Fail**, not an unavailable-prerequisite Blocked result).
Authentication safety: **Unproven**. Production readiness: **false**.

W2h remains an authentication counterexample; W2i–W2l retain their limited
historical results. All B01–B06 remain open. This failed diagnostic found an
FD-cleanup/inventory counterexample in the test transport path, **not an
unauthorized-action or original-process-authorship counterexample**.

## Authorized scope and implementation

Only the owner's W2m authorization was used: M1 healthy control and M2 one
complete valid credential-bearing record attaching both ends of one run-owned
pipe. The harness derives from reviewed W2l `2b39c58` and imports definitions only
from unchanged reviewed W2i `1fc228e`. No earlier experiment entrypoint runs.
Earlier experiments, shared helpers and production files are unchanged.

The two direct child actors are single-threaded and unprivileged. They use a
pathname AF_UNIX SOCK_SEQPACKET listener in a fresh 0700 root with a 0600 socket.
SO_PASSCRED is enabled before connection and checked on the accepted endpoint;
the sender also checks it before the action send. Private bounded control pipes
supply trusted fixture enrollment and explicit barriers. Each peer retains a
non-inheritable pidfd; initial Hello/reply credentials are checked in both
directions. Trusted test enrollment is not production privileged enrollment.

M1 uses normal capacities, no transfer pipe and no descriptor attachment. M2
creates exactly one pipe and sends both of its ends with explicit own
SCM_CREDENTIALS in one complete sendmsg. Payload capacity stays 16,384 bytes.
Only M2's action ancillary capacity changes to the fixed test-only formula:

`CMSG_SPACE(sizeof(ucred)) + CMSG_LEN(sizeof(int))`

Here `sizeof(ucred)=12`, `sizeof(int)=4`, CMSG_SPACE(12)=32 and CMSG_LEN(4)=20,
giving **52 bytes**. Normal ancillary capacity remains 256 for M1, Hello and
replies. Every receive preserves mandatory MSG_CMSG_CLOEXEC. Private controls
are bounded at 4096 bytes, the watchdog is five seconds per operation, and the
only authorized effect is incrementing a server-local integer. There is no
capacity scan, retry, transport substitution, package command or GUI operation.

The unchanged validator receives the actual returned bytes, ancillary tuples
and flags. It inventories returned SCM_RIGHTS integers before rejecting
truncation and closes those enumerated descriptors in its finally block. The
receiver records metadata before validation and checks closure immediately
afterward, before inventory allocation can reuse FD numbers. The parent audits
observations; it cannot tell the validator to authorize a request.

## Preserved native observations and failure

[Native report](evidence/linux-run.json) contains **33 barrier events** across
exactly two schedules. The harness source and shared-helper hashes are recorded.

| Observation | M1 | M2 |
| --- | --- | --- |
| Payload sent / received | 53 / 53 bytes | 53 / 53 bytes |
| Action ancillary capacity | 256 | 52 |
| Actual returned flags | 1073741824 | 1073741832: MSG_CTRUNC, no MSG_TRUNC |
| Returned kernel credentials | `[43802,1000,1000]` | `[43804,1000,1000]` |
| Returned SCM_RIGHTS tuples | None | **None, despite an additional pipe FD in inventory** |
| Authorized actions | 1 | 0 |
| Validator result | Accepted | Rejected: `truncated record/control` |
| Receiver inventory | Six unchanged FDs | Six → seven FDs |
| Case result | Pass | **Fail: `receiver FD inventory changed`** |

M2's sender owns pipe descriptors 5 and 6. Both identify device 12/inode 292069,
with read/write access modes respectively. The sender's complete canonical
payload and successful 53-byte send are recorded. The receiver's returned
ancillary list contains only one 12-byte credential item (raw bytes are saved).
It does not contain an SCM_RIGHTS tuple or descriptor integer.

Nevertheless, the receiver's after-inventory contains a new FD 6, device
12/inode 292069, FIFO mode, read-only flags and FD_CLOEXEC. All six baseline
entries retain their identities/flags. This is evidence of one live received pipe
FD matching the sender's read end, independently of the returned ancillary list.
There is no receiver-side transfer-pipe creation operation in this schedule.

The report's `installed` field inventories only FD integers enumerated from
Python's returned SCM_RIGHTS tuples. Its empty list therefore **does not mean
that no descriptor was installed**. Here `installed=[]`,
`immediately_closed=[]` and `delivered_fds_closed=0` coexist with the extra live
pipe FD. The unchanged validator had no returned descriptor integer to close.
Immediate closure is **not established**, and stable receiver inventory **fails**.
Raw recvmsg syscall control memory is not captured; the cause/location of the
lost descriptor metadata across kernel/runtime boundaries is not established.
Do not assert a general Linux or CPython defect from this one observation.

The full payload hash matches, and both actual truncation and rejection are
recorded. Returned kernel credentials remain diagnostic metadata: truncation
prevents credential authority, and the validator returns no accepted credentials.
There is no unsafe accepted action. The sender's post-evaluation descriptor
validity, later instance observations and normal shutdown acknowledgements were
**not collected**, because the inventory stop condition fired first. Pre-send
and at-send metadata must not be described as post-receive validity evidence.

## Stop, cleanup and environment evidence

No unexpected-outcome retry was attempted. The capacity and mechanism were not
tuned or replaced. No further native schedule or fault injection ran. The failed
native command exited 1 and its original report remains unchanged.

Managed disposable Linux x86_64, kernel 6.18.44/glibc 2.41, Python 3.12.14,
UID/GID 1000 and all recorded capability sets zero. The command required the
tool's additional local socket permission; it did not use sudo, host elevation,
external network requests, a VM/container, dependency installation or services.
This does not certify booted Mint, Windows or privileged bootstrap behavior.

All four direct child actors were reaped through their known Popen ownership
handles. M1 actors exited zero normally. M2's two still-live owned actors required
pidfd-directed SIGTERM and exited -15; both cleanup records explicitly say
`forced=true`. Both private roots/socket entries were removed after actor
completion and fixture identity checks. No unrelated process was signaled.

Runner FD metadata is unchanged before/after and subreaper remains **0→0**;
no setting was modified or needs restoration. Actor exit ends the remaining
process-owned FD lifetime, but it does not supply the missing immediate
in-process closure/EBADF proof. No unknown-process cleanup guarantee is claimed.

## Local QA is separate from native acceptance

[Focused checks](evidence/checks.txt): **29 pass** — 23 synthetic/mocked checks
and six saved-native-evidence audits. They do not report 29 native schedules.
[Pre-native checks](evidence/pre-native-checks.txt) preserve the initial 23 local
passes with saved-evidence checks skipped until a report existed.

Local checks cover the unchanged formula, complete send/payload, actual-flag and
capacity requirements, one-of-two descriptor expectations, credentials/ancillary
shape, atomic CLOEXEC, immediate closure, pipe identity, stable inventories,
strict integer counts, truncation-specific rejection, counterexample
classification, exact sendmsg/recvmsg arguments, guard forwarding,
cleanup-before-inventory ordering and stopping after failed healthy control.
Mocked descriptor numbers never reach a real close operation.

Saved-report audits intentionally require the **observed failure**, empty
returned-rights metadata alongside the additional live pipe FD, zero M2 actions,
forced M2 cleanup and missing post-stop observations. Passing these audits means
the failure is faithfully preserved; it does not turn M2 into a native pass.
The production validator, receive capacity and transport were not changed after
the native failure. All artifacts are covered by [SHA256SUMS](evidence/SHA256SUMS).

## Remaining gaps and next gate

Immediate closure and stable receiver inventories are not validated for this
partial-delivery shape. Post-receive sender descriptor validity was not reached.
The discrepancy between FD installation and returned ancillary metadata needs
source/evidence review before proposing any separately authorized diagnostic.
Do not rerun this native case, tune capacity, replace the mechanism or implement
a cleanup workaround as an implicit follow-up to this stopped run.

General descriptor leak freedom, kernel-discarded-rights handling, larger/multiple
rights, saturation/resource exhaustion, native crash/cleanup faults, reverse
hostile writers, exec/PID reuse, credential/namespace changes, protected
enrollment, real capabilities/replay/consent/Ready/close grants, durable intent,
installer handoff/recovery, migration and Windows remain unvalidated. W2m neither
repairs W2h nor proves the complete record-based candidate safe.

All other W2/W3, production implementation, elevation, registration, package
operations, build dispatch and release preparation remain deferred. No GitHub
publication or PR belongs to this step. Native execution has stopped; the next
action is review of the failure and limitations, not another experiment.
