# W2l: unprivileged Linux credential-only ancillary truncation

Executed only the owner's separately authorized W2l scope: a healthy control and
one complete valid credential-bearing record received with normal payload
capacity and an explicitly test-only zero-byte ancillary buffer. **No descriptors
are attached.** Descriptor partial-delivery experiments and all other W2/W3,
production, elevation, registration, package, build and release work remain deferred.

**Diagnostic success: true. Narrow primitive result: Pass. Authentication safety:
Unproven. Production readiness: false.** B01–B06 remain open. W2h remains an
authentication counterexample; W2i–W2k retain their limited historical scope.

## Implementation and authority boundary

The standalone runner/actors derive from reviewed W2k `9d3c2fb`, with the action
receive limit changed only for L2's ancillary buffer. Definitions from unchanged
reviewed W2i `1fc228e` supply the actual validator, credential checks, process
identity/pidfd helpers and owned-child cleanup. Previous experiment entrypoints
and schedules never run. No W2i/W2j/W2k files are modified. Both source/helper
hashes are recorded in [the native report](evidence/linux-run.json).

Two independent direct child actors use a real pathname AF_UNIX SOCK_SEQPACKET
listener in a fresh 0700 root with a 0600 socket. SO_PASSCRED is enabled/verified
before connect/first application sends. Trusted private control pipes enroll
expected process instances out of band; both peers retain pidfds and validate the
initial credential exchange in both directions using normal receive capacities.
Private controls establish barriers; they never supply a receiver allow/deny bit.

The sender constructs one complete fixed envelope and submits explicit own
SCM_CREDENTIALS in sendmsg. It has **no SCM_RIGHTS send path**, accepts no
attachment selector, creates no transfer pipe and cannot attach an FD. The
ordinary Popen control pipes are test plumbing, not data-message attachments.
Status observations record empty transfer-FD inventories. Defensive receive-side
unexpected-FD observation/cleanup remains available, but is not exercised by this
credential-only run and cannot be claimed as additional FD cleanup coverage.

L1's action receive uses 16,384 payload bytes and 256 ancillary bytes. L2 keeps
16,384 payload bytes and uses **zero ancillary bytes**. Both retain recvmsg's
mandatory MSG_CMSG_CLOEXEC argument, fixed bounded schema, 4,096-byte private
control lines and five-second test-only per-operation watchdogs. This zero-byte
buffer is test instrumentation, not a proposed production default. No sleep or
stress average establishes ordering.

The **unchanged** validator receives actual bytes, ancillary items and flags.
Only its acceptance can increment the fixed server-local integer. The complete
payload, claimed PID, old Hello credentials, connection identity and retained
peer liveness cannot replace missing per-record kernel credentials. Local checks
also show that removing MSG_CTRUNC in synthetic input still rejects the complete
payload for missing credentials; this is not an extra native schedule.

## Native observations

[Native report](evidence/linux-run.json): **L1 Pass / L2 Pass**, 37 ordered barrier
events, no unexpected native failures or cleanup fallback.

| Case | Sent / received | Kernel receive observations | Actions |
| --- | --- | --- | --- |
| L1 healthy | 53 / 53 payload bytes | Ancillary capacity 256; one 12-byte SCM_CREDENTIALS item `[42133,1000,1000]`; accepted fixed record and credential-verified reply | 1 |
| L2 zero ancillary buffer | 53 / 53 payload bytes | Ancillary capacity 0; actual flags 1073741832 include MSG_CTRUNC and exclude MSG_TRUNC; ancillary list empty | 0 |

Both receives use normal payload capacity 16,384 and preserve the complete
four-byte prefix (declared JSON length 49) and canonical full-payload hash.
L2's unchanged validator returns `accepted=false`, reason
`truncated record/control`, no credential result and zero delivered-FD closures.
The raw ancillary/credential lists and installed/closed-descriptor observations
are empty, as required. L1 flags are 1073741824 (no truncation). These are observed
run-specific values; flags are never supplied by the runner or synthesized as
native evidence.

