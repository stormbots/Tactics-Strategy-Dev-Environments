# Bounded Windows migration CI efficiency experiment

## Acceptance and constraints

Keep all existing application, trust, bootstrap, manual/scheduled recovery,
signature and actual Mint 22.3 upgrade gates. Do not change release optimization,
runner size, production coordination or package checks. No owner workstation,
protected interruption evidence, release asset or UAT state is touched.

The original Node 26-to-24 test also provisions a real system baseline. The signed
SYSTEM upgrade explicitly requires that baseline, installed package records and
scheduled task on the **same** runner. Moving the whole test without replacement
would break coverage; a synthetic baseline or cross-runner copy is not equivalent.

## Implementation

- `windows-migration` runs the original exact Rust test on a separate Windows 2022
  runner, using the same clean SYSTEM-style environment wrapper, real Node conflict,
  retry/pin assertions and real system setup. Nonzero exit or either missing
  `SKYVIEW_NODE_MIGRATION_OK` / `SKYVIEW_SYSTEM_SETUP_OK` marker fails the job.
- Extract only the existing baseline portion into `Test-WindowsSystemSetupCI.ps1`.
  Both the original Node fixture and a new native Rust baseline test call it.
  All assertions, ordinary provisioning, supervision and narrowly evidenced
  disposable-runner feed retry behavior remain. It is not production recovery.
- Native Rust tests exclude only the relocated Node-conflict test, retaining the
  new real baseline test before signed SYSTEM upgrade. All other tests stay.
- Reuse the native dependency cache namespace for the standalone job; Cargo still
  fingerprints source changes. Never cache installed packages or coordination state.
- The existing `checks` job waits for migration and uses `always()` plus an explicit
  success assertion so failure, cancellation or unexpected skip cannot become a
  successful/skipped acceptance status. Browser/general checks then run unchanged.
  Native and trust jobs remain independent/concurrent. Release also directly needs
  migration. Scope policy classifies the new job as application validation.
- Branch protection inspection returned HTTP 403; repository rulesets listed none.
  No repository settings were changed or claimed verified. Wiring migration into
  the existing `checks` status avoids relying solely on a newly named required check.

This duplicates baseline provisioning on two disposable runners. It should remove
the Node-conflict preparation/migration from the critical native path, **not** all
nine minutes of system setup. Savings are unproven until native CI completes; the
earlier 13–16 minute estimate must not be treated as a commitment after discovering
this dependency. General/browser results also arrive later because their existing
status now incorporates migration. Larger runners/caching changes remain deferred.

## Baseline and measurement

Successful runs before the change (seconds, GitHub jobs API):

| Run | Observed job span | Windows native | Native Rust tests | Completed runner seconds |
| --- | ---: | ---: | ---: | ---: |
| 41321708372 | 1354 | 1345 | 555 | 2384 |
| 41313214988 | 1376 | 1364 | 587 | 2442 |
| 41281623560 | 1438 | 1425 | 657 | 2686 |

Use `python3 tests/ci_timings.py --run RUN_ID` after a run completes. It is read-only,
supports saved jobs API JSON with `--input`, handles pagination and reports per-step
durations, overlapping-job elapsed span and summed completed runner seconds.
The latter is **not** billed minutes or pricing; queue time is not included in the
observed span. Compare full workflow completion and queue delays separately.

Review the first exact-head result for correctness and timing, then compare the
median of three naturally occurring successful warm-cache runs. Do not trigger
extra full runs solely to manufacture samples. Failed/pending runs, feed incidents
and cold-cache effects must be identified, not counted as ordinary speed gains.
Require both success markers, native baseline/upgrade evidence, all inherited
gates and a meaningful elapsed-time improvement before accepting the optimization.
If added runner time or complexity outweighs savings, revise/revert this experiment.

## Local validation and handoff

25 scope/gate/timing tests, eight Mint inventory policy tests, three UAT-version
tests, four command-permission tests and 35 backend contracts pass; changed Rust file passes
rustfmt and whitespace checks. Full-crate formatting reports unrelated existing
differences; none were applied. No local native Windows or browser pass is claimed.
The existing Build workflow owns exact-head Windows/Mint execution and performance
measurement. Do not merge while that validation is pending.

### First native run: missing fixture prerequisites

Build `41325149143` at `126e2d9` failed; it is not timing acceptance:

- The standalone migration regression reached the real system backend, but its
  local `skyview-student-dev` 1.2.1 package had not been built on that runner.
  Restore `choco pack` from the reviewed nuspec there and require the expected
  `.nupkg` file before running the regression. No external package substitution.
- The native baseline test correctly refused GitHub's untracked Node 22.23.4
  installation. Previously the real Node 26 regression replaced that MSI before
  baseline provisioning. A separate disposable-runner wrapper now explicitly
  installs Node 24.21.0 via ordinary Chocolatey/MSI, verifies both its package
  record and actual runtime, emits `SKYVIEW_CI_NODE24_BASELINE_READY`, then runs
  the unchanged real baseline fixture. The Rust test requires both that marker
  and `SKYVIEW_SYSTEM_SETUP_OK`. No force/checksum bypass, fabricated records,
  package removal or production policy change is introduced.
- The existing `checks` gate correctly failed on migration failure. Both trust
  jobs and Linux native/Mint validation passed, but Windows signed upgrade did
  not execute after the baseline failure. All remain required on the fixed head.

26 scope/gate/timing, 35 backend and eight Mint policy tests pass locally after
the correction. Windows runner/package execution and final timing remain pending.
