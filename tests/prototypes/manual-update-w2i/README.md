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

The reviewed [native report](evidence/reviewed-linux-run.json) has three fresh connections and
64 ordered barrier events:

| Case | Kernel / syscall evidence | Authorized actions |
| --- | --- | --- |
| I1: intended original, explicit valid credentials | Sender/original PID 36349; received SCM_CREDENTIALS `[36349,1000,1000]`; complete 53-byte record; fixed reply independently credential-checked | 1 |
| I2: live original, inherited-socket holder, automatic credentials | Original PID 36351 remains live; actual holder PID 36352; received SCM_CREDENTIALS `[36352,1000,1000]`; complete 53-byte record; receiver rejects `sender mismatch` | 0 |
| I3: holder explicitly claims original PID | Original PID 36354 remains live; holder PID 36355; sendmsg returns -1 with actual errno 1 / EPERM; independent receiver status reports no received/queued record | 0 |

These are observed run-specific PIDs, not fixed inputs. I3's errno, not a receive
timeout, establishes the observed kernel refusal. The original sends no action
in I2/I3; holder payload fields and attempt bindings are otherwise valid.

[Reviewed focused checks](evidence/review-checks.txt): **29 pass** — the original
12 synthetic validator checks and 7 evidence/orderly-exit checks, plus 10 review
regressions covering synthetic, corrupted-evidence and mocked failure paths.
None is an additional native hostile-traffic schedule. The original
[native report](evidence/linux-run.json), [19-check record](evidence/checks.txt) and
[12-check synthetic-only record](evidence/synthetic-checks.txt) remain historical
baseline evidence at commit `41c04b9`; their source hash does not identify the
reviewed source. The reviewed report pins the current harness hash.

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
enforces an eight-container JSON nesting bound before decoding, then limits
accepted fields and PID range. No generic command execution or real secret
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
integration remain unvalidated. Cleanup fault coverage includes the observed initial reporting/startup failures
and local mocked orderly-exit, signal-race, wait, ownership/status and restoration
checks. Those mocks are not native crash, pidfd failure, descriptor truncation or
unkillable-descendant injection. Unknown/pre-enrollment descendants remain an
explicit gap; absent or failed reaping evidence cannot authorize fixture deletion.

## Review corrections and affected QA

Review baseline: `41c04b9`. Only this W2i harness, its checks/evidence and linked
W2i documentation were changed.

| Finding | Correction | Coverage |
| --- | --- | --- |
| Healthy I1 rejection was recorded as an authentication counterexample | Healthy failure is Fail; only observed delegated action acceptance is CounterexampleDetected; counterexamples propagate to top-level property results | Local classification/count regressions; unchanged native I1/I2 schedules |
| Actor exit could race a signal and skip waiting / FD closure | Treat ESRCH as a race, still wait for the owned child; close transports and retained pidfd in finally | Mocked signal race and wait failure regressions |
| Exited holder was not sufficient proof of reaping | Require a validated normal holder wait or terminal adopted-holder wait with matching PID; preserve root if reaping is uncertain | Normal native reaping plus mocked wrong wait identity/status; no native crash injection |
| Restoration or audit errors could prevent final report persistence | Preserve finalization errors, fail diagnostic success, and retain results; do not claim restored state after a restoration error | Mocked setup/restoration failure with no actor launch |
| Original nesting fixture exceeded frame limit before JSON parsing | Enforce depth before decoding; add a within-limit depth fixture and quoted-bracket/escape control | Synthetic only |
| Evidence checks did not require every intended submission mode / holder count | Audit explicit I1, automatic I2, forged I3; strict integer counts, actual sender, namespaces, endpoint device/inode/options, liveness and barrier order | Audit before native case Pass plus local corrupted-record tests |
| Socket options were audited late | Assert listener/client receiving options before connect/readiness and preserve non-inheritable enrollment pidfd flags | Same three native schedules |

[Three before-fix regressions](evidence/review-regressions-before-fixes.txt) were
run against the unmodified baseline using existing entrypoints: signal/exit race,
wait failure FD cleanup, and report persistence on restoration failure. They
produce two errors and one failed assertion before correction. New-helper
absence is **not** counted as a reproduced defect. The reviewed suite passes
all 29 checks; the native rerun retains I1/I2/I3 = 1/0/0, actual EPERM, 64 events,
normal reaping of eight owned actors, removed roots and restored settings.

No new authentication counterexample appeared in the reviewed native run.
Diagnostic success and narrow primitive feasibility remain distinct from
unproven authentication safety. No B01–B06 blocker is closed.

## Reproduction (only within separately authorized W2i scope)

```sh
python tests/prototypes/manual-update-w2i/run_experiment.py /tmp/w2i-report.json
python -m unittest discover -s tests/prototypes/manual-update-w2i -p test_checks.py -v
```

The focused evidence audits read the checked-in report; they do not rerun native
schedules. Missing prerequisites stop the run; do not install packages, elevate,
substitute stream sockets, waive credentials, or continue dependent cases.
[evidence/SHA256SUMS](evidence/SHA256SUMS) pins the final source, tests and artifacts.
