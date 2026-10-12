# Unattended Windows application installation (#39)

The per-machine NSIS package now bootstraps a protected external maintenance host
at `C:\ProgramData\SkyviewRobotics\SelfUpdate`. Its fixed schema-1 PowerShell launcher
accepts no installer path, URL, key, executable or script argument. It requires
SYSTEM, validates the protected receipt/engine, and copies the complete engine
(binary plus version receipt) into a private per-invocation snapshot. The worker
runs outside Program Files, so it does not keep the installed application or its
bundled verifier open while NSIS replaces them. The privileged GUI interface is
unchanged. The hook selects the native Windows shell and the bootstrap pins its
module path to native system modules. This also handles installers started from
PowerShell 7, whose module paths otherwise leak through intermediate processes
([Microsoft explanation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_psmodulepath?view=powershell-7.6)).

## Expected behavior

The existing weekly SYSTEM task runs development-tool maintenance first using the
currently deployed applied baseline, waits for its script/children, then considers
application installation as a separate transaction. A failed/offline GitHub check
cannot prevent that earlier tool work. Tool exit and self-update outcome are
reported independently. Contention is deferred (task exit 75); ordinary failure
returns 1. An app-only installation creates engine resources but neither registers
nor starts tool maintenance. GUI baseline Install/Repair registers the existing
task against the external host when present.

An embedded supervisor acquires the shared operation lease before reading the
applied scripts. It copies the updater, Node helper/policy and coordination module
into the private invocation snapshot and holds its transaction through the child
PowerShell process. Concurrent mentor Repair cannot mix script generations. These
copies come from the applied baseline, not the newly bundled baseline proposal.

The worker uses #37's fixed-repository discovery and protected staging. Only a
newer compatible stable release, excluding GitHub drafts/prereleases and semantic
prerelease versions, is eligible. Candidate signing does not approve promotion.
After download it rechecks GitHub eligibility, acquires #38's operation and
exclusive session leases, rechecks installed identity and pause policy, repeats
pinned Minisign verification and the payload hash/length check, then writes durable
installation intent before running the protected NSIS asset with **`/S /UPDATE`**.
No destination override, passive UI, relaunch flag, forced GUI closure or reboot
is requested. The worker waits without killing a long-running installer.
Child processes use the established sanitized Windows backend environment,
including SYSTEMDRIVE, native modules and fixed SYSTEM profile folders needed by
Windows known-folder APIs. They inherit no student profile or executable/module
search paths.

Exit **0** requires matching machine registration/executable version, required
bundled files, and an active engine receipt whose verifier bytes match the newly
installed bundle before reporting `updated`. Exit **3010** records
`rebootRequired=true` but is not accepted as proven NSIS success; it requires
mentor review and retains interruption intent. Every other nonzero result also
requires review. MSI success codes are not assumed to establish NSIS success.
A launch/wait error, post-check failure, crash or reboot leaves the coordination
journal and blocks automatic retry. Recovery controls belong to #41; there is no
automatic rollback or blind repetition of an uncertain installation.

## Engine and baseline separation

The packaging hook creates a new protected immutable UUID engine generation and
atomically publishes `active.json` only after its files exist. It preserves the
previous engine receipt and retains current plus previous generations. Running
tasks use their private snapshots; only the next invocation selects the new
receipt. A snapshot left by an abrupt launcher crash is preserved for diagnosis;
normal completion removes only that invocation's known files.

The hook never invokes Chocolatey, provisioning, Repair or a baseline updater. It
never copies newly bundled policy-bearing tool scripts over the deployed baseline.
Node policies, editor settings, repository configuration, projects, credentials
and workspace files remain independent of application installation. The existing
deployed scripts remain the applied maintenance generation until an explicit GUI
baseline action changes them; #33's complete baseline version/proposal UI remains
separate work. Status identifies this preserved generation and reads its baseline version from the protected installed Chocolatey
metapackage when available. Missing/untrusted baseline metadata is reported as
unknown; the newly installed application version is never substituted.

