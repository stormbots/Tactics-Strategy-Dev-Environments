# #72 W2g: enrolled-client exit with a surviving connected-socket holder

Only the separately authorized unprivileged Linux W2g experiment ran. This is a
pre-commit authority surrogate: an authorized action is one in-memory test counter,
not an update, policy change, GUI close, installer launch or package operation.
All other W2/W3, elevation, registration, production implementation, workflows,
build dispatch and release preparation remain deferred. B01–B06 remain open.

## Run and requirements

```bash
mkdir -p work
python3 -I tests/prototypes/manual-update-w2g/run_experiment.py > work/w2g-run.json
python3 -I tests/prototypes/manual-update-w2g/test_checks.py
```

Requires Linux AF_UNIX/SO_PEERCRED, pidfd_open/pidfd signaling, readable process
creation metadata, child-subreaper support, Python standard library, private
writable temporary storage and an unprivileged account with zero effective
capabilities. The runner must initially be child-free. Local socket sandbox
permission is needed; no external network is contacted and no packages are
installed. No VM/container or desktop is created. The disposable boundary is
run-owned processes and fresh private temporary roots in the managed environment.

Preflight inability is reported with a Blocked reason. Once a case starts, an
unexpected error is Fail and dependent cases stop. Five-second watchdogs are
per-operation diagnostics, not production handshake/drain/install deadlines.

## Actors, enrollment and barriers

Each fresh 0700 `PROTOTYPE-W2g-*` root contains one 0600 pathname socket. The
server binds its own AF_UNIX stream listener; an independent client creates the
connection. Both mutually authenticate against process instances enrolled by the
runner's trusted control pipes, using kernel SO_PEERCRED and creation/liveness
checks. The server additionally binds and retains a non-inheritable pidfd for the
original enrolled client until evaluation and shutdown. Endpoint metadata, kernel
credentials and initial process creation samples are recorded.

The client then execs a fixed holder actor with `close_fds=True` and explicitly
passes only its connected socket and a separate trusted holder-control endpoint.
Its connected descriptor is non-inheritable by default; explicit `pass_fds`
clears close-on-exec in the holder. Matching fstat device/inode/type/owner records
establish that client and holder retain the same endpoint. The holder's initial
PID/parent/UID/GID/creation identity is independently bound to a runner-held pidfd.
The tested credential endpoint is not a parent-created socketpair; the socketpair
is trusted harness control plumbing only.

In loss cases the original client exits normally, closing its descriptor without
waiting for the holder. The runner verifies exit with its own pidfd and Popen
wait, and confirms holder adoption and liveness before and after the request.
The runner temporarily enables its own child-subreaper bit and restores its prior
value after every case has completed or failed. No service/system policy changes.

Named control barriers establish authentication, holder readiness, client exit,
holder survival, request sending, evaluation and reaping. There are no timed
sleep/stress assumptions. The server receives the same evaluation command in
each case, without a parent allow/deny bit. Its guard compares kernel credentials
to the enrolled client and checks the retained original-client pidfd at request
evaluation. A payload PID cannot choose the identity to be checked.

## Native evidence

[evidence/linux-run.json](evidence/linux-run.json) records 61 ordered trace events
and source SHA-256 hashes for both W2g Python files plus unchanged W2f/W2b helper
modules, imported for definitions only. No earlier scenario executes.

| Case | Actual request sender | SO_PEERCRED at server | Original client pidfd | Authorized actions | Result |
| --- | --- | --- | --- | --- | --- |
| Healthy | Enrolled original client | Original client PID/UID/GID | Live | 1 | Pass |
| Client exits, socket survives | Adopted holder | Still original client PID/UID/GID | Exited | 0 | Pass: original-client-exited |
| TEST-ONLY omitted liveness | Adopted holder | Still original client PID/UID/GID | Exited | 1 | Detected: stale-peer authorization |

Every case actually sends and receives one fixed test request. Both loss-case
requests claim the original client's PID, while independent holder control and
creation records identify the actual sender. The negative control omits only
the liveness condition; kernel identity and fixed-request checks remain. Its
unsafe test action is an expected detected counterexample, never a safe protocol
pass. Overall success requires exactly Pass / Pass / Detected.

The independent oracle checks initial mutual authentication and creation proof,
original-client liveness before/after evaluation, retained pidfd identity, actual
sender versus cached kernel PID, explicit socket inheritance, holder survival and
adoption, fixed request contents, typed counts and monotonic barrier ordering.
The parent observations supplement endpoint decisions; they do not authorize the
server's action.

## Environment, failures, cleanup and restoration

Recorded run: managed Linux 6.18.44 x86_64, Python 3.12.14, UID/EUID/GID 1000,
zero effective capabilities. All three schedules had no unexpected failures or
cleanup fallback; the mutant's unauthorized test action is explicitly Detected.
No development execution failure occurred.

Six direct server/client actors exited zero with empty stderr. Three holders also
exited zero and were reaped: by the still-live client in the healthy case and by
the runner after adoption in the loss cases. Holder stderr is not captured; exit
status and bounded control replies supply its recorded success/failure evidence.
All three socket entries and roots were removed after identity checks; no direct
children remain. The runner's child-subreaper flag was 0 before, 1 during, and 0
afterward. All retained pidfds and control/socket handles close during teardown.

Exceptional cleanup can signal only registered pidfds or a still-unreaped direct
Popen child whose pidfd setup failed. It never kills an unknown adopted process.
Unknown/replaced files or roots, uncertain actor ownership/reaping, and failed
restoration fail the run; unsafe root removal is refused. Cleanup path checks are
conservative fixture guards, not atomic defenses against hostile namespace races.
Actual cleanup/timeouts/unkillable-task faults were not injected natively.

[evidence/local-checks.txt](evidence/local-checks.txt) records 14 focused checks:
healthy admission, original-client exit rejection despite matching credentials,
mutant detection, kernel mismatch even in the mutant, payload/variant/missing-
request rejection, pidfd-query failure, creation changes/exited binding,
descriptor identity, partial startup cleanup, unknown-case rejection and corrupted
native snapshot rejection. Mock failures and replayed snapshots are not additional
native schedules or proof of hostile IPC security.

## Remaining coverage gaps

This is a narrow E06/B02 pre-commit lifetime subset, not an integrated updater or
production enrollment/privilege design. SO_PEERCRED remains a connection snapshot,
not continuous message authorship. The guard samples liveness at evaluation; it
cannot guarantee survival through a later action or exclude delegation while the
original client remains alive. That delegation schedule was not tested. No claim
is made about post-commit behavior, which must not depend on continued GUI life.

No reverse-direction server-loss case, PID-reuse attack, exec/credential change,
SCM_RIGHTS transfer, arbitrary malformed/flooded traffic, protected socket
namespace, cross-UID/root peer, polkit/UAC, Windows named pipe, Mint desktop,
service/cgroup lifetime, real close grant, package operation, durable intent or
recovery clearance was exercised. All six blockers remain open.
