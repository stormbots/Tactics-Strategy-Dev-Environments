# #72 W2h: live-client socket-delegation diagnostic

Only W2h ran: one healthy original-client control and one holder sending through
an explicitly inherited connected socket while its enrolled original client stays
alive. Credential and liveness guards stay enabled in both cases. This is
pre-commit test authority only: an authorized action is a single in-memory counter,
not a GUI close, policy write, package operation or installer launch.

**Diagnostic success does not mean authentication safety.** The recorded result is
`diagnostic_success=true`, `authentication_safety=CounterexampleDetected`, and
`production_readiness=false`. Exit status zero means the diagnostic completed and
detected the expected counterexample, not that the guard meets B02 requirements.
All six blockers remain open. All other W2/W3, elevation, registration, production
implementation, package operations, workflows/builds and release work remain
deferred. No authentication replacement or protocol revision was implemented.

## Run and environment

```bash
mkdir -p work
python3 -I tests/prototypes/manual-update-w2h/run_experiment.py > work/w2h-run.json
python3 -I tests/prototypes/manual-update-w2h/test_checks.py
```

Requires unprivileged Linux with zero effective capabilities, Python standard
library, readable `/proc`, AF_UNIX/SO_PEERCRED, pidfds/signaling, child-subreaper
support and private temporary storage. The runner must initially be child-free.
Local socket sandbox permission is needed; no external network, account creation,
VM/container provisioning, service or package operation is involved. The disposable
boundary is run-owned actors and private roots in the existing managed runtime.
Missing prerequisites produce a Blocked reason. Errors after a case starts fail
the diagnostic and stop dependent cases. Five-second watchdogs are test diagnostic
limits, not production timing guarantees.

## Scope and unchanged guard

W2h imports reviewed W2g/W2f/W2b definitions only. No earlier scenario or entrypoint
runs, and no previous helper is edited. All spawned actors execute the W2h script.
The server calls the unchanged W2g `evaluate` function with literal `guarded`.
Its setup command accepts no guard-selection field. The fixed request retains
its `W2g-precommit` fixture tag so the exact reviewed predicate is exercised;
that tag is a test-format name, not evidence that W2g scenarios were rerun.

Both server and client independently create their tested Unix-stream endpoints.
Mutual initial verification uses kernel SO_PEERCRED, trusted parent enrollment,
process creation samples and pidfd liveness. The server additionally retains its
original-client pidfd through evaluation/shutdown. The client passes exactly two
descriptors to an exec'd holder with `close_fds=True`: its connected data socket
and separate trusted control endpoint. Parent-created socketpairs are control
plumbing only, not the credential endpoint under test.

The runner binds the holder's distinct process instance independently, observes
its original client as parent, and checks descriptor device/inode/owner/type and
inheritance settings. Both client and holder remain alive across request handling.
Separate control channels record actual sender identity and cumulative send counts.
Before each request both send totals are zero. Afterward they are 1/0 for the
healthy client/holder and 0/1 for delegation. The original client waits on trusted
control while the holder writes in the delegated schedule.

Named barriers establish connection/authentication, holder readiness, original-
client and holder liveness, request send, server evaluation, subsequent liveness,
shutdown and reaping. The parent supplies no action allow/deny decision. The
server checks cached kernel peer PID/UID/GID and its retained original-client
pidfd at evaluation. The holder's request claims the enrolled client's PID;
independent controls identify the actual sender without treating that claim as
authentication authority.

## Native result and counterexample

[Reviewed native evidence](evidence/reviewed-linux-run.json) records 50 ordered barrier events,
source hashes, ownership, privileges, descriptor settings, both initial
verification directions, retained pidfds, before/after process observations,
request counts, evaluation results, cleanup and restoration.

| Case | Actual sender | Server SO_PEERCRED | Original client pidfd | Client/holder sends | Server-permitted test actions | Classification |
| --- | --- | --- | --- | --- | --- | --- |
| Healthy original client | Original client | Original client | Live | 1 / 0 | 1 | Pass: healthy control only |
| Live-client delegation | Distinct holder | Still original client | Live | 0 / 1 | 1 | CounterexampleDetected |

In the delegated schedule the enrolled client and actual holder sender have
distinct PIDs, and SO_PEERCRED still reports the enrolled client PID. Both
credential/liveness conditions pass. This counterexample requires no omitted
liveness check, mutation of the guard or parent permission to authorize an action.
The finding is that connection credentials plus retained original-client liveness
are insufficient to establish the sender of each request on a delegated socket.

The oracle requires mutual authentication/creation evidence, original-client and
holder liveness, matching inherited socket identities, exact explicit inheritance,
actual-sender identity, non-sender silence, fixed request contents, typed counts
and monotonic barrier order. Disabled guards, an exited original client, an
unexpected rejection, or inconsistent ownership/transport observations cannot be
reported as a successful W2h diagnostic. Unexpected outcomes remain evidence for
inspection, not fabricated acceptance of the expected counterexample.

