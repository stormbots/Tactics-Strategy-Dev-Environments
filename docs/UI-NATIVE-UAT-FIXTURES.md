# Controlled native UI UAT fixtures

These helpers support the [milestone UAT plan](UI-MILESTONE-UAT.md). They do not
install SDE, run an operation, change application versions, dispatch a workflow,
sign artifacts, publish releases, or change application-update policy.

## Status and responsibility

Implemented: `tests/native_uat_fixtures.py`, one shared Python CLI for Windows and
Linux Mint. Local tests exercise real Git and filesystem restoration in temporary
roots, with platform identity and target locations substituted. The fixture-only
Actions workflow exercises actual Windows ACL/CLI behavior and
authenticated Mint userland as a non-root account. It builds no application and
installs no SDE package. See the [verification evidence](UI-NATIVE-UAT-EVIDENCE.md)
for exact runs, results and remaining desktop UAT. Neither platform’s application
UI is accepted by helper automation.

Codex prepares the VM and runs the commands below. The owner tests the UI and
returns observations; the owner is not expected to write scripts or break tools.

## Prerequisites

- For owner UI UAT: a disposable Windows 11 or Mint Cinnamon 22.x desktop VM,
  dedicated test account, and a snapshot captured before fixture enrollment.
  For helper automation: an ephemeral Actions Windows VM or authenticated Mint
  container with synthetic configuration and a dedicated fixture profile/account.
  The legacy `--acknowledge-disposable-vm` flag also acknowledges that disposable
  CI environment; it does not assert a booted desktop or establish UI acceptance.
  The helper cannot prove disposability and is not a security boundary against
  the same local account.
- For application UAT, a separately authorized, correctly versioned test build.
  Helper-only automation does not need an SDE build. Current development
  bundles are not upgrade instructions for the owner's installed v1.2.7.
- For application UAT, a completed healthy native Validate report. Save its log and the app/source,
  baseline, schedule and pause-policy record from the consolidated plan.
- Python 3, Git, and a new private state-directory path outside Development.
  Use the dedicated desktop account throughout. Mint rejects root execution;
  do not use sudo to change which profile is under test.
- The target configuration must already exist and be writable to that account.
  The helper never elevates or grants permissions. For machine-wide repository
  CSV access or Windows workspace rename permissions, Codex/mentor must prepare
  permissions on the disposable VM before its snapshot. If unavailable, record
  the case Blocked. Never grant such access on a student workstation.
- Close SDE and editors before setup/restoration. Run only one helper at a time.
  Keep scheduled maintenance from overlapping through the lab's planned test
  window; no schedule or policy changes are performed by this helper.

## Commands (Codex operates these)

Run from the repository root. Substitute the real fixture-state path once and
reuse it. It must not be inside Development. Windows PowerShell examples:

```powershell
python tests/native_uat_fixtures.py enroll --state-dir "$env:LOCALAPPDATA\SdeNativeUat" --acknowledge-disposable-vm
python tests/native_uat_fixtures.py apply --state-dir "$env:LOCALAPPDATA\SdeNativeUat" --case git-manual
python tests/native_uat_fixtures.py status --state-dir "$env:LOCALAPPDATA\SdeNativeUat"
python tests/native_uat_fixtures.py restore --state-dir "$env:LOCALAPPDATA\SdeNativeUat"
```

Mint Bash equivalents:

```bash
python3 tests/native_uat_fixtures.py enroll --state-dir "$HOME/.sde-native-uat" --acknowledge-disposable-vm
python3 tests/native_uat_fixtures.py apply --state-dir "$HOME/.sde-native-uat" --case git-manual
python3 tests/native_uat_fixtures.py status --state-dir "$HOME/.sde-native-uat"
python3 tests/native_uat_fixtures.py restore --state-dir "$HOME/.sde-native-uat"
```

Choose one case below, apply it with SDE closed, open SDE and run Validate, perform
the UI observations, close SDE, restore, then rerun native Validate and compare to
baseline. Export evidence before reverting a snapshot. A helper success verifies
its own target, not the whole workstation; the native report is still required.

## Cases and expected outcomes

| `--case` | Preconditions and controlled change | Native expected diagnostic and UI |
| --- | --- | --- |
| `workspace` | Existing **empty** `C:\Development` on Windows or `~/Development` on Mint. Rename to adjacent `Development.sde-uat-parked`; never move files/projects. | Windows `FAIL Development folder`; Mint `FAIL Development workspace missing: <home>/Development`. Repair guidance. Review Repair selects Overview/Repair without native work or elevation. |
| `git-manual` | Existing `.gitconfig`; effective global `init.defaultBranch` is `main`; no Git configuration environment overrides or additional XDG Git config. Save exact bytes, use Git to set `uat-fixture`. | Windows `FAIL Git default init.defaultBranch = main`; Mint `FAIL Git init.defaultBranch is not main`. Manual guidance, original diagnostic expandable, no automatic Repair action for this row. |
| `mentor-repository` | Installed repository CSV contains **only** its stock header. Add one enabled missing project `sde-uat-missing-project` with non-routable `https://example.invalid/uat-only.git`. Refuse if that project path exists. | Windows `FAIL Configured repository: sde-uat-missing-project`; Mint `FAIL Configured repository missing: <home>/Development/sde-uat-missing-project`. Mentor guidance; do not imply project loss. |

