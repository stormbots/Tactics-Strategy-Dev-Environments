# Read-only validation and self-service recovery guidance

Branch: `codex/recovery-readonly-diagnosis`.
Base: accepted #124 head `8935a4137ca67fa26b4c61f3f4e4ca0cea90e12e`,
[Build 41074586107](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41074586107),
attempt 2, full success. Attempt 1 hit a Chocolatey PyCharm-feed HTTP 504; the
fixture correctly refused an in-place retry while package processes remained.
The fresh-runner retry passed without changing source or waiving a check.
Both signed native paths emitted `SDE_RECOVERY_APPLICATION_INSTALL_CONTRACT_OK`;
Windows SYSTEM upgrade, actual Mint 22.3 upgrade and all inherited checks passed.

## Bounded T6 task

Readiness validation is diagnostic, not proof that an interrupted package
operation finished. Keep the old evidence and decision separate from its result.

- Linux's public bundled validator uses a dedicated read-only coordination mode.
  It acquires the same trusted operation gate and shared session lease, but does
  not read private journal contents, create a transaction, prepare incident
  metadata, submit intent, archive, acknowledge or clear evidence. A journal's
  presence (even malformed private contents) does not by itself block diagnosis.
- This mode is NOT a generic command runner around an interruption. It accepts
  only `/bin/bash`, an absolute protected `Validate-SkyviewStudentDev.sh`, and
  optionally `--check-updates`. File/ancestors must be root-owned and not writable
  by others; reject links, non-regular files, extra options and other commands.
  Real inherited descriptors remain required for normal nested script execution;
  no environment boolean creates a bypass or OS privilege.
- Another participating SDE operation still excludes validation through its
  physically held gate. Nonparticipating external package activity can make
  version/status results transient; these are read-only snapshots, not native
  inactivity or change authorization. Wait for known package work to finish and
  recheck before relying on readiness. All actual mutations retain the fresh
  native activity/health and old-process-lifetime checks from ADR 0002.
- Windows retains its existing `-ReadOnly` gates and evidence-preservation
  behavior. Both wrappers now explain that Validation does not acknowledge the
  incident or authorize changes, instead of referring the student to servicing
  by a mentor. Real validation exit codes are preserved, including readiness
  failure on an incomplete app-only fixture.
- The frontend no longer acknowledges/deletes a user incident merely because
  Validation succeeded. It retains the Recovery destination and explains the
  distinction. Existing full Repair completion behavior is unchanged; final
  explicit acknowledgment/report/resume integration belongs to T7/T8.
- Existing validation guidance keeps narrow matching and no inferred repair for
  unknown text. Runtime, platform, repository and schedule uncertainty now offer
  self-service diagnostic review, setup requirements and support-report retention,
  not mandatory mentor servicing. Repair/Update suggestions remain explicit,
  scoped, user-started operations with normal OS authentication. Arbitrary raw
  errors remain escaped plain text, never executable instructions.

## Shared native guidance contract

`coordination::guidance` maps the existing typed observation/decision to bounded
serializable explanations for later report/Recovery consumers. It is data only:
no command execution, deserializable permit, token, raw journal or boot key.
The final frontend safety-observation wiring is still T7/T8 work; do not claim
that this pure contract alone changes admission or completes the Recovery UI.

- Active activity: wait/recheck; never kill installers or remove locks.
- Unknown activity: save work, normal Restart, Check Again. Restart is not
  consent or healthy-package proof; first-captured legacy provenance may need
  a further normal Restart. Persistent failures retain diagnostics for sharing.
- Unknown/untrusted coordination: retain evidence; never loosen permissions or
  replace gates. An authenticated SDE installer can repair a damaged application,
  not certify or acknowledge its old transaction.
- Positive Linux package damage: pause app updates, inspect `sudo dpkg --audit`,
  review `sudo apt-get --simulate --fix-broken install` before approving changes,
  and use `sudo dpkg --configure -a` only for reported unfinished configuration.
  These existing native steps come from the repository's self-update runbook;
  they are conditional, system-wide, normally authenticated manual operations.
- Positive Windows Installer damage: identify the affected installer from its
  own error/log and use its supported Resume/Repair path (Installed apps may
  offer Modify/Repair). Never delete Installer registry state or locks. No
  generic Windows cleanup command or automatic package repair is introduced.
- Unknown health alone remains a warning once inactivity is established; it
  must not be recast as damage. Acknowledge/recheck guidance never promises that
  passing Validation resolves the incident.

The runbook's interrupted-package section now assigns these self-service steps
to the administrator-capable student, not a mentor. Unrelated historical release
and support documentation is not rewritten here.

## Native acceptance and limits

The installed Linux manual verifier now runs the actual bundled validator with
an unacknowledged retained journal both as root and UID 65534. It must emit its
real completion summary and interruption warning, preserve the original bytes,
inode and modification time plus every coordination-state file, and leave no
archive/acknowledgment side effect. This runs on the host AND actual Mint 22.3;
both paths must emit `SDE_RECOVERY_LINUX_READONLY_VALIDATION_OK`.

The existing Windows native coordination fixture still invokes both real public
validators against its synthetic private journal, requires summaries/real exits,
unchanged original bytes/private ACLs, continued mutation blocking and active-gate
deferral. Its new `SDE_RECOVERY_WINDOWS_READONLY_VALIDATION_OK` marker is mandatory
in the NSIS packaging path. This fixture is elevated; it is not new Windows
standard-user validation proof. Existing standard-user storage/acknowledgment,
manual, trust and signed SYSTEM-upgrade checks remain required.

Two new protected Linux Python tests cover read-only evidence/object retention,
real exit status, held-gate exclusion, invalid commands/options/writable or linked
entry-point rejection, and an actual standard-user process unable to mutate the
private state. Full UI tests include passing Validation without an acknowledgment
call, retained machine-only blocking, safe text rendering and unknown diagnostics
without an automatic Repair operation. Pure Rust tests cover all guidance decisions
on both platforms and distinguish unavailable activity/health from positive damage.

This verifies the newly shipped bundled entry points. Application-only upgrades
do not silently rewrite an older applied development baseline: old separately
deployed CLI copies can retain old behavior until a normally authorized
Install/Repair refreshes them. Use the current application's Validation for
diagnosis. Owner UAT must cover that deployment distinction. Existing
`backend_active` frontend fallback/tri-state observation wiring remains T7/T8;
native mutation guards continue to fail closed independently.

Local: 135 frontend tests and production build, 19 backend contracts, 20 workflow
tests, two Rust guidance tests, Linux/Windows-GNU coordinator clippy, Python
compilation, shell syntax and diff checks passed. Nine protected Python tests
were explicitly skipped at local UID 1000, not claimed as root/native acceptance.
Windows PowerShell/native, root Linux and actual Mint evidence remain pending CI.

## Durable continuation

The PR comment records the exact head and initial Build URL. A completed-run
notice authorizes validating/fixing that head and starting the next planned task,
not a status-only response. After acceptance, continue T7 automatic reports and
history, then T8 safety-observation/acknowledgment/resume UI, consolidated review
and exact-source candidate validation. No scheduler is active. If only long CI
remains, leave a checkpoint and stop; signing approval and UAT are owner gates.
No partial-stack merge, signing, publication, release, fleet rollout or milestone
closure here. Preserve Windows interruption evidence and Mint v1.2.18 35/0/0.
