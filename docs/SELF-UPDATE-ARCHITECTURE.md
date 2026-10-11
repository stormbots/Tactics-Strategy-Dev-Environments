# SDE unattended self-update contract

Status: proposed implementation contract for issue #35; no production updater is
implemented here. Native evidence and outstanding checks are recorded below.

## Scope and decisions

Support Windows 11 x64 per-machine NSIS and Linux Mint Cinnamon 22.x amd64 DEB.
Extend the existing SYSTEM task/root service; keep the GUI unelevated. Do not use
the Tauri GUI updater as the privileged installer or change Mint to AppImage.
No new privileged webview, arbitrary shell command, student-supplied script path,
forced application exit, forced reboot, or unattended baseline provisioning.

The scheduled orchestration must run outside the installed application directory.
It must not keep the application's executable open while NSIS replaces it. A
short-lived native verification helper may exit before installation starts.

The existing weekly schedule is the default check cadence, including its existing
missed-run catch-up. No always-running service or GitHub credentials are needed.
The task must report self-update and development-tool maintenance separately.
An offline update check must not prevent otherwise usable tool maintenance.

## Inspected starting point

Inspected source: `d4df8ac022e6de61520e0942baac9ac8947bcdfe` (SDE 1.2.1).

| Component | Current behavior | Consequence |
| --- | --- | --- |
| `installer/src-tauri/tauri.conf.json` | NSIS `perMachine`, DEB, bundled Windows/Linux backends | Native app installation replaces bundled resources only. |
| `installer/src-tauri/src/main.rs` | Process-local `Busy`; GUI invokes enumerated operations | Does not coordinate different GUI processes or maintenance. |
| `installer/src-tauri/src/process.rs` | Narrow elevated helper, trusted installed paths | Preserve these trust checks; do not add arbitrary executable/path commands. |
| Windows `chocolateyInstall.ps1` | Copies scripts into `C:\ProgramData\SkyviewRobotics`; registers SYSTEM task | App installation alone does not refresh this copy or task. |
| Linux `Install-SkyviewStudentDev.sh` | Copies libraries, updater, units during provisioning | App installation alone does not refresh `/usr/local` scripts or units. |
| `.github/workflows/build-dev-setup.yml` | Both installers and SHA256SUMS; initially prerelease | Existing checksums are integrity evidence, not a pinned-key trust mechanism. |

Current installation paths to confirm in each probe:

- Windows: `C:\Program Files\Skyview Dev Setup\skyview-dev-setup.exe`; bundled
  maintenance resource under `backend\windows\chocolatey\tools`.
- Linux: `/usr/bin/skyview-dev-setup`; resources under
  `/usr/lib/Skyview Dev Setup/backend/linux`.
- Existing Windows task: `\Skyview Robotics - Dev Tool Updates`.
- Existing Linux service/timer: `skyview-student-dev-update.service` and `.timer`.

Resolve Windows paths from the validated machine installation record, then
canonicalize and enforce Program Files ownership/ACL rules. Do not use a user
PATH search, HKCU installation record, or a fallback user-writable executable.
Linux package identity is `skyview-dev-setup`, architecture `amd64`.

## Separate application and applied-baseline state

Track at least `applicationVersion`, `maintenanceEngineVersion`, and
`appliedBaselineVersion`. Do not use Linux's existing provisioning state/version
as the installed application version. Confirm the latter through package metadata;
Windows uses the machine installation record plus executable version metadata.

Installing a new app may update its bundled baseline proposal/default files. It
must not install new managed tools, change Node/Python families, apply required
editor settings, or promote those files to the workstation's applied baseline.

There are two resource generations:

1. **Maintenance engine:** update orchestration, verification, status, and scheduler
   support. Refresh this from the newly verified app without provisioning.
2. **Applied baseline:** tool list, version policies, configuration, and associated
   policy-bearing scripts. Preserve this until an explicitly requested GUI
   Install/Repair/Update applies a baseline under #33's policy.

Until a policy-driven backend exists, retain the currently applied tool-maintenance
script generation rather than blindly copying new hardcoded tool scripts. A
release must not silently reinterpret the applied policy through engine changes.
Shared schema compatibility is an integration requirement with #33; its complete
audit/proposal UI is not a prerequisite for self-update work.