For `mentor-repository`, run **Validate only**. Do not run Install/Repair/Update
with the deliberately invalid repository configured. Restore it before other
operations. Existing nonempty repository configurations are rejected wholesale.

For appearance changes during a real elevated Repair, use the workspace snapshot
only, after separately confirming the full operation scope and network access.
Repair can recreate Development, change other configuration, and install/update
tools. Export the log, then **revert the entire VM snapshot**. The helper refuses
to merge a recreated workspace with its parked original. This case is not a
promise of single-check Repair or helper-only rollback of a full operation.

## Restoration and interruption behavior

- One active fixture per state directory. A host/account/home-bound ledger saves
  original bytes or the parked path before mutation. The directory is private
  (0700 on Mint; explicit current-user inherited ACL on Windows). Git backups may
  contain private configuration: do not upload the ledger or state directory.
- Linked/junction paths and hard-linked configuration files are rejected.
- Repeated restoration after success is harmless. If interrupted after saving
  intent but before changing the target, restoration accepts the original state.
- Changed/deleted configuration, new workspace content, recreated Development,
  or unexpected parked paths cause a refusal without deleting the new content.
  Preserve evidence and revert the VM snapshot; do not force restoration.
- An exclusive operation lock prevents overlapping CLI mutations. A killed helper
  may leave the lock: use snapshot recovery rather than deleting it and guessing
  whether mutation finished. Loss/corruption of the ledger also requires snapshot
  recovery. No recovery command fabricates original state.

## Remaining controlled cases

| Case | Preparation / acceptance |
| --- | --- |
| Healthy, optional identity/authentication | Use the baseline snapshot and dedicated account; do not log into real student accounts. Run actual Validate. |
| Intentionally disabled task/timer | Use a separately prepared VM snapshot. These helpers do not control system schedulers. Confirm mentor/read-only Schedule guidance, then revert the snapshot. |
| Managed tool update | Use a separately prepared, known supported older-tool snapshot and genuine current package-source metadata. Do not downgrade the owner's tools or fabricate metadata. If no candidate exists, record Blocked/Not run. |
| Runtime/unknown failure and suffix regression | Retain existing automated fixtures separately. These helpers do not replace commands, inject backend events, or modify the installed validator. A real native case remains Not run unless independently available. |

For every native case record OS/webview, source/build identity, original report,
page/theme/zoom/window/OS scale, observed versus expected behavior, keyboard and
screen-reader findings, log, restoration outcome and post-restore Validate report.
Apply the full theme/zoom/accessibility matrix from the consolidated plan.

## Deferred versioned test-build recommendation

Recommend numeric application identity **1.2.8**, published as a testing prerelease
only if separately authorized. Read-only GitHub inspection on 2026-10-15 found no
`v1.2.8` tag; recheck before allocating it. Do not reuse v1.2.7 or use a suffixed
identity that the current canonical numeric-tag validator rejects.

The current candidate helper and tests support only 1.2.2–1.2.7; supporting 1.2.8
requires a later reviewed change. Both native packages must use one reviewed
source commit and consistent npm/Tauri/Cargo/lock identities, leaving development
tool baseline/dependency identities unchanged. Require exact-source CI, package
identity verification, authenticated artifacts and explicit installation
instructions before handing builds to the owner. Any changed published candidate
needs a new version. Build dispatch, signing, publication and stable promotion
remain deferred; no such changes accompany these fixture helpers.

## Fixture-only CI

`.github/workflows/native-uat-fixtures.yml` runs on relevant pull requests and
pushes to the dedicated `qa/native-uat-fixtures` branch. Workflow lint runs alongside
the Windows/Mint jobs. Windows uses the real runner filesystem and .NET
ACL implementation. Mint uses the existing signed-ISO extraction procedure,
then runs the helper as a non-root test account in that genuine Mint userland.
The CLI smoke test substitutes no platform identity or target paths: it enrolls,
applies and restores all three cases at their actual platform locations. Its
Git profile contains only synthetic test data. It also checks drift refusal.

This differs from the local unit suite, which substitutes platform/target paths.
CI does not install SDE, run a native application Validate report, exercise a
desktop/screen reader, or run Repair. Those acceptance checks remain pending.

The application workflow now starts with a tested scope classifier. A PR whose
changes are entirely in the explicit fixture/support path set skips the existing
`checks`, `native`, and `update-trust` jobs. Mixed or unknown changes retain all
application checks. Workflow integration itself is permitted only when parsed
application/release jobs and triggers are unchanged after removing the scope job
and its three exact gate conditions. Shared Mint image preparation changes still
require application checks. Git diffs use the merge base, include all names, and
treat renames as old/new paths. Push/manual/tag events retain full application CI;
merging to main can therefore build SDE and is a separate step while builds are
deferred. No release/signing behavior was changed.

`python3 -m unittest discover -s tests -p test_ci_scope.py -v` verifies this policy.
The lightweight `scope` job and the three fixture workflow jobs must pass before
considering this PR ready; application jobs shown as skipped are expected for
fixture-only PRs. Success artifacts contain unit output and a small JSON evidence
record, never the private ledger/configuration backup.
