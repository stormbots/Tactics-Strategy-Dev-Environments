# W2j: unprivileged Linux unexpected-descriptor rejection

Executed only the owner's separately authorized W2j scope: a healthy control and
one otherwise-valid credential-bearing request attaching one run-owned pipe
read descriptor with SCM_RIGHTS. No truncation, partial delivery, multi-FD or
flood schedule was executed. No production, elevation, registration, package,
workflow/build dispatch or release work occurred.

**Diagnostic success: true. Narrow primitive result: Pass. Authentication safety:
Unproven. Production readiness: false.** B01–B06 remain open. W2h's authentication
counterexample and W2i's limited record-credential feasibility result are preserved;
this experiment does not replace or expand their historical claims.

## Implementation and trust boundaries

`run_experiment.py` imports definitions from the reviewed W2i harness at baseline
`1fc228e`; neither its scenario runner nor its entrypoint executes. W2i files are
unchanged. Both source SHA-256 hashes are in [the report](evidence/linux-run.json).
This harness launches only its own server/client script in independent processes.

Each fresh 0700 private root contains a 0600 pathname AF_UNIX SOCK_SEQPACKET
listener. Listener and client SO_PASSCRED are set/verified before connect; accepted
state is verified before the first application-send barrier. Trusted private
control pipes enroll expected process instances out of band; both actors retain
pidfds and validate the initial credential exchange in both directions. No
payload PID or parent allow/deny decision substitutes for receiver checks.

Both action records contain the same fixed valid envelope shape, bound to that
case's attempt/original PID, with explicit valid own SCM_CREDENTIALS. The client
adds one owned pipe descriptor only in J2. The server receives no attachment
expectation or allow/deny bit: its real decision comes from the **unchanged**
W2i validator with the complete kernel-delivered ancillary list and retained
peer liveness. Only a receiver-local fixed integer can be incremented.

Before validation, instrumentation records installed FD metadata without opening
another descriptor. The validator rejects SCM_RIGHTS and closes delivered FDs.
Immediately afterward, before any directory open/listdir, receive, pipe creation
or other FD allocation, fstat and F_GETFD must each return EBADF for the received
number. Only then is the receiver inventory collected again. Kernel credentials
are recorded independently from the full ancillary list, because ancillary
rejection may stop the validator before its normal credential-result field is
populated. This diagnostic extraction does not authorize a command.

The receiver's before/after inventory records FD numbers, device/inode, mode,
F_GETFD and F_GETFL, detecting unexpected closures, replacements, leaks or flag
changes. The single-threaded snapshot excludes the directory handle already
closed by listdir, not a live actor descriptor. Sender pipe metadata is checked
before and after evaluation; fstat and F_GETFD/F_GETFL prove both original pipe
ends remain valid. No pipe data is read or written.

Bounds are unchanged from W2i: 16,384 record bytes including length prefix,
256 ancillary bytes, 4,096 private-control bytes and five-second per-operation
watchdogs. Mandatory MSG_CMSG_CLOEXEC is used on recvmsg. No sleep/stress average,
missing-credential fallback, alternate transport or disabled guard is used.

## Observed results

[Native run](evidence/linux-run.json): **J1 Pass / J2 Pass**, 38 ordered barrier
events, no unexpected native failures or cleanup fallback.

| Case | Native observation | Actions |
| --- | --- | --- |
| J1 healthy | Complete valid record, kernel credentials `[38541,1000,1000]`, no received FD, credential-verified fixed reply | 1 |
| J2 one unexpected pipe FD | Complete otherwise-valid record, kernel credentials `[38543,1000,1000]`; receiver rejects `unexpected ancillary/descriptor` | 0 |