App/bundled engine/deployed engine must agree after an update. A different applied
baseline version is intentional and must be visible rather than called drift.
Never call `choco install --force`, the full provisioning Bash script, or GUI
Repair from an application installer hook merely to refresh maintenance files.

## Bootstrap and generation replacement

Use an administrator-owned external host with immutable, versioned engine
directories and an atomically replaced active-generation receipt:

- Windows: `C:\ProgramData\SkyviewRobotics\SelfUpdate` (SYSTEM/Administrators write;
  Users read-only for status and coordination where needed).
- Linux: `/var/lib/skyview-robotics/self-update` (root-owned; engine directories
  0755, staging/private transaction directories 0700). Configuration under
  `/etc/skyview-robotics/student-dev` remains root-controlled.

A fixed protected launcher reads only a constrained version/generation identifier
from the receipt, never an arbitrary executable/URL/script supplied by a user.
It copies the complete trusted engine generation into a private execution
snapshot, then runs that snapshot. All sourced scripts/modules come from it.
Do not source from a live generation that can change during installation.

The NSIS/DEB packaging hook in #39/#40 installs engine resources and bootstrap
metadata without provisioning. Enable/update the existing scheduler only when a
workstation already has the provisioned-environment marker. On app-only machines,
GUI environment installation establishes the privileged maintenance bootstrap.
Never start maintenance from a package hook. On Linux reload changed unit metadata
without restarting the running service; on Windows preserve schedule settings
and normal-user read access rather than resetting them at every app upgrade.

Replacement protocol:

1. Validate a new engine directory from protected installed resources.
2. Write it completely under a new generation identifier; reject symlinks,
   reparse points, unsafe permissions, and paths escaping the protected root.
3. Validate required files, engine version, and compatible state schema.
4. Atomically publish the new active receipt; retain the prior generation.
5. The current task continues using its snapshot. Only the next invocation reads
   the new generation. Garbage collection excludes active snapshots and retained
   recovery generations; bound retained history (current plus previous).

Do not claim a multi-file filesystem operation is atomic. Receipt publication is
the commit point; package verification and engine activation are separate stages.
Journal each so a crash between them is detectable and repairable.

## Shared coordination contract (#38)

Implemented interfaces, migration boundaries, interrupted-state behavior and tests
are documented in [SELF-UPDATE-COORDINATION.md](SELF-UPDATE-COORDINATION.md). Native
installers must retain the shared installation lease, rather than use a status
snapshot as permission to replace files.


Use two OS-managed gates in an administrator-created protected location:

- **Session gate:** each GUI holds a shared lease for its entire lifetime, acquired
  before webview initialization. Self-installation needs an exclusive lease.
- **Operation gate:** GUI privileged operations and weekly tool maintenance hold
  an exclusive lease for their transaction. Self-installation also needs it.

Windows can use protected lock files with read-only client ACLs and kernel file
sharing semantics: GUI sessions open with shared read access; installation opens
without sharing; operations use a second file without sharing. Linux can use
`flock` on root-created files readable by clients, with shared session leases and
exclusive operation/installation leases. Students must not replace/delete the
files or write privileged state. Read access allowing a lease is not permission
to execute a privileged command. A user-held lease can defer updates; fail closed.

All acquisitions are nonblocking. The installer acquires operation then exclusive
session gates and releases both if either fails. GUI acquires its session lease
first and attempts the operation gate without waiting. This avoids deadlock and
the check-then-install race. New sessions encountering an installation gate show
a brief “SDE is being updated” message without starting provisioning. Never launch
the GUI automatically under SYSTEM/root after installation.

Locks are handle-based, released on process exit/reboot; PID/status files are
diagnostics, not the lock authority. Every real backend entry point, including
manual supported scripts, must use the gate. Helpers inherit/retain transaction
ownership so GUI exit cannot release the gate while a backend keeps running.
Do not hold an operation gate across a helper that tries to reacquire it: pass a
validated inherited handle or retain a supervising owner for the complete chain.
Snapshot generation and lock lifetime must cover all child processes.

Run tool maintenance under the applied-baseline generation, then release its
transaction gate before attempting self-installation as a separate transaction.
If busy, mark deferred and try on the next scheduled invocation. Never delete
APT/DPKG locks, kill an editor, or stop another package transaction.

## Release selection and authenticity (#36/#37)

