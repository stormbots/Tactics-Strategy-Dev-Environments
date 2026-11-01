# Windows CI efficiency: measurement and coordinator caching

## Current scope

Keep the original execution topology and every existing acceptance gate. Cache
the coordinator Cargo target in both native and update-trust jobs, alongside the
already cached application/updater targets. Previously the standalone coordinator
target was omitted and native initialization rebuilt it (31 seconds in the most
recent successful run). Cargo still fingerprints current source and dependencies;
this caches build artifacts, never installed packages, journals or runner state.
No compiler optimization, runner size, production logic, version or release changes.

The original full Node 26-to-24/system-setup Rust test again runs in the native
Windows job before the signed SYSTEM upgrade. All assertions, clean-environment
wrapping, package checks and inherited native/actual Mint 22.3 gates are unchanged.
There is no separate migration job, duplicate baseline or delayed browser job.
Existing checks and release dependencies remain exactly as on main.

## Rejected parallel-provisioning experiment

PR #144 first separated the full migration regression onto a Windows runner and
provisioned a second real baseline on the native runner. The latter is necessary:
the signed SYSTEM upgrade explicitly requires the actual installed baseline,
package records and scheduled task on that same machine, not synthetic copies.

The first split run (41325149143, head 126e2d9) exposed missing local package and
hosted Node prerequisites. Correcting those only in disposable fixtures produced
a completely successful Build 41327041770 at head
340adf7be110197da4b98754850915a572bd3f2a. Both original migration markers,
106 native Windows tests, signed SYSTEM upgrade, all trust/general checks and
actual Mint 22.3 signed upgrade passed. No gate was waived.

However, the full elapsed span was 1311 seconds (21m51s) and summed runner time
3336 seconds (55m36s). Against the prior three-run median, that saves just 65
seconds (4.7%) while using 894 additional runner seconds (36.6%). One sample is
not statistical proof of a speedup; the duplicated provisioning is a structural
cost and does not justify adoption on this evidence. The split and all its test/
fixture changes are removed. Its successful validation is historical evidence,
not acceptance of the subsequent cache-only head.

## Baseline and measurement

Successful pre-experiment runs (seconds, GitHub jobs API):

| Run | Observed job span | Windows native | Native Rust tests | Completed runner seconds |
| --- | ---: | ---: | ---: | ---: |
| 41321708372 | 1354 | 1345 | 555 | 2384 |
| 41313214988 | 1376 | 1364 | 587 | 2442 |
| 41281623560 | 1438 | 1425 | 657 | 2686 |
| Split experiment 41327041770 | 1311 | 1298 | 528 | 3336 |

Use `python3 tests/ci_timings.py --run RUN_ID` after a run completes. This read-only
tool supports saved jobs API JSON via `--input`, pagination, per-step durations,
overlapping-job elapsed span and summed completed runner seconds. Runner seconds
are **not** billed minutes or pricing. The observed span excludes queue time;
check total workflow completion and queue delays separately.

Review the cache-only exact-head native CI first, then the median of three
naturally occurring successful warm-cache runs. Do not launch extra full builds
solely to manufacture samples. Cache restore/save overhead may offset compile
savings; compare coordinator initialization plus total elapsed/runner time.
Cold caches, failed runs and feed incidents must not be presented as ordinary
performance results. No unmeasured speed guarantee or broader tuning is approved
by this document.

## Validation and safety

Local tests verify timing calculations, pending/failure handling, coordinator
cache coverage, original job/dependency topology and unfiltered native test
invocation. Authoritative Windows/Mint, signed-upgrade, trust and browser evidence
must come from the full Build workflow on the latest exact head. Do not merge
while it is pending. Branch-protection inspection returned 403 earlier; no GitHub
settings were changed.

Owner Windows interruption evidence and Mint v1.2.18's 35/0/0 acceptance remain
untouched. No owner workstation, signing, publication or UAT action occurred.