J2 sender FD **5** and kernel-installed receiver FD **6** share device **12**, inode
**256854**, FIFO mode **4480**, and read-only F_GETFL **0**. Receiver F_GETFD **1**
confirms FD_CLOEXEC. Its FD 6 was absent from the receiver baseline and was closed
by validation: immediate fstat errno **9 / EBADF** and F_GETFD errno **9 / EBADF**.
Receiver inventory is identical before/after: **6 live descriptors**. Sender
original read/write descriptor metadata is unchanged. These are observed run
values, not hard-coded fixture identities or copied payload FD claims.

Received flags **1073741824** include the returned CLOEXEC flag and neither
MSG_TRUNC nor MSG_CTRUNC. Ancillary types/sizes, raw kernel credentials, payload
hash/match, actual syscall returns, pidfd state, instance metadata and ownership
are in the report. Truncation would stop this run, not become W2j coverage.

[Focused local checks](evidence/checks.txt): **17 pass** — 13 synthetic/mocked
validation and ordering checks plus 4 saved-native-evidence audits. These are not
17 native cases or native fault injections. They cover evidence corruption,
missing CLOEXEC/closure observations, inventory changes, identity mismatches,
healthy-failure versus counterexample classification, cleanup despite a metadata
observation error, and closure-before-inventory ordering.

## Environment, ownership and cleanup

Managed disposable Linux x86_64, kernel 6.18.44, glibc 2.41, Python 3.12.14;
UID/GID 1000 and zero observed capability sets. Actors are single-threaded with
unchanged PID/user namespaces and OS creation identities. Each is a direct
runner-owned child retained by pidfd; all four actors exited 0 and were reaped
through their Popen handles. Both private roots/socket entries were removed only
after actor completion and unchanged fixture identities were checked.

Runner FD inventory is identical before/after (three live standard descriptors,
including identities and flags). Subreaper state is **0 → 0**: no process setting
was changed, no descendants were spawned and no restoration action was needed.
No unknown process was discovered/signaled or claimed cleaned up. No automatic
proc-children enumeration or global unrelated-process cleanup claim is made.
The sender's pipe ends close in its finally block and the receiver attachment
closes before the immediate checks; normal actor exits additionally release all
remaining owned sockets and retained handles.

The native command used the tool's additional local socket/network permission,
as W2i required, while processes remained unprivileged. No sudo, host privilege
elevation, external network request, VM/container, package or service operation
was used. Runtime and source details are pinned in the report. This is not a
booted Mint desktop or Windows validation result.

## Stopping conditions and limits

A failed healthy control, unsupported prerequisite, unexpected send result,
credential ambiguity, truncation, descriptor identity/flag mismatch, failed
closure observation, inventory change, timeout, uncertain ownership/reaping or
cleanup failure stops dependent cases. Any observed unexpected J2 acceptance is
preserved as CounterexampleDetected even if another evidence check also fails.
Unknown/replaced fixture paths or uncertain actor completion prevent root removal.

This validates only one completely delivered descriptor on a small record. It
does not validate truncated ancillary lists, partial FD delivery, multiple rights,
resource exhaustion, saturation, hostile server writers, actual exec exclusion,
PID reuse, credential/namespace transitions or arbitrary native cleanup faults.
Those experiments remain deferred. Trusted fixture enrollment is not privileged
bootstrap or a protected root-owned namespace. Full capability/replay/consent,
Ready/close/install/recovery, Windows and desktop/service behavior are untested.
A local metadata-failure mock is not native error-path coverage. A clean finite
run does not establish general leak freedom or mutual authentication safety.

## Reproduction within separately authorized W2j scope

```sh
python tests/prototypes/manual-update-w2j/run_experiment.py /tmp/w2j-report.json
python -m unittest discover -s tests/prototypes/manual-update-w2j -p test_checks.py -v
```

The focused evidence audits read the checked-in report; they do not run actors.
Do not install dependencies or replace required primitives if preflight is blocked.
[SHA256SUMS](evidence/SHA256SUMS) pins source, checks, documentation and evidence,
including the unchanged W2i helper used by this harness.
