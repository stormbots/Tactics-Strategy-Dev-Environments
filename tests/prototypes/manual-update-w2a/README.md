# #72 W2a: unprivileged Linux cross-process lock experiment

**Executed scope: the authorized W2a subset only.** Real Linux `flock` operations
with three separate, unprivileged Python processes against fresh prototype files.
This is narrow L2 primitive evidence, not completion of W2, B06, or native updater
validation. Remaining W2/W3, elevation, registration, production implementation,
package operations, workflows, build dispatch and releases remain deferred.

## Run and environment requirements

```bash
python3 tests/prototypes/manual-update-w2a/run_experiment.py > work/w2a-results.json
```

Create `work/` first. Requires Linux, Python standard library, `/proc`, an
unprivileged UID with zero effective capabilities, writable private temporary
storage, `flock` support and permission to start child processes. Root/non-Linux
runs report Blocked. Unsupported primitive/process/storage operations fail with
recorded details rather than silently substituting an in-memory test. No package
installation, network access or external command is used by the experiment.

The runner creates a random `PROTOTYPE-W2a-*` directory with mode 0700 and exactly
three empty 0600 lock files, O/A/S. It never opens SDE objects or accepts an
arbitrary root/action command from a user. Workers use multiprocessing **spawn**
and open their own descriptors; the parent never opens a lock-bearing descriptor
for them to inherit. Interprocess messages are trusted test plumbing, not an
implementation or test of authenticated production IPC.

## Schedules and recorded results

[Machine-readable run](evidence/linux-run.json) records **Pass: five checks**:

| Schedule | Expected and observed result |
| --- | --- |
| Existing GUI enters A shared → S shared → releases A; updater takes O exclusive → A exclusive | Updater S exclusive attempt returns busy while GUI retains S shared |
| Peer attempts GUI admission while updater owns A exclusive | Admission rejected; S not attempted and no lock retained |
| Existing GUI releases S | Updater acquires S while retaining O/A; competing O exclusive attempt returns busy |
| Run-owned updater surrogate is terminated before any native mutation or intent | Exit by SIGTERM observed; peer acquires O/A/S on the same unchanged files |
| Positive admission control after updater exit and peer releases | A shared/S shared admission succeeds, drops A, retains S and then releases S |

All lock acquisitions are nonblocking. Parent-controlled request/reply barriers
establish order; no sleep or stress-run average is used as evidence. Five-second
response/join watchdogs detect a stuck test and are not protocol deadlines.
Every reply checks the lock-file device/inode/owner/mode/size inventory. Checks
fail immediately on unexpected acquisition or identity change. Only the run-owned
surrogate may be terminated; no real installer, descendant or uncertain intent
exists in this experiment. Cleanup may terminate only its own test actors if
needed and marks such fallback a failure.

## Environment, traces, failures and cleanup

Recorded final run: managed Debian GNU/Linux 13 runtime, Linux kernel 6.18.44,
Python 3.12.14, UID/EUID 1000, zero effective capabilities, `/tmp` tmpfs. This is
not a booted Mint desktop or Windows machine. No additional container or VM was
created. The disposable boundary is the private test root and its run-owned
processes inside the managed test environment.

The report includes source SHA-256, UTC start, relative monotonic barrier times,
actor PIDs/credentials, all 49 trace events, expected-check results, failures,
initial/final lock-file identities and cleanup outcomes. Mountinfo exposes stacked
`/tmp` entries with differing flags; both are recorded rather than claiming a
single selected mount. Actual creation, locking and deletion succeeded.

**Failures:** none in the recorded final run. Busy/admission-denied outcomes are
expected contention observations, not hidden failures. A metadata-review rerun
added private-root verification and all matching mount entries; it did not change
the lock schedule. No deliberately defective actor was run in W2a.

**Cleanup:** GUI and peer exited 0; the intentionally terminated updater exited
-15. All three actors were joined and not alive. No cleanup fallback was needed.
The three lock-file identities remained unchanged until every actor exited; the
private temporary directory was then removed and absence verified. Source hash,
report inventory and cleanup assertions were checked separately after the run.

## Evidence limits and next boundary

This covers only cooperating same-UID processes and one controlled interleaving
on this kernel/filesystem. It shows observed exclusion and kernel release on
surrogate process exit, not arbitrary race freedom, fairness, deadlines, or
protection from a malicious same-UID process that unlinks/replaces lock objects.
The admission rejection depends on the GUI surrogate honoring the A-before-S rule;
Linux does not prevent an unsupported legacy client from ignoring A.

No IPC authentication, polkit/UAC/SYSTEM, service lifetime, desktop logout/suspend,
clock mapping, package hooks, durable intent/receipt, surviving installer child,
legacy upgrade, installed SDE or accessibility behavior was exercised. There is
no claim about production lock-object compatibility. W1's fault ledger remains
historical; this evidence does not relabel all its native cases Pass. B01–B06
remain open. Review this result and define any next native slice before executing
remaining W2/W3 work.
