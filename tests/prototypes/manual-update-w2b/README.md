# #72 W2b: lock lifetime with a surviving sentinel

Executed only the separately authorized **unprivileged Linux W2b** experiment.
No installed SDE paths, elevation, service/task registration, package operations,
production imports, workflows, builds or releases are involved. All other W2/W3
work remains deferred; B01–B06 remain open.

## Run

```bash
python3 tests/prototypes/manual-update-w2b/run_experiment.py > work/w2b-results.json
python3 -m unittest discover -s tests/prototypes/manual-update-w2b -p test_checks.py -v
```

Create `work/` first. Requires Linux, Python standard library, local `flock`
storage, writable temporary storage, process creation, readable `/proc` identity
metadata, pidfds/pidfd signaling and unprivileged `prctl` child-subreaper support.
No installation or network is needed. Preflight inability reports Blocked; an
error after cases start reports Fail. A fresh runner must have no existing children.

## Process ownership and isolation

Each case creates a fresh private 0700 `PROTOTYPE-W2b-*` root and one empty 0600 O
lock file. The runner closes its creation descriptor before starting the supervisor;
its later probe opens an independent file description. The supervisor acquires
O exclusive using nonblocking `flock`, then execs this same fixed script as a
sentinel. Both subprocess launches use `close_fds=True` and explicit `pass_fds`.
All actor credentials are checked: UID/EUID 1000, zero effective capabilities in
the recorded environment.

Kernel process identities (PID, PPID, UID and creation ticks) are read before and
after binding pidfds. Supervisor termination uses its bound pidfd; no bare-PID
signal is sent. The sentinel must initially belong to that supervisor. After the
supervisor exits, the sentinel must respond at the same creation identity and be
adopted by the runner. The runner temporarily sets **its own** child-subreaper bit
and restores the original bit afterward; this changes no service or system policy.
Sentinel exit is reaped through its pidfd. This is controlled test ownership, not
production IPC authentication or the proposed privileged supervisor mechanism.

Trusted socketpair/stdout messages provide explicit readiness, ping, descriptor-
close and exit barriers. Reads have five-second diagnostic watchdogs and an 8-KiB
message cap. Pipe/socket writes are small trusted messages, not hardened against
hostile backpressure. No sleeps or average stress outcomes establish correctness.

## Results

[Recorded native run](evidence/linux-run.json): **both directed cases Pass**,
33 total trace events (14 exclusion, 19 inheritance). The supervisor genuinely
excludes an independent probe before termination in both cases.

| Case | Descriptor setting and evidence | Observation after supervisor SIGTERM |
| --- | --- | --- |
| Exclude | Supervisor descriptor is non-inheritable; omitted from sentinel pass_fds; sentinel regular-file descriptor inventory has no matching lock inode | Independent probe acquires O while sentinel responds alive before and after probe |
| Inherit control | Explicit pass_fds includes supervisor's descriptor; sentinel reports matching fstat identity and matching actual descriptor inventory | Probe remains busy while sentinel survives. Sentinel closes its descriptor without LOCK_UN; probe then acquires O while sentinel is still alive |

Explicit inheritance is a diagnostic control, not a proposed production setting.
A shared open file description, not just the original process PID, determines
this observed `flock` lifetime. The probe runs in the independent runner process;
it is not another supervisor child. All probe descriptors close after observation.

The report records source hashes for both Python files, UTC start, environment,
private-root identity, mountinfo matches, launch descriptor settings, actor
identities, pidfd binding, ordered barriers, fstat identities, probe outcomes,
exit/reaping status, failures, cleanup and subreaper restoration.

## Environment, failures and cleanup

Recorded environment: managed Debian GNU/Linux 13, Linux 6.18.44, Python 3.12.14,
UID/EUID 1000 with zero effective capabilities. Roots are on tmpfs; all longest-
path mountinfo entries are recorded because this environment exposes stacked
mounts with differing flags. No new VM/container or booted desktop was created.

The [preserved development preflight](evidence/development-blocked-proc-children.json)
reported Blocked before starting any cases: this host omits task/*/children.
Child discovery was adapted to read process identity metadata and select direct
children of this otherwise child-free runner. No unrelated process is signaled.
That development report belongs to its earlier source hash, not the final source.
The final native cases have no unexpected failures or cleanup fallbacks.

Both supervisors exited by the intended SIGTERM (-15); both sentinels exited
normally (0) and were reaped. Each lock identity stayed unchanged. Both private
roots were removed, no direct children remained, and the runner's subreaper value
was restored from 1 to its original 0. Removal refuses uncertain process completion,
changed root/file identities or unknown root entries. Failure fallback signals
use owned pidfds and count as failure; uncertain roots remain for inspection.
Startup-orphan cleanup is limited to verified same-UID direct children adopted
into this single-purpose runner, and records any such fallback as failure.

[Four focused checks](evidence/local-checks.txt) additionally pass: reap timeout
never enters waitid, readable-pidfd reaping uses WNOHANG, a mismatched process
identity cannot bind a pidfd, and identity change during binding closes the handle.
Those checks use mocks; they are not additional native schedules or evidence for
unkillable processes. Source hashes and native cleanup invariants were verified
separately after the run.

## Limits and next gate

Only one prototype lock and two directed schedules on this kernel/filesystem were
exercised, using cooperating same-UID actors and trusted message plumbing. There
was no systematic race exploration, real timeout/cleanup failure injection,
malicious peer, descriptor-passing attack, desktop logout/suspend, native privilege,
Windows/Mint desktop, service/cgroup, storage durability or actual installer test.
This does not prove production descriptor hygiene or lock-object compatibility.

No installation intent, journal, receipt, package child or recovery startup exists
here. **A released lock does not establish that native installation stopped.**
The exclusion case deliberately demonstrates that a child can remain alive after
the supervisor's lock disappears. Neither result authorizes GUI startup during
uncertain real installation. Durable-intent/child-quiescence validation remains a
separate requirement; no blocker is cleared and no broader wave is authorized.
