# Recovery-aware application installation

Branch: `codex/recovery-application-updater`.
Base: accepted #123 head `fd7762f41a85088655dd277e7c71f1319b7cd038`,
[Build 41015393940](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41015393940),
full success. The stack remains unmerged; no signing or UAT candidate is ready.

## T4 execution-parity review

The supported backend system-mutation entry points are connected. This is a
source/accepted-CI review, not a claim of finished UI, actual reboot or owner UAT.

| Entry point | Native outer owner | Nested boundary |
| --- | --- | --- |
| GUI Install/Repair/Update helper | Rust system mutation guard (#118) | Fixed privileged command; private Windows token or actual Linux descriptors |
| Linux manual Install/Update; Repair reuses Install | Installed Linux manual adapter (#120) | Root system phase; separate desktop-user configuration; real descriptor validation |
| Windows direct maintenance | Installed Windows manual adapter (#121) | Fixed interpreter, protected paths, literal Node version, normal effective-admin token |
| Windows direct Install/Repair | Installed Windows adapter (#123) | Explicit existing switches; native account profile or SystemOnly policy; genuine parent reuse |
| Scheduled tools on both platforms | Rust scheduled-tool guard (#119) | Private applied-baseline snapshot and existing physical nesting proof |
| Chocolatey configuration hook | Must reuse outer owner (#122) | Elevated private token plus physically held operation gate; no independent hook transaction |

The embedded applied supervisors retain conservative legacy fallback code for
internal/backward-compatible callers; the shipped worker always supplies its
native parent (Linux `--leased` plus real descriptors, Windows private token plus
held gate). These are not additional supported direct orchestration entry points.
No generic OS/package-manager interception is claimed. User-only configuration,
read-only validation and frontend admission remain separate T6/T8 responsibilities.
Real standalone Install/Repair completion and actual restart remain UAT criteria;
#123's no-package outer fixture and real nested provisioning are distinct proofs.

The remaining application installer still used legacy `operation/installation`
gates before staging and execution, preventing acknowledged recovery. This task
connects that boundary rather than changing the already accepted script paths.

## Bounded T5 backend task and acceptance criteria

1. Introduce a Rust-only preparation lease. It holds operation/session locks for
   eligibility and signature checks without publishing incidents, committing
   acknowledgment, archiving old evidence or creating a transaction. It validates
   an existing private journal's storage. Dropping it leaves evidence unchanged.
   System preparation shares sessions; installation preparation excludes all GUI
   sessions and rechecks maintenance compatibility under its held locks.
2. Transfer both handles directly into the existing acknowledgment-aware begin
   path, without a release/reacquire gap. Only begin can evaluate fresh native
   activity, reconcile actual generation-bound intent, archive original evidence
   and create a distinct installation transaction. A preparation snapshot is not
   mutation permission or an IPC capability.
3. Authenticate the staged manifest/signature/payload, native package identity,
   installed version and no-downgrade eligibility before consuming an incident.
   Keep initial and immediately-pre-launch pause checks. A late pause is a known
   no-child abort, not successful package completion.
4. Supervise actual APT/NSIS through the guard with existing literal arguments,
   fixed environment and nesting proof. Retain native package locks, indefinite
   installer waiting, NSIS zero-only success, explicit 3010/reboot reporting,
   installed version/resource/engine postchecks and protected receipts. Nonzero,
   spawn/wait failure, failed postcheck or uncertain final activity keeps intent.
5. Use shared bounded native inspection for Linux package health. Positive damage
   and unknown activity block. An unavailable audit is unknown health, which may
   warn/allow only when inactivity is independently established. Final completion
   requires a fresh safe native observation after all platform postchecks.
6. Coordinate staging without consuming recovery. With a retained journal, never
   prune older staged inputs or replace the earlier recovery receipt: an uncertain
   installer may still need them. Only read-only existing recovery verification
   and a new, separately authenticated staging generation are allowed. Acquisition
   failures still stop the work. No automatic interrupted-package retry is added.
7. Preserve typed report outcomes: activity/unknown activity/awaiting consent are
   deferred; known incomplete state fails; trust/unavailable findings are not
   mislabeled as healthy/current. This does not complete later Recovery UI work.

ADR 0002's lease-bound permit, original bytes and generation remain authoritative.
Old generic APIs remain conservative; no environment bypass, lock deletion,
permission loosening, service, process termination or validation-based clearing
is introduced.

## Required evidence

Four new root/native coordinator tests cover preparation with unchanged original
bytes/object identity/context, exact exclusive session and operation leases,
unbroken transfer into acknowledgment-aware installation, active/unknown/incomplete
rejection despite consent, and clean system preparation with shared sessions.

Both existing signed native upgrade fixtures now create a disposable interrupted
installation, using the actual production storage and platform installer path.
They require authentication rejection to leave it unchanged, deny consent in the
same boot, deny simulated restart without intent, reject authentication even with
valid final intent, then complete the real signed APT/NSIS upgrade after valid
intent plus simulated earlier provenance. Original journal and retired-object
bytes and receipt must remain archived; a fresh successful journal must clear.
Simulated provenance is test-only, not an actual reboot or production override.
The required `SDE_RECOVERY_APPLICATION_INSTALL_CONTRACT_OK` marker is enforced in
both signed-upgrade wrappers, including actual Mint 22.3. No marker means failure.

The subsequent scheduled-tool native proof checks absence of its own incident's
archive before consent, rather than requiring an entirely empty history directory:
the application recovery proof now legitimately leaves earlier retained history.
Its original-byte/receipt assertions, inactivity setup and actual next invocation
remain required. No existing signed upgrade, failure/postcheck, bootstrap,
feasibility, package-hook, manual supervisor, session or trust check is waived.

Local verification: 18 backend contracts, 20 workflow/scope tests and 29 applicable
Linux updater tests passed (one actual Mint native test filtered). Linux updater
and Linux/Windows-GNU coordinator clippy passed; formatting/diff checks passed.
Coordinator local harness reported 69 passing entries, but root-only storage tests
(including the four new tests) return early at local UID 1000. That is compilation
and pure-test evidence only, NOT native/root acceptance. Required root Linux,
Windows and real signed upgrades remain pending CI.

## Durable continuation

The PR comment records the exact pushed head and initial Build URL. Inspect live
head and completed results once; diagnose actual failing commands, fix in scope,
and rerun through existing workflows. Stop with a checkpoint when only long CI
remains. A user notice that a run completed authorizes checking it, resolving
failures and beginning the next planned increment, not just reporting status.
No scheduled automation is active. Signing approval and UAT remain owner gates.

After native acceptance, continue T6 read-only diagnosis/self-service guidance,
then automatic reports/history, Recovery UI/resume, consolidated review and
exact-source candidate validation. No partial-stack merge, release, publication,
stable promotion or milestone closure here. Preserve Windows interruption evidence
and Mint v1.2.18 Install/Validate acceptance (35 passed, 0 warnings, 0 failed).