## QA, failures and cleanup

Recorded environment: managed Linux 6.18.44 x86_64, Python 3.12.14,
UID/EUID/GID 1000, zero effective capabilities. Both diagnostic schedules completed
without infrastructure failures or cleanup fallback. The delegated authorization
is the explicit authentication counterexample. No unexpected native execution
failure occurred; pre-fix local regression failures are preserved below.

[Original local checks](evidence/local-checks.txt) record 15 passing checks.
They verify that the reused guard accepts a live enrolled connection but still
rejects an exited original or mismatching kernel PID; that the healthy control
cannot be generalized to safety; that delegated authorization is classified as a
counterexample; and that disabled guards, non-sender writes, false sender claims,
invalid inheritance/privilege/events/counts/order, unexpected rejection and unknown
cases are rejected. These checks use mocks and recorded snapshots; they are not
additional native attacks, native client-exit tests or reruns of prior experiments.

Four direct server/client actors exit zero with empty stderr. Both holder actors
exit zero and are reaped by their still-live original clients. Holder stderr is
not captured; control replies and exit status provide its recorded evidence.
All six actors are reaped, both private 0700 roots and their 0600 socket entries
are removed, no children remain and no close errors occur. The runner's temporary
child-subreaper setting is restored 0 → 1 → 0; adoption is reserved for exceptional
cleanup and is not used in either normal schedule. All retained handles close.

W2h cleanup uses reviewed W2g close utilities to continue across individual errors and refuses
unknown/replaced paths or uncertain process cleanup. Only registered pidfds or a
still-unreaped direct Popen child can be signaled; unknown adopted actors are not
killed. Actual exceptional cleanup, timeouts and unkillable tasks were not tested
natively. Path checks are fixture safeguards, not atomic hostile-race protection.


## W2h implementation and evidence review

The original `linux-run.json` and `local-checks.txt` are preserved unchanged, with
source hashes bound to commit `b124ea7`. Reviewed source/evidence appears in
`evidence/reviewed-linux-run.json` and `evidence/review-checks.txt`. No earlier
helper source, guard implementation or experiment was modified/rerun.

The original native records support the counterexample and its classification.
Review fixed two narrow W2h proof/cleanup gaps:

- The oracle now requires ordered initial credential-verification timestamps,
  independently observed holder readiness, and readiness before the existing
  client/holder/request/evaluation barriers. Previously a mutated authentication
  timestamp after evaluation was accepted in either case.
- W2h has a local fallback-cleanup override that still reaps the registered holder
  if it exits between a live probe and pidfd signaling. The inherited path could
  skip reaping after ProcessLookupError. W2h also requires the returned wait PID
  to match the registered holder and validates the wait-event kind/status before
  treating cleanup as complete. Signal termination and exit codes are recorded
  separately. Mismatched wait evidence leaves reaping uncertain and prevents root
  removal. Exceptional cleanup still fails the diagnostic, even when reaping
  succeeds; it cannot create an authentication safety pass.

[Pre-fix output](evidence/review-counterexamples.txt) records **four failing
assertions across three added regressions in an 18-test suite**: authentication
ordering for both native fixtures, a simulated exit/signal race, and mismatched
reap PID. These are snapshot/mocked counterexamples to harness validation, not
four native authentication failures. [Reviewed checks](evidence/review-checks.txt)
pass **all 18 checks**. The two authentication timestamps and cleanup faults in
these regressions are injected facts, not additional native schedules.

The reviewed native run still records healthy control Pass and live delegation
CounterexampleDetected, 50 barrier events and one permitted test action in each
case. Both guards remain enabled with the unchanged `guarded` evaluator. All six
actors exit zero and are reaped, both roots/socket entries are removed, no native
cleanup fallback/close errors occur, and the subreaper flag is restored. The
summary remains diagnostic_success=true, authentication_safety=CounterexampleDetected,
production_readiness=false. Source hashes bind the reviewed W2h Python files and
unchanged W2g/W2f/W2b helper definitions. Native exceptional-cleanup/timeout faults
and broader security integration remain unvalidated.

## Remaining gaps and design consequence

B02 requires a design decision before treating original-process request binding
as feasible. This diagnostic implements no per-message identity mechanism and
makes no claim that another credential API, transport or capability design solves
the issue. Trusted enrollment/control channels and cooperative role code are test
assumptions. The counterexample is bounded to this guard and explicit delegation.

No cross-UID/root peer, protected production namespace, executable/session/namespace
binding, SCM_RIGHTS transfer, PID reuse, exec/credential change, hostile partial
frames/flooding, reverse server loss, Windows/Mint desktop, polkit/UAC or service
lifecycle was exercised. No Ready/Commit/close-grant integration, post-commit work,
lock coordination, durable intent, recovery or real installer operation occurred.
This result neither clears B02 nor establishes a released application defect.
Engineering review of W2h and a subsequent B02 specification decision are the
proposed follow-ups; no additional experiment is authorized by this result.
