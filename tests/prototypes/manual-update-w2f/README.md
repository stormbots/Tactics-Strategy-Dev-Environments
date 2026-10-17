# #72 W2f: unprivileged Linux Unix-socket peer identity

Only W2f was executed. Production code, other W2/W3 experiments, elevation,
registration, packages, workflows, builds and release preparation are unchanged.
All six blockers remain open. This is a narrow E06/B02 surrogate, not native
production authentication certification.

## Reproduce

```bash
python3 -I tests/prototypes/manual-update-w2f/test_checks.py
python3 -I tests/prototypes/manual-update-w2f/run_experiment.py > work/w2f-run.json
```

Create `work/` first. Requires Linux AF_UNIX/SO_PEERCRED, pidfd_open and pidfd
signaling, readable `/proc`, Python standard library and private temporary
storage. No external network is contacted. The execution sandbox initially
prohibited socket bind (EPERM); `evidence/blocked-sandbox-run.json` preserves that
failed attempt, child exit and successful root removal. The passing run used
sandbox socket permission, without OS elevation or capabilities. Missing socket
access must not be replaced with mocked native credentials.

## Protocol and trust boundary

The runner starts independent exec'd server/client actors with closed inherited
file descriptors. Servers bind their own pathname sockets; clients create their
own connected sockets. Tested sockets are not parent-created socketpairs.
Parent-owned stdin/stdout pipes enroll expected PID, UID, GID, parent PID and
`/proc` creation ticks before either actor connects. Each actor has its own
parent-held pidfd. Enrollment through these pipes is a trusted fixture assumption,
not a solution for production original-GUI enrollment.

Both endpoints independently obtain kernel SO_PEERCRED and compare UID/GID/PID
before accessing peer process metadata. They sample creation identity around
pidfd_open and require an unsignaled pidfd. Verification is reported through
separate control pipes; both processes remain alive behind an explicit barrier.
The parent sends the same `exchange` barrier in all three cases, with no allow
or deny bit. Each endpoint gates its own requests, actions and trusted replies
on its verification result. The unexpected client sends a valid fixed request
claiming the enrolled client's PID. The rejecting server receives the bounded
probe only to discard/log it, without parsing it as an authorized request. The
unexpected server sends a valid-looking acknowledgment claiming the enrolled
server's PID. The rejecting client discards/logs it without issuing a request or
trusting the acknowledgment. These fixed attack probes are test code, not an
application protocol or an arbitrary hostile-stream parser.

The independent result oracle checks actual kernel identities against the owned
actors, enrolled identities, creation snapshots/liveness, verification reasons,
verification-before-exchange ordering, exact typed counters, and receipt of the
spoofed probes. Same-UID admission alone, accepted flags alone, or zero counts
without a received probe cannot establish a pass.

Five-second per-operation watchdogs are test-only. The report records both
verification directions, enrollment and observed credentials, creation samples,
pidfd liveness, decision reasons, monotonic verification/completion times, actor
ownership, socket device/inode/UID/GID/mode, counters, failures and teardown.

## Recorded results

`evidence/linux-run-reviewed.json` binds the reviewed Python sources (including the unchanged W2b
utility module imported for definitions only) by SHA-256. On Linux 6.18.44,
Python 3.12.14, UID/GID 1000 and zero effective capabilities:

| Case | Server verifies client | Client verifies server | Server actions / client requests / trusted acknowledgments |
| --- | --- | --- | --- |
| Intended peers | Accepted live enrolled instance | Accepted live enrolled instance | 1 / 1 / 1 |
| Unexpected same-UID client | Rejected: PID mismatch | Accepted real server | 0 / 1 attempted / 0 |
| Unexpected same-UID server | Accepted intended client | Rejected: PID mismatch | 0 / 0 / 0 |

The wrong-client case retains the intended enrolled client alive. The wrong-server
case retains the intended enrolled server alive and directs the client to a
separate fake endpoint; it does not simulate namespace replacement races.
Eight actors exit normally and are reaped. All three private 0700 roots and four
0600 socket entries are removed after identity checks, with no remaining children
or passing-run failures. Unknown or replaced entries, a replaced root, or
uncertain actor cleanup prevent filesystem deletion. These checks are conservative
fixture cleanup guards, not an atomic defense against a hostile filesystem racer.

`evidence/local-checks-reviewed.txt` records 18 focused checks. They include
synthetic credential/creation/liveness failures, invalid enrollment types,
pidfd-open failure, partial actor-startup teardown, preservation of unknown or
replaced entries/root, independent endpoint action gating, unknown-scenario
rejection, and rejection of contradictory snapshots/counters/timestamps/probe
records. Synthetic checks do not extend native coverage to those faults.

The original `linux-run.json` and `local-checks.txt` remain unchanged as historical
evidence for commit `cc06f25`. Their negative cases used parent suppression and
must not be cited as proof of endpoint-enforced action rejection. See
[REVIEW.md](REVIEW.md) for review findings and evidence boundaries.

## Remaining gaps

SO_PEERCRED is a kernel snapshot for the connected peer, not proof of continuous
message authorship, executable identity, or who may subsequently receive an FD.
The pidfd is held during verification only; peers remain alive by harness barriers
until exchange completes. This does not solve exit/exec/FD-transfer races in a
production IPC session. No PID reuse attack, ancillary FD transfer, arbitrary hostile byte
stream, credential transition, malicious control parent, cross-UID/root peer, protected production
socket namespace, polkit/UAC, Windows named pipe, Mint desktop or real application
bootstrap was tested. No unexpected same-UID peer was accepted in these schedules;
that result cannot close B02 or any other blocker.
