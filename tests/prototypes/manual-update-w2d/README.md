# #72 W2d: post-session intent-check race

Executed only the separately authorized unprivileged Linux W2d experiment: two
barrier-controlled guarded schedules and an explicitly defective startup control.
No installed SDE, production code, elevation, registration, packages, workflows,
build dispatch or release work is involved. All other W2/W3 remains deferred;
B01–B06 remain open.

## Run and requirements

```bash
python3 tests/prototypes/manual-update-w2d/run_experiment.py > work/w2d-results.json
python3 -m unittest discover -s tests/prototypes/manual-update-w2d -p test_checks.py -v
```

Create `work/` first. Requires unprivileged Linux, Python standard library,
readable process metadata, pidfds/pidfd signaling, local flock/hard-link/fsync
support and private temporary storage. The runner starts without children and
with zero effective capabilities. It imports definitions from the unchanged W2c
fixture and W2b process/message helpers, without executing their earlier scenarios.
All three dependency/source locations are bound by hashes in the report.

Each schedule uses a fresh 0700 `PROTOTYPE-W2d-*` directory, empty 0600 O/A/S
files, and two separate exec'd actors: startup and an O/S-only legacy surrogate.
No child-subreaper change is needed: both actors belong directly to the runner.
Processes are checked for PID/PPID/UID/creation identity and bound to pidfds.
Only registered pidfds receive termination signals. IPC is trusted test plumbing,
not production authenticated IPC. Messages use the reviewed helper's size bounds
and diagnostic read/write watchdogs. There are no sleep-based race assertions.

## Results and independent oracle

[Native run](evidence/linux-run.json): **two guarded schedules Pass; negative
control Detected**, with 56 total trace events (19, 18 and 19 respectively).
The overall Pass means this expected combination, not that the defective control
was safe. The report separates guarded_passes=2 and negative_control_detected=true.

| Schedule | Controlled ordering | Observed outcome |
| --- | --- | --- |
| legacy_wins | Startup holds A shared and checks intent absent. Legacy takes O/S exclusive, ignoring A, then publishes unresolved intent. Startup's S attempt is busy and retains A. The owned legacy actor is terminated. Startup acquires S and performs its second check. | Second check sees the original unresolved intent; RecoveryRequired, no normal session, all startup locks released. Independent exclusive O/A/S probes then succeed. |
| startup_wins | Startup holds A, sees no intent, obtains S shared, checks absent again and releases A while retaining S. Legacy acquires O but its S-exclusive attempt is busy. | NormalSession remains protected by S; legacy releases O and defers with no publication and zero mutation starts. Probes acquire O/A and are excluded by S. |
| negative_omitted_check | Repeat legacy_wins, but deliberately skip startup's second intent check after S acquisition. | Defective actor reports NormalSession and retains S despite unresolved intent. The independent oracle detects normal_admission_with_unresolved_intent; a kernel probe confirms S exclusion. |

The oracle inspects the actual fixture independently of the actor's second-check
claim. The mutant reports second.skipped=true; that does not conceal the fixture.
It is an isolated test normal-session state, not a real GUI, update or mutation.
The legacy surrogate never starts a native child. It deliberately ignores A to
represent the reviewed O/S-only contract, not certify a released legacy updater.

Actor histories, held-descriptor fstat identities and independent kernel probes
record the relevant ownership. Parent and worker acquisition attempts are
nonblocking. No upgrades, reentrant acquisition or deliberate indefinite waits
are permitted. Both intent checks are recorded in guarded schedules; the negative
control explicitly records the omitted check rather than fabricating its result.

## Fixture, environment, failures and cleanup

W2d reuses the **W2c-only** fixture format. Its transaction names the W2d temporary
root. Publication uses exclusive temporary creation, complete write, file fsync,
atomic no-replace hard link, temporary-name removal and directory fsync. Intent
content/hash/inode and lock-file identities remain unchanged through each
published schedule and until teardown. No intent exists throughout startup_wins.
This is a test format and local process-loss observation, not production journal
compatibility or power-loss durability.

Recorded environment: managed Debian GNU/Linux 13, Linux 6.18.44, Python 3.12.14,
UID/EUID 1000 with zero effective capabilities, roots on tmpfs. All longest-path
mountinfo entries are retained because the environment exposes stacked mounts.
No desktop VM/container, privileged service or task was created.

The [first development attempt](evidence/development-invocation-failure.json)
failed because the actor CLI checked the wrong argument count. Startup exited 1,
the parent recorded barrier EOF and unexpected actor exit, and its root was
removed with no remaining child. That report is preserved under its original
source hash. The argument-count check was corrected. The final native run has
no unexpected failures or cleanup fallback; the detected negative control is an
expected finding, not an undisclosed baseline failure.

[Six focused checks](evidence/local-checks.txt) pass: the oracle uses actual intent
even when the actor skips inspection; recovery rejection is not unsafe admission;
unknown fixtures are preserved at teardown; no signal/disposal occurs for an
unbound live actor; inconsistent held-lock evidence is rejected; known quiescent
teardown succeeds. Mocked ownership and cleanup branches do not constitute extra
native race schedules.

All six actors were joined/reaped: four normal exits 0 and two planned legacy
SIGTERM exits -15. No direct children remained, no cleanup fallback occurred,
all three roots were removed, and their absence was verified separately.
Known fixture removal is labeled teardown_only_removal/not_recovery, after actor
completion. Unknown/replaced files or uncertain process completion preserve the
root and fail. A baseline failure stops dependent schedules and is retained;
expected negative-control detection is handled separately.

## Coverage limits

Two chosen guarded interleavings and one defect control on this Linux/tmpfs
host, not exhaustive concurrency, fairness, repeated-launch or multi-worker proof.
No hostile path/IPC/PID-reuse attack, actual startup/cleanup/fsync fault injection,
protected ownership/ACLs, real legacy packages, production GUI/startup, installer
quiescence, recovery clearance, persistent-storage/power-loss, Windows/Mint desktop,
service lifetime or accessibility validation occurred. Test helpers remain test
code; no production implementation-readiness or blocker closure follows.
