# W2k: unprivileged Linux payload truncation with one attached FD

Executed only the separately authorized W2k scope: a healthy control and one
complete valid record carrying one owned pipe descriptor, received with an
explicitly test-only eight-byte payload buffer. Ancillary capacity stays 256
bytes. No ancillary-truncation or partial-delivery experiment was executed.
No production, elevation, registration, package, build or release work occurred.

**Diagnostic success: true. Narrow primitive result: Pass. Authentication safety:
Unproven. Production readiness: false.** B01–B06 stay open. W2h's authentication
counterexample and W2i/W2j's limited results remain unchanged.

## Scope and implementation

The standalone actor/runner derives from reviewed W2j `c19be5d`, with the K2
payload receive limit and corresponding evidence assertions added. It imports
only definitions from unchanged reviewed W2i `1fc228e`; previous experiment
entrypoints and schedules never run. The W2i validator, credential and liveness
guards, framing limit and cleanup are unchanged. W2j files are unchanged.
Source and helper hashes are pinned in [the reviewed native report](evidence/reviewed-linux-run.json).

Two independent direct child actors use private control pipes for trusted
out-of-band process enrollment and named barriers. Both retain pidfds and
validate the initial credential exchange in both directions. The actual data
endpoint is a pathname AF_UNIX SOCK_SEQPACKET socket in a fresh 0700 root with
0600 socket permissions. SO_PASSCRED is verified before connect/first sends.
recvmsg always uses MSG_CMSG_CLOEXEC; no silent transport or credential fallback
is permitted.

The client submits one complete fixed JSON envelope in one sendmsg, with explicit
valid own SCM_CREDENTIALS. K2 adds one run-owned pipe read descriptor through
SCM_RIGHTS. Hashes independently bind the complete sent fixture, record length,
length prefix and received eight-byte prefix to the enrolled PID and case. The
sender submits 53 bytes; it does not deliberately send a malformed eight-byte
message. Only a receiver-local integer counter can change.

K1 uses the normal 16,384-byte payload capacity. K2 changes **only** the action
receive's payload capacity to eight bytes; both retain 256 ancillary bytes,
4,096 private-control bytes and five-second per-operation diagnostic watchdogs.
The eight-byte limit is test instrumentation, not a proposed production setting.
Hello/reply exchanges retain their normal receive bounds.

The receiver applies the unchanged validator to actual received bytes, ancillary
items and flags. It increments its counter only on that validator's acceptance;
there is no runner-supplied allow/deny decision. Before validation, instrumentation
records installed FD metadata without opening another FD. Validation must reject
for `truncated record/control`, not merely `unexpected ancillary/descriptor`.
Immediate fstat and F_GETFD probes must return EBADF before a directory open,
pipe creation, second receive or other FD allocation could reuse the number.
Only afterward is the receiver inventory collected again. No suffix is read,
reassembled or promoted to a new command.

## Final native observations

[Reviewed native report](evidence/reviewed-linux-run.json): **K1 Pass / K2 Pass**, 38 ordered barrier
events, no unexpected native or cleanup failures.

| Case | Sent / received | Actual flags and decision | Actions |
| --- | --- | --- | --- |
| K1 healthy, no attachment | 53 / 53 bytes; credentials `[40892,1000,1000]` | Flags 1073741824; complete record accepted, fixed reply credential-verified | 1 |
| K2 one attached pipe FD | 53 / 8 bytes; credentials `[40894,1000,1000]`; declared JSON length 49 | Flags 1073741856: MSG_TRUNC present, MSG_CTRUNC absent; truncation-specific rejection | 0 |

Both K2 ancillary items arrive completely: one 12-byte credential item and one
4-byte single-FD rights item. The sender's original read FD 5 and installed
receiver FD 6 share device 12, inode 272588, FIFO mode 4480 and read-only flags 0.
Receiver F_GETFD is 1 (CLOEXEC) before validation. The validator closes exactly
one delivered FD; immediate fstat and F_GETFD both return errno 9 / EBADF.
Receiver inventories match at six live descriptors, including identities and
flags. Both original sender pipe ends remain valid with unchanged metadata.
These are observed run-specific values, not constants used to fake observations.

The validator's credential-result list is empty in K2 because its truncation
check rejects before ordinary credential dispatch. The instrumentation separately
records the actual complete kernel credential item and retained-peer liveness.
That diagnostic extraction is not authentication acceptance or an allowed effect.
The eight-byte prefix is not sufficient for server-side full-body validation;
the controlled sender's pinned source and canonical full-fixture hash establish
what this experiment submitted. No general statement about arbitrary unseen
suffixes follows.

[Reviewed focused checks](evidence/review-checks.txt): **33 pass** — the original
28 local validation, integrity and saved-report checks plus 5 review checks with
multiple corruption subcases. These are not 33 native schedules or native fault
injections. The suite includes missing MSG_TRUNC, synthetic MSG_CTRUNC rejection,
wrong capacities/prefixes, malformed fixture evidence, wrong rejection reasons,
FD closure/inventory evidence, metadata-observation cleanup and closure ordering.
No native ancillary truncation is exercised by synthetic flag tests.

The [original native report](evidence/linux-run.json) and
[28-check output](evidence/checks.txt) are preserved unchanged as baseline evidence
at `ac63314`; their source hash identifies that baseline, not the reviewed source.
The reviewed report independently pins the current source and unchanged W2i helper.
No unexpected native failure was observed in the affected review rerun.