For a provisioned machine the hook changes only the existing task's action and
restores normal-user read permission. It preserves custom triggers/settings,
principal and enabled/disabled state, and never starts the task. Missing tasks are
not silently registered by application installation. An older uncoordinated
baseline needs the one-time mentor Repair migration described in
[SELF-UPDATE-COORDINATION.md](SELF-UPDATE-COORDINATION.md); disable its old schedule
and wait for all package work before migration. Never kill package transactions.
The initial schema-1 launchers are installed once; a future incompatible launcher
schema requires an explicit migration rather than in-place replacement while it
is running.

## Pause, state and recovery retention

`policy.json` is administrator-controlled, schema 1, with a `paused` boolean.
Bootstrap creates it with **paused=true** and preserves an existing policy on
upgrade. This deliberately keeps fleet self-installation off pending #41's mentor
controls, #42's end-to-end tests and #43's owner acceptance. Pause blocks app
self-installation, not tool maintenance. Unsupported Windows editions/architectures
also fail closed; production discovery supports Windows 11 x64, not CI Server
2022. Do not enable production based only on CI success.

`status.json` is atomically replaced, then given standard-user read-only access.
It records application/engine versions, preserved applied baseline, separate tool
exit, candidate, native exit, reboot requirement, timestamps, outcome and sanitized
failure detail and a private transcript reference. The launcher keeps eight
completed transcripts plus any active/crashed invocation logs. Other state, snapshots, staging, installation journal and recovery
receipts stay administrator/SYSTEM writable; private payloads stay unreadable to
students. #41 will add mentor controls and GUI status integration.

Before an upgrade the worker attempts to cache the exact currently installed
stable signed installer and evidence. Older unsigned releases cannot supply this;
`recoveryAvailable=false` reports reduced previous-version recovery capability.
Never invent authentication for an archived checksum-only release. A successful
installation retains its installer/manifest/signature as current recovery material
and retains the previous recovery receipt/assets when available. Under the
operation gate, staging cleanup keeps those two sets and removes only known files
from other UUID transactions; unknown/link/unsafe state requires mentor review.
An interrupted install blocks cleanup and new work. Recovery is an explicit mentor
action under the same coordination contract, not an automated downgrade.

## Automated verification and owner UAT

Required CI builds an unpublished newer fixture and runs the same native
installation path under a scheduled SYSTEM task, upgrading 1.2.1 to 1.2.2. A key
created only inside that test authenticates fixture metadata; production's pinned
key rejects it and neither the production CLI nor environment can select it.
The native test checks tampered metadata rejection, real session deferral,
installer exit, registration/executable version, engine activation, baseline and
student sentinel preservation, no SYSTEM GUI launch, and coordination completion.
The required package bootstrap first installs on an app-only runner and asserts
that it creates no applied baseline/task and defaults to paused. Full provisioning
then establishes the baseline/task; the upgrade test retains customized disabled
scheduling settings through the hook. It also checks payload tamper rejection and
a signed synthetic failing executable: durable intent survives and blocks retry
without terminating any package process.

An early native check validates the real installed registry/PE identity before
provisioning. Windows permission tests distinguish inherit-only rules (which grant
no access to their current object) from effective inherited student-write grants
on child files, which remain rejected.
Windows' inherited TrustedInstaller control is accepted only on canonical
Program Files directories and platform anchors. Executable files and private
payload/state objects retain administrator/SYSTEM ownership and write rules; the
native permission regression verifies servicing control is rejected on a private
staging directory.

The next-run fixture executes the actual fixed launcher and packaged production
worker with a deterministic no-package tool script, restoring the applied script
in `finally`. It confirms the new engine and independent tool result. Production
OS detection correctly rejects the Server runner for release discovery. This
fixture does not promote an asset or claim Windows 11 desktop/UAC acceptance.
Existing required coordination, signature/tamper, protected staging, full Windows
provisioning, frontend, Linux and package bootstrap regressions still run.

Remaining #42/#43 UAT: representative Windows 11 school laptops, the first
administrator-approved migration, custom schedules/runtime policy and real
student profiles, missed weekly runs/offline recovery, live GUI deferral, actual
approved stable release selection, reboot-required/interrupted package recovery,
and mentor pause/recovery controls. Full rollback is not promised.

Mentor pause/resume, status interpretation and platform recovery are documented
in [SELF-UPDATE-MENTOR.md](SELF-UPDATE-MENTOR.md). Only non-secret `policy.json`
and sanitized `status.json` are readable by students; other receipts remain private.