L2's payload match proves only the controlled fixture's complete data arrived.
**It does not authenticate that record's sender.** Its actual per-record kernel
credentials are unavailable at the receiver, so the record remains rejected.
The sender's independently observed identity and requested own credentials are
diagnostic fixture evidence, not a replacement for the missing kernel item.
Successful earlier Hello authentication does not authorize this later command.

The receiver's before/after inventories are identical at six live descriptors,
including identities and flags. Runner inventories likewise match at three
standard descriptors. Inventories keep the scandir handle live, exclude exactly
one matching directory identity, and fail on vanished baseline entries. No
transferred descriptor is installed, probed, closed or inferred discarded.
Consequently this run says nothing about kernel-discarded/partially delivered
rights cleanup or general descriptor leak freedom.

## Local QA and evidence limits

[Focused checks](evidence/checks.txt): **22 pass** — 18 local synthetic/mocked
checks and 4 saved-native-evidence audits. They cover complete fixture/hash and
length evidence, actual-flag requirements, buffer capacities, absence of delivered
credentials/rights, rejection reason, integer counts, stable inventories, exact
guard arguments, sender control shape, stop-after-failed-healthy behavior, peer
readiness/enrollment and post-observation ordering. A synthetic unexpected
acceptance is classified CounterexampleDetected; failed healthy control is not.

These are not 22 native schedules or native fault injections. No fake/omitted
credential guard runs natively. No unexpected native failure occurred. All
native observations are pinned to the source/helper hashes; artifact hashes are
in [SHA256SUMS](evidence/SHA256SUMS).

## Environment, ownership, cleanup and unchanged settings

Recorded environment: managed disposable Linux x86_64, kernel 6.18.44,
glibc 2.41, Python 3.12.14, UID/GID 1000 and zero observed capability sets.
Both actors in each case are single-threaded, share the runner's fixed PID/user
namespace context, and retain their OS creation identities. Four direct child
actors exit 0 and are reaped through their known Popen handles. Retained pidfds
and independent post-evaluation identity/liveness observations are recorded.

Both private roots/socket entries are removed after known-actor completion and
unchanged fixture-identity checks. No forced cleanup signal is needed. Runner
FD metadata and subreaper state remain identical before/after, **0→0** for the
latter; no process/host setting is changed and no restoration action is needed.
No descendants are spawned or unknown actors signaled. No global unrelated-process
cleanup guarantee is claimed.

The native command uses tool-level additional local socket permission without
sudo, host privilege elevation, external network requests, dependency installation,
VM/container creation or task/service registration. This is not booted Mint,
Windows, protected root-owned namespace or privileged bootstrap validation.

## Stop rules and remaining gaps

Stop dependent cases on failed healthy control, missing primitives, unexpected
send/receive shape, absent MSG_CTRUNC in L2, any MSG_TRUNC, unexpected ancillary
items/descriptors, payload mismatch, changed identities/counters/inventories,
watchdog or uncertain ownership/reaping/cleanup. Preserve any L2 authorization as
a counterexample even if another evidence audit also fails. Do not fabricate
flags, reduce payload capacity, attach rights, reuse cached credentials or accept
the payload's claimed PID to manufacture a pass. Unknown/replaced fixture paths
or uncertain actor completion prevent root removal.

This tests complete payload delivery with the entire credential item unavailable,
not partial control parsing or partial FD delivery. Multiple rights, descriptor
partial delivery, resource exhaustion/saturation, hostile server writers, native
cleanup/crash faults, exec exclusion, PID reuse, and credential/namespace changes
remain unvalidated. Trusted fixture enrollment is not production privileged
enrollment. Full capabilities/replay/consent/Ready/close/install/recovery,
compatibility migration, Windows and desktop/service behavior remain unresolved.
Diagnostic completion and a finite primitive pass are not mutual authentication
safety, integrated updater proof or production readiness.

## Reproduction within separately authorized W2l scope

```sh
python tests/prototypes/manual-update-w2l/run_experiment.py /tmp/w2l-report.json
python -m unittest discover -s tests/prototypes/manual-update-w2l -p test_checks.py -v
```

Evidence audits read the checked-in report and do not run actors. Missing
prerequisites do not authorize installation, elevation or substitution of the
required mechanism. No publication or PR belongs to this execution.