## Environment, ownership, cleanup and unchanged settings

Managed disposable Linux x86_64, kernel 6.18.44, glibc 2.41, Python 3.12.14,
UID/GID 1000 and zero observed capability sets. Both actors in each case are
single-threaded, in the runner's unchanged PID/user namespaces, and retained at
their observed OS creation identities. This is not a booted Mint desktop,
Windows, privileged peer or protected root-owned endpoint validation.

The command used tool-level additional local socket permission, without sudo,
host privilege elevation, external network requests, dependency installation,
VM/container creation or service operations. Runtime identities are in the report.

All four direct actors exited 0 and were reaped via their Popen handles. No forced
cleanup signal was needed. Both private roots/socket entries were removed only
after known-actor completion and fixture identity checks. Runner FD inventories
are identical before/after (three standard descriptors with matching metadata).
Subreaper state remains 0→0; no runner or host setting was changed and no
restoration action was necessary. No descendants are spawned, unknown processes
signaled or global unrelated-process cleanup guarantees claimed.

Inventory observations keep scandir's directory handle live, exclude exactly one
matching directory identity and fail on vanished baseline descriptors. They do
not silently discard unknown EBADF entries. The sender pipe closes in its finally
block; remaining owned sockets/pidfds close at normal actor shutdown.

## Stopping conditions and remaining gaps

Stop dependent cases on failed healthy control, missing primitives, unexpected
send/flags, MSG_CTRUNC, wrong ancillary count/size, absent kernel credentials,
changed ownership/namespace, missing CLOEXEC, incorrect truncation reason,
closure failure, FD inventory change, watchdog, uncertain reaping or cleanup.
Preserve any K2 acceptance as CounterexampleDetected even if another audit also
fails. Never substitute mocked flags, shrink ancillary capacity, inject additional
FDs or replace the transport to manufacture a pass. Preserve unknown/replaced
paths or uncertain actor-completion roots for investigation.

This validates one small record, eight received payload bytes and one completely
delivered FD. It does not validate ancillary truncation, partial FD delivery,
multiple rights, saturation/resource exhaustion, hostile server writers, actual
exec exclusion, PID reuse or credential/namespace transitions. Cleanup fault
checks are mocked; arbitrary native crash/unkillable-actor behavior is untested.
Trusted fixture enrollment is not privileged bootstrap or production namespace
security. Full capabilities/replay/consent/Ready/close/install/recovery,
compatibility migration, Windows and desktop/service behavior remain unresolved.
A diagnostic completion or finite primitive pass does not establish general
leak freedom, mutual authentication safety or production readiness.

## Implementation/evidence review

Review baseline: `ac63314`. Changes are confined to W2k and its evidence ledger.
The production updater, W2i helper and W2j files are unchanged.

| Finding | Correction | Coverage |
| --- | --- | --- |
| Float capacities/lengths and a float flag argument could compare equal to integer evidence | Require serialized nonnegative integers for receive sizes, flags, capacities, prefix length, sender size and validator fields | Local corrupted evidence; same two native schedules |
| Validator flags/byte count were not tied to the raw receive | Require exact raw/validator flag and length agreement | Local corrupted evidence; native K2 still rejects actual MSG_TRUNC |
| The recorded receiver baseline did not have to show zero prior activity | Require matching server identity and integer zero action/request counts before the send | Local corrupted saved evidence |
| Final retained-instance observations could be moved before evaluation while preserving the old required barrier order | Require both post-instance barriers after sender-after | Local reordered evidence; original process code already observed them afterward |
| Receiver metadata could name a different accepted socket or inventory object | Bind receiver descriptor to the accepted endpoint and require its device/inode in both inventories | Local corrupted evidence |
| MSG_TRUNC/MSG_CTRUNC availability was not an explicit preflight prerequisite | Check both constants before actors start | Code correction; missing-constant native injection not performed |

[Five tests against the baseline](evidence/review-regressions-before-fixes.txt)
produce **14 failed assertions**. These are synthetic/mocked evidence-validation
findings, not native authentication counterexamples or released-app defects. The
synthetic fixtures now use serialized integer flags, matching the control-pipe
JSON representation; no native flags are normalized or substituted. The reviewed
suite passes 33 checks. The native rerun remains K1/K2 = 1/0 with actual MSG_TRUNC,
no MSG_CTRUNC, one installed CLOEXEC FD immediately closed, unchanged inventories,
38 events, normal reaping and unchanged settings.

No new authentication counterexample appeared. Diagnostic success and the narrow
primitive pass remain distinct from unproven authentication safety. All B01–B06
remain open. This review adds no ancillary-truncation/partial-delivery, native
fault-injection, privileged or production validation.

## Reproduction within separately authorized W2k scope

```sh
python tests/prototypes/manual-update-w2k/run_experiment.py /tmp/w2k-report.json
python -m unittest discover -s tests/prototypes/manual-update-w2k -p test_checks.py -v
```

Evidence audits read the checked-in report; they do not run native actors.
[SHA256SUMS](evidence/SHA256SUMS) pins source, checks, documentation, evidence and
the unchanged W2i helper. All other W2/W3, production implementation, elevation,
registration, package operations, build dispatch and release preparation remain
deferred. No PR or publication belongs to this step.
