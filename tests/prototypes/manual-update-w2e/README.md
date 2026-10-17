# #72 W2e: progress backpressure and safe pre-install deferral

Executed only the separately authorized unprivileged Linux W2e experiment: a
responsive-reader control and an alive/open but deliberately stalled progress
reader. This is a test-only supervisor and GUI surrogate, not an SDE updater.
All other W2/W3, elevation, registration, production implementation, package
operations, workflows, build dispatch and release work remain deferred.
B01–B06 remain open.

## Run and requirements

```bash
python3 tests/prototypes/manual-update-w2e/run_experiment.py > work/w2e-results.json
python3 -m unittest discover -s tests/prototypes/manual-update-w2e -p test_checks.py -v
```

Create `work/` first. Requires Linux, Python standard library, private temporary
storage, local flock, pidfds/signaling, readable process identity metadata,
nonblocking pipes, F_GETPIPE_SZ and FIONREAD. No installation or network is needed.
The runner must initially be child-free, unprivileged and have zero effective
capabilities. Preflight failure is Blocked; failures after root allocation are
Fail. All original scenarios in helper modules remain unexecuted.

Each fresh 0700 `PROTOTYPE-W2e-*` root contains 0600 O/A/S files. Three exec'd
same-UID actors belong directly to the runner: GUI surrogate, reader and
supervisor. The GUI retains S shared throughout the test. The supervisor holds
O/A exclusive, never acquires S and never starts an installer/mutation child or
creates installation intent. Kernel creation identities are checked around pidfd
binding; only registered pidfds authorize fallback signals.

## Channels, queue bound and test timing

Progress uses its own OS pipe created O_NONBLOCK/O_CLOEXEC. Only the reader gets
the read endpoint and only the supervisor gets the write endpoint; the parent
closes its copies. Their fstat identities must match. Each actor has separate
trusted stdin/stdout control channels. The stalled reader does not read progress
at all, but continues answering control and inspecting FIONREAD without draining.
The responsive reader drains into a bounded 4096-byte temporary buffer and counts
received bytes; it does not retain a progress history.

A frame is exactly 512 bytes, below the observed PIPE_BUF atomic-write bound.
The application retains at most one pending frame, replacing older pending
progress on subsequent updates. Nonblocking writes either accept a whole frame
or return EAGAIN; partial atomic-size writes and unrelated errors fail. Writable
transport retries do not block the control/deadline loop. Pipe capacity is read
from the kernel and limited to 1 MiB for this test; no capacity is changed.

**Timing is test-only:** begin fixes a two-second monotonic lease. Pumping progress,
ping, status and await_deferred never renew it. The event loop evaluates expiry
independently of progress writability, including after select wakes. At expiry it
writes a small private Deferred record, drops pending unsent progress and releases
O/A without waiting for S or for the reader. It then answers the pending deferral
query through control. The record is written before lock release; no file/directory
fsync or durability guarantee is claimed.

A separate five-second diagnostic watchdog bounds observed deferral decision,
reply receipt and independent lock verification relative to lease start. This is
not the production 30/45-second budget, a suspend/resume test or a real-time kernel
scheduling guarantee. The pre-begin Prepared state is a test setup barrier, not
validation of production readiness/handshake lifetime.

## Native results

[Machine-readable report](evidence/linux-run.json): **both cases Pass**, with
90 trace events (45 per case).

| Case | Observed behavior |
| --- | --- |
| Responsive | Progress bytes are delivered; supervisor control remains responsive; original test lease reaches Deferred; O/A release while live GUI still protects S |
| Stalled | Kernel EAGAIN/EWOULDBLOCK is observed, progress coalesces to one pending frame, reader stays open/alive with zero bytes read, ping/status work while Waiting, and deferral releases O/A without draining progress |

In the recorded stalled case the kernel pipe capacity is 65,536 bytes, 128 frames
are accepted and subsequent writes observe errno 11. There are 384 backpressure
events and 383 coalesced overwrites. Pending high-water is **one frame / 512 bytes**;
after deferral the pending slot is discarded. The reader still reports **zero
bytes read and 65,536 bytes queued** after lock release. Responsive delivery is
verified separately; transient backpressure in that control would not itself be
a failure if progress is delivered and the other invariants hold.

Independent probes observe O/A/S busy before begin. After deferral O/A are
acquirable while S remains busy, and the GUI answers an alive control barrier
still reporting shared S. There is no normal-session termination or native
installation attempt. Supervisor snapshots, deadline/decision/reply/probe times,
queue counters, errno, capacity, reader bytes/queued bytes, descriptor identities,
actor identities and control-response latencies are retained.

Queue counters establish the pending-frame data structure bound only. They are
not a measured process RSS/memory bound. Kernel buffering is reported separately;
JSON construction and temporary buffers are not included in the 512-byte pending
slot claim. The transport is trusted test plumbing, not authenticated production
IPC or a flood-resistant protocol implementation.

## Environment, checks, failures and cleanup

Recorded host: managed Debian GNU/Linux 13, Linux 6.18.44, Python 3.12.14,
UID/EUID 1000, zero effective capabilities, private roots on tmpfs. All longest-
path mountinfo matches are recorded; no VM/container, desktop, service/task or
subreaper setting was created/changed. Only utility definitions from the reviewed
W2b test helper are reused, with that dependency bound by source hash.

[Five focused checks](evidence/local-checks.txt) pass: blocking writer rejection,
10,000 blocked updates retaining only the latest bounded frame, successful-write
slot removal, partial atomic-size write failure, and broken-reader errors staying
distinct from EAGAIN. These are mock/error-path checks, not additional native
backpressure schedules or actual failure injection.

**Failures:** none in the recorded native cases; EAGAIN is the intended stalled-
reader observation. No cleanup fallback was needed. The development rerun added
state-record validation and timestamps for reply/lock verification, without
changing the two schedules or test lease.

**Cleanup:** both supervisors reach Deferred before exit. Readers remain open
until the proof is complete and exit before the writer, avoiding an unrelated
EOF experiment. All six actors exit 0 and are reaped; no direct children remain.
O/A/S identities stay unchanged and each exact recorded Deferred fixture stays
unchanged until teardown. Only known files are removed after actor completion;
both private roots are removed and their absence verified separately. Unknown
objects or uncertain process completion preserve the root and fail. Final fixture
deletion is test teardown, not recovery clearance. Source hashes and unchanged
shared-helper source were checked separately.

## Coverage limits

Only two directed same-UID cooperating-process cases, one pipe capacity and these
small fixed messages. No adversarial partial control frames, flooding, broken
reader native schedule, real timeout/cleanup/storage fault injection, multiple
GUI/workers, native peer authentication/ACLs, privileged process/service lifetime,
actual installer/postchecks/journal/recovery, persistent storage/power-loss,
Windows/Mint desktop or production timeout/suspend behavior was tested.
await_deferred is an observer request; source and fixed-deadline traces support
that it does not initiate expiry, but no separate observer-free schedule ran.
No exhaustive liveness or universal kernel-I/O termination proof is claimed.
All six blockers remain open, including B02/B06; no broader wave is authorized.