Use the official `stormbots/Tactics-Strategy-Dev-Environments` releases API with
bounded pagination. Select the highest compatible semantic version, strictly
newer than the actual installed app; exclude drafts, prereleases, semantic
prerelease versions, and legacy `windows-v…`/`linux-v…` tags. Do not rely only on
GitHub's “latest” setting or lexicographic ordering. Do not fall back to an older
candidate after rejecting a newer candidate's signature.

Chosen format: a small UTF-8 `sde-update.json` plus detached Minisign signature
`sde-update.json.minisig`. Verify the exact downloaded bytes using a pinned public
key and a maintained implementation before interpreting installation fields.
Metadata includes schema version, stable channel, repository, release tag,
semantic version, minimum supported engine/schema, and platform entries with
exact installer filename, byte length, and SHA-256. The release tag/version must
match the GitHub candidate and package identity; unknown schemas fail closed.

The signed hash authenticates the installer; a separate installer signature is
optional rather than a second required signing scheme. Keep existing SHA256SUMS
for human downloads. Do not trust API-provided digests/checksums alone. A hash
manifest fetched beside an installer is not independent proof of authenticity.

Keep the private key in protected Actions signing secrets and back it up offline.
Production signing/publication requires release approval. Stable eligibility
requires both authenticated `stable` metadata and GitHub non-prerelease status.
Candidates can carry signed stable-intent metadata while GitHub marks them
prerelease; they remain ineligible until approved promotion. Fixtures use a
separate test key/repository endpoint that production configuration cannot select.
Plan key rollover through an already trusted release before changing the key.

Allow HTTPS requests only to the fixed repository's API/release routes. Validate
initial installer URLs against the selected tag and exact asset; explicitly allow
only GitHub's required HTTPS asset/CDN redirect hosts, a bounded redirect count,
and no URL credentials. Never execute a redirect target before signed verification.
The concrete host list and redirect tests belong to #37. Apply maximum metadata
size (64 KiB), installer size (512 MiB), response timeout (30 seconds), and total
download deadline (10 minutes); make deviations an explicit reviewed contract
change. Retry transient requests at most twice with bounded backoff and honor
rate-limit reset only within the transaction deadline. Otherwise retry next week.

Download to fresh exclusive files in protected staging. Validate ownership/ACLs,
reject links, enforce size, close the download, then verify hash. Keep files
protected until the native installer opens them. Journal candidate and verified
hash before execution. Read-only #11 discovery shares semantic selection but
never installs or grants the GUI a privileged arbitrary-path interface.

## Native installation contract

### Windows

Implemented host, engine-generation, pause and native verification behavior is
documented in [SELF-UPDATE-WINDOWS.md](SELF-UPDATE-WINDOWS.md).

