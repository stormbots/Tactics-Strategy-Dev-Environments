# #72 W2c: unresolved-intent startup guard

Executed only the separately authorized unprivileged Linux W2c experiment.
This is a test-only startup surrogate and intent fixture, not an SDE feature,
production journal format or recovery implementation. All other W2/W3, elevation,
registration, production implementation, package operations, workflows, builds
and releases remain deferred. B01–B06 remain open.

## Run

```bash
python3 tests/prototypes/manual-update-w2c/run_experiment.py > work/w2c-results.json
python3 -m unittest discover -s tests/prototypes/manual-update-w2c -p test_checks.py -v
```

Create `work/` first. Requires unprivileged Linux with Python standard library,
pidfds/pidfd signaling, process-local child-subreaper support, readable `/proc`
identity metadata, local flock support and a writable temporary root. The runner
must initially have no children and no effective capabilities. No installation,
network, privileged prompt or new VM/container is required.

The implementation imports definitions only from the reviewed W2b test helper;
it never runs W2b scenarios or production modules. That dependency is included in
the source-hash evidence. Existing W1/W2a/W2b code and evidence are unchanged.

## Recorded native schedule

[Machine-readable evidence](evidence/linux-run.json): **Pass**, with 23 ordered
trace events and the following three observed decisions:

| Phase | Observed result | Additional native observation |
| --- | --- | --- |
| Healthy, no intent/supervisor | NormalSession; A-shared → S-shared → release A | Startup retains S at its exit barrier; an independent exclusive S probe is rejected |
| Supervisor terminated; sentinel survives without inherited lock descriptors | RecoveryRequired; no normal session, no S attempt, no retained locks | Independent runner acquires O/A/S before rejection; another probe can acquire all three while the rejected actor waits to exit |
| Sentinel exits normally; same intent remains | RecoveryRequired again | No automatic clearance or success; another lock probe succeeds while rejection remains in force |

The supervisor first acquires O/A/S exclusively, then publishes the fixture before
starting the fixed sentinel. An initial independent O probe is busy. The runner
terminates only its registered supervisor using a bound pidfd, verifies the
sentinel's original PID/UID/creation identity and adoption PPID, and checks it
remains alive before and after the child-survival startup attempt. Actual sentinel
regular-descriptor inventory contains none of the lock inodes. Probes use separate
open file descriptions in the independent runner and close them after observation.

Each startup actor is a separate process, bound to a pidfd and checked for UID
and capabilities. It checks intent while holding A shared, then checks again after
obtaining S shared before allowing a healthy session. The unresolved cases take
the first rejection path. This run does not exercise concurrent publication
between the two checks; no race-coverage claim is made for that path.

## Test-only fixture and publication

The private 0700 `PROTOTYPE-W2c-*` root contains three 0600 O/A/S files and a 0600
intent.json with four explicit fields: fixture=W2c-only, schema=1, transaction=
that temporary root's name, and state=unresolved. This is not a proposed production
schema and contains no secrets or arbitrary commands/paths.

The supervisor records successful calls in this order:

1. Exclusive creation of intent.tmp with mode 0600.
2. Complete write of the fixture bytes.
3. fsync of the temporary file.
4. Replace into intent.json.
5. fsync of the parent directory.

The parent independently observes the fixture and preserves its inode metadata,
body and SHA-256 through all subsequent decisions. Every probe/startup completion
rechecks lock identities and the unresolved fixture. An existing intent is never
overwritten by publication. Invalid/unreadable fixtures fail closed in the test
surrogate; duplicate keys, unsupported/boolean schemas, unknown fields, oversize
content, malformed JSON and dangling symlinks cannot be interpreted as absence.

The filesystem is tmpfs. These successful calls and process-loss observations
**do not establish disk durability, power-loss behavior or the production write
protocol**. There is no installer or filesystem mutation by the sentinel.

## Ownership, environment, failures and cleanup

Recorded environment: managed Debian GNU/Linux 13, Linux 6.18.44, Python 3.12.14,
UID/EUID 1000, zero effective capabilities, tmpfs temporary storage. Stacked mount
entries are recorded rather than selecting one flag set. No booted Mint or
Windows desktop was used.

The report binds W2c's two Python files and its W2b helper by SHA-256. It records
UTC/relative timestamps, kernel identities, pidfd ownership, actor privileges,
publication calls, fixture/lock identities, decisions, probe outcomes and exits.
Trusted test pipes are not production authenticated IPC. Reads/writes use the
reviewed helper's message bounds and diagnostic watchdogs.

**Failures:** none in the recorded native run. Expected contention and
RecoveryRequired are successful test outcomes, not failures. There was no fallback
cleanup. The [five focused checks](evidence/local-checks.txt) cover absence, repeated
inspection/publication refusal, malformed/unsupported/boolean/oversize fixtures,
duplicate fields and dangling symlinks. They are fixture checks, not five further
native process-loss schedules.

**Cleanup:** three startup actors exited 0; the supervisor exited by intended
SIGTERM (-15); the adopted sentinel exited 0 and was reaped. No direct children
remained. The original subreaper bit was restored from 1 to 0. Lock identities and
intent content/identity remained unchanged until all actors exited. The trace
explicitly labels final fixture deletion as **test teardown, not recovery**.
Only then were the known files and private directory removed; absence was checked
separately. No application recovery decision cleared the fixture.

Failure cleanup signals only registered pidfds, records fallback as failure, and
preserves roots when process completion or inventory is uncertain. An unregistered
adopted child may be reaped after control EOF but is not signaled on a bare PID.
Exceptional startup/cleanup failures were not injected in this native schedule.

## Coverage limits

One controlled same-UID cooperating-process schedule on this Linux/tmpfs host.
No concurrent journal-publication race, exhaustive interleavings, hostile peer,
privileged ownership/ACL, production parser, actual installer child, package-state
reconciliation, recovery clearance, reboot/power-loss, service/cgroup lifetime,
Windows/Mint desktop or accessibility validation occurred. Unit fixture checks
are not a security proof for production receipts.

W2c establishes that this surrogate can reject startup on an unchanged unresolved
fixture even though locks are free and the sentinel later exits. It does not prove
that real SDE startup does so, or that real installation is quiescent. All six
blockers remain open and later native/integration work needs its own scope.
