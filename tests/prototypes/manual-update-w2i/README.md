# W2i: unprivileged Linux record-credential primitive

Issue #72 / B02 revision 4 only. The owner authorized this isolated experiment
following Gate A review at baseline `99532ee`. This is test-only pre-commit
authority: the only permitted effect is a server-local integer increment.
No production updater, GUI, close grant, elevation, registration, package,
workflow, build, version or release operation is implemented or exercised.

## Disposition

**Diagnostic success: true. Primitive feasibility at this scope: Pass.
Authentication safety: Unproven. Production readiness: false.**

W2h remains unchanged: its diagnostic successfully demonstrated the earlier
guard's authentication counterexample. W2i tests a different proposed transport;
it does not retroactively turn W2h into an authentication pass or close B02.
B01–B06 remain open.

The final [native report](evidence/linux-run.json) has three fresh connections and
64 ordered barrier events:

| Case | Kernel / syscall evidence | Authorized actions |
| --- | --- | --- |
| I1: intended original, explicit valid credentials | Sender/original PID 35653; received SCM_CREDENTIALS `[35653,1000,1000]`; complete 53-byte record; fixed reply independently credential-checked | 1 |
| I2: live original, inherited-socket holder, automatic credentials | Original PID 35656 remains live; actual holder PID 35657; received SCM_CREDENTIALS `[35657,1000,1000]`; complete 53-byte record; receiver rejects `sender mismatch` | 0 |
| I3: holder explicitly claims original PID | Original PID 35659 remains live; holder PID 35660; sendmsg returns -1 with actual errno 1 / EPERM; independent receiver status reports no received/queued record | 0 |

These are observed run-specific PIDs, not fixed inputs. I3's errno, not a receive
timeout, establishes the observed kernel refusal. The original sends no action
in I2/I3; holder payload fields and attempt bindings are otherwise valid.

[Focused checks](evidence/checks.txt): **19 pass** — 12 synthetic validator checks,
6 saved-evidence audits, and 1 mocked orderly-exit regression check. None of those
19 checks is an additional native hostile-traffic schedule. The initial
[12-check synthetic-only record](evidence/synthetic-checks.txt) is also retained.

## Trust, ordering and resource bounds

`run_experiment.py` is standalone; it does not execute earlier W2/W3 harnesses.
The runner launches independent server and original client processes using
private control pipes. Expected process instances are enrolled out of band from
owned-child OS metadata, then retained via pidfds at both peers. First-record
credentials confirm that enrollment; a payload PID never creates trust. The
receiver, not the runner, checks each record and decides its action count.

The server creates a real pathname AF_UNIX SOCK_SEQPACKET listener, not an inherited
parent-created data socketpair. Listener SO_PASSCRED is enabled and verified before
connect is released. Client receiving options are set before connect; inherited
accepted options are verified before the first send barrier. All data reads use
recvmsg with mandatory MSG_CMSG_CLOEXEC and fresh per-record credentials. The
server validates client Hello and the client validates server replies.

For I2/I3 the original explicitly launches its holder with exactly the connected
socket in `pass_fds`, `close_fds=True`. Descriptor inode/device/flags, parentage,
credential/capability sets, namespace identities, actual senders, retained pidfd
state and barrier order are recorded. Original and holder are single-threaded and
observed alive before/after evaluation; this is not an atomic production
liveness-to-action proof. No SO_PEERCRED dependency or fallback is used.

Test-only bounds: 16,384 record bytes including four-byte length prefix; 256
ancillary bytes; 4,096 control-line bytes; one action attempt per sender; one
connection per case; five-second per-operation watchdogs. Fixed JSON schema
limits depth, fields and PID range. No generic command execution or real secret
is accepted. The reader does not cache credentials from earlier records.

## Environment, cleanup and restoration