Execute the protected staged NSIS installer as SYSTEM with `/S /UPDATE`; do not
pass `/R` (Tauri's application relaunch flag), `/P` (passive UI), or `/D` overrides.
`/S` is case-sensitive. Use the existing registered machine location after trust
validation. The probe uses `/S` for initial installation and `/S /UPDATE` for
upgrade. The locked Tauri CLI is 2.12.1; its NSIS template recognizes `/UPDATE`
and starts the app from a silent install only when `/R` is supplied.

Wait for completion, retain the operation/session gates, and record the numeric
exit. Exit zero is necessary but not sufficient: verify expected executable
version, machine registration, bundled resources, and engine receipt. Treat every
other exit as failure unless a specific reboot-required code is established by
native evidence. Record reboot-needed separately; never reboot automatically.
Do not impose a timeout by forcibly killing an installer. A supervising watchdog
can flag a long-running transaction while retaining coordination.

### Linux

As root, install the verified absolute DEB path using
`DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Lock::Timeout=60 --no-remove
install <protected-absolute-path.deb>`. Use a sanitized system environment/PATH.
Use noninteractive needrestart policy where present; do not auto-reboot. Do not
perform a distribution upgrade or invoke full SDE provisioning.

Dependency resolution may install needed app libraries, not managed development
tools. Bound download operations; defer on contention after the lock timeout.
Never use `--allow-unauthenticated`, force-remove packages, or delete locks. APT
exit zero must be followed by package `install ok installed`, exact version and
amd64 identity, required resources, and committed engine receipt. Record nonzero
status and leave package-database recovery to documented mentor procedures.

## Failure, status, and recovery (#41/#42)

Persist a schema-versioned protected transaction journal and atomically publish
read-only sanitized status: current/candidate versions, applied baseline, engine
version, stage, outcome, UTC timestamps, native exit, and log reference.

Outcomes: `current`, `paused`, `deferred`, `unavailable`, `failed`, `updated`.
Do not report current after a failed check or updated after only a download.
Track tool-maintenance outcome independently. Keep administrator-controlled pause
configuration separate from app package files; pause blocks self-installation,
not development-tool maintenance. Recheck pause immediately before execution.

Failures before execution leave the installed app intact. A crash after installer
start is not evidence of a working previous app. On next run, inspect the journal,
package state, resources and receipts before allowing another transaction. If
inconsistent, stop automatic installation and report mentor recovery required.
Do not blindly resume or repeat an unknown interrupted package transaction.

Retain the verified previous installer, hash/signature evidence, prior engine,
and prior receipts. Bootstrap must cache/verify the baseline installer while it
is available; if missing, report reduced recovery capability. Recovery reinstallation
is an explicit mentor action under the same locks. No universal automatic rollback
is promised: NSIS/DEB downgrade and interrupted-install recovery need separate
native tests before automation. Never delete student files to recover the app.

## One-time migration

The first updater-enabled release must be installed once using the normal native
installer with administrator approval. Its narrow packaging hook seeds trusted
engine state and refreshes the existing scheduled host without applying a baseline.
Preserve existing task/timer settings, runtime policy, repository configuration,
and user settings. A laptop with only the app installed receives engine files but
does not start provisioning or enable tool maintenance until GUI Install.

Legacy copied scripts must be captured as the applied-baseline generation before
switching scheduler entry points. Missing/unsafe legacy state must be reported for
mentor repair, not guessed from whichever baseline ships in the new app. Record
that pre-update releases lack signed recovery assets; seed a verified recovery
installer for the updater-enabled version before later automatic upgrades.

Subsequent accepted stable releases update through weekly maintenance. Initial
rollout uses representative laptops before the wider fleet. Administrator pause
and previous-installer recovery must be available before enabling production.

## Verification evidence and gates

The accompanying workflow probes archived v1.2.0 → v1.2.1 installers, verifies
their published SHA256SUMS, and uses disposable runners only. This is inspection
of known release behavior, not production pinned-key verification. It must never
publish assets or promote a release.

- Windows probe: scheduled SYSTEM worker; silent install/upgrade exits, expected
  executable version/path, bundled backend, no GUI launch, no external maintenance
  provisioning, and a student-file sentinel.
- Linux probe: actual root APT install/upgrade, DEB metadata/control inspection,
  package state/path/resources, no provisioning/GUI launch, and a sentinel.
  Ubuntu 24.04 is supporting package evidence, not Linux Mint acceptance.
- Existing source/static checks remain applicable. This PR adds no production
  installer hooks, coordination implementation, signing key, or automatic updater.

Native run results will be recorded in `SELF-UPDATE-VERIFICATION.md` before this
contract is presented as ready for review. Windows Server CI cannot establish
Windows 11 UI/UAC behavior; Ubuntu CI cannot establish Mint PolicyKit/Cinnamon
behavior. Those platform-specific checks remain explicit owner UAT in #43.

Before production (#39–#43), verify new bootstrap hooks, preserved custom schedules,
engine/applied-baseline separation, handle inheritance, inactivity races, APT
contention, signature rejection, interruption recovery, and next-run maintenance
on supported native platforms. Archived-installer probes do not prove these new
features. Do not close their acceptance gates based on build success alone.

## Source references and issue boundaries

- [Tauri 2.12.1 NSIS template](https://github.com/tauri-apps/tauri/blob/tauri-cli-v2.12.1/crates/tauri-bundler/src/bundle/windows/nsis/installer.nsi)
- [NSIS silent installation reference](https://nsis.sourceforge.io/Docs/Chapter4.html)
- [Tauri updater packaging/signature constraints](https://v2.tauri.app/plugin/updater/)
- [APT command documentation](https://manpages.debian.org/bookworm/apt/apt-get.8)
- #36: signing/verification format and pipeline; #37: selector/network/staging.
- #38: coordination; #39/#40: native hooks and installation.
- #41: controls/status/recovery; #42: end-to-end evidence; #43: UAT/migration.
- #11 stays notification-only; #8 shares interruption state; #10 shares maintenance
  notices; #33 owns baseline application. These integrations are not circular
  requirements to finish unrelated UI before implementing the engine.