Final run: managed disposable Linux x86_64, kernel 6.18.44, glibc 2.41,
Python 3.12.14. Runner and actors used UID/GID 1000. All observed capability sets
were zero. PID/user namespace identities and OS creation metadata are in the
report; actors did not transition them. This is **not Mint desktop validation**,
cross-UID/root validation, or Windows validation.

The default command sandbox denied local Unix-socket creation. The later run
used the tool's additional network/socket permission with the same Python
command, without sudo, changed credentials, host privilege elevation, external
network requests, or replacement of the required transport. The invocation
contexts' recorded user namespace identities differ; each case requires all
actors to match its runner's context. Results are scoped to the final context.

All eight final-run actors exited normally and were reaped (six direct Popen
waits, two holder waits by their originals); retained holder pidfds also report
exit. No forced cleanup signal was used in the final run. All three private
0700 roots and 0600 socket entries were removed after ownership checks. Runner
FD count was 4 before and 4 after; subreaper state was restored 0 → 1 → 0.

This runtime lacks `/proc/.../children`; that extra global child-enumeration audit
is explicitly unavailable. Cleanup evidence concerns registered run-owned actors
and their retained handles/waits; it makes no claim about unrelated or unknown
processes. Abrupt failures before descendant enrollment remain a fault-coverage
gap, not a claimed tested cleanup guarantee.

## Preserved failures and corrections

- [Initial reporting failure](evidence/initial-reporting-failure.txt): final proc
  child enumeration raised FileNotFoundError before saving a report. No native
  case result is claimed from that invocation. Added incremental case persistence
  and explicit unavailable-audit reporting.
- [Initialization reporting failure](evidence/initialization-reporting-failure.json):
  the denied server startup was masked by a missing `identity` lookup. Corrected
  initialization error propagation and retained initialization responses.
- [Sandbox socket denial](evidence/sandbox-socket-denial.json): the server reported
  PermissionError before I1; I2/I3 were not attempted. The historical report says
  Fail; current code classifies this prerequisite denial Blocked.
- [Cleanup-race run](evidence/cleanup-race-run.json): native outcomes matched the
  expected counts, but the runner signaled direct actors immediately after their
  stop acknowledgements, yielding -15 exits. Overall diagnostic success was false.
  Its historical per-case Pass labels exclude that final cleanup failure and must
  not be read as complete gate passes. Corrected orderly waiting and made abnormal
  or forced normal-path cleanup fail the case before dependent cases proceed.
- Final run reran only the authorized W2i schedules after harness corrections.
  Historical failures are not counted as passes or additional coverage.

## Remaining gaps

No native malformed/truncated/SCM_RIGHTS/saturated traffic was injected. Synthetic
FD tests use locally owned pipe FDs in fabricated metadata; they do not validate
kernel descriptor installation, partial ancillary delivery or native leak safety.
Those are mandatory later adapter gates. This fixed-envelope harness also does
not implement the full protocol negotiation, attempt capability, replay, consent,
Ready, close grant, durable intent, installation or recovery state machines.

Hostile/delegated server writers, process exit races, thread/exec/credential or
namespace transitions, privileged forgery, protected root-owned endpoint/bootstrap
enrollment, compatibility migration, Windows attribution and desktop/service
integration remain unvalidated. Cleanup fault coverage is limited to the observed
reporting/startup failures and the mocked orderly-exit regression, not arbitrary
native crash, pidfd failure or unkillable descendant injection.

## Reproduction (only within separately authorized W2i scope)

```sh
python tests/prototypes/manual-update-w2i/run_experiment.py /tmp/w2i-report.json
python -m unittest discover -s tests/prototypes/manual-update-w2i -p test_checks.py -v
```

The focused evidence audits read the checked-in report; they do not rerun native
schedules. Missing prerequisites stop the run; do not install packages, elevate,
substitute stream sockets, waive credentials, or continue dependent cases.
[evidence/SHA256SUMS](evidence/SHA256SUMS) pins the final source, tests and artifacts.
