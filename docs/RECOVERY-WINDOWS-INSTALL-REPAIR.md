# Windows direct Install/Repair supervision

Branch: `codex/recovery-windows-install-supervision`.
Base: accepted #122 head `26a769b773fa0500427c5a675348579a484bc508`,
[Build 41010290087](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41010290087),
full success. The recovery stack remains unmerged.

## Bounded T4 task and acceptance criteria

- The already-elevated installed Windows Install script delegates before package
  work to the same native mutation, acknowledgment, evidence retirement and
  completion policy used by direct maintenance. Repair uses the same entry point.
  No independent journal writer is selected for an un-nested Install/Repair.
- Only the existing `-SystemOnly` and `-Repair` switches are accepted as literal
  arguments, at most once each. Arbitrary commands, profile targets and policy
  overrides are rejected. Existing authenticated GUI/scheduled parents are reused
  before outer delegation. Chocolatey's hook still requires its genuine parent.
- SystemOnly retains the fixed SYSTEM profile environment. Bare manual setup
  retains the current administrator's Windows profile, roaming and local known
  folders, including redirection, rather than trusting inherited profile variables
  or accidentally configuring systemprofile. Native token/known-folder lookup
  failure blocks before mutation; SYSTEM must explicitly use SystemOnly.
- Existing effective-admin, protected entry-point ACL/reparse/link checks, fixed
  interpreter, cleared environment, private temporary storage and held gates are
  unchanged. Direct checkout/download execution is not a trusted installed entry
  point. Use the installed application or protected installed backend.
- Active/unknown package activity and incomplete package health still block.
  A zero child exit without fresh safe completion still retains the transaction;
  no package process is killed or dismissed through an environment flag.

## Verification boundaries

The mandatory installed Windows manual fixture now also runs protected synthetic
Install/Repair backends through the actual packaged supervisor. It proves all four
switch combinations, rejection of contaminated profile variables, native account
profile preservation, SystemOnly policy, real held-gate/token nesting, no child
before acknowledgment (even after simulated restart), and continuation with
byte-preserved archive evidence after explicit generation-specific intent.
Both `SDE_RECOVERY_WINDOWS_MANUAL_MAINTENANCE_OK` and
`SDE_RECOVERY_WINDOWS_MANUAL_INSTALL_REPAIR_OK` are required; native failure or
missing markers fail the existing NSIS path. This is no-package supervision
proof, not real package completion or actual reboot evidence.

The existing Node 26-to-24/full system provisioning regression keeps all real
package, task, workspace, maintenance and final idle checks. It now explicitly
establishes its original legacy protected parent around the checkout script.
This deliberately tests nested reuse, not the new installed outer: the earlier
real MSI work can legitimately remain active, and a checkout path is not trusted
installed code. Its existing narrowly scoped feed-failure retry is unchanged.
It must not be cited as proof that native outer completion succeeds after real
package activity. Real Install/Repair completion remains an owner UAT criterion;
uncertain native completion must not be forced to success to satisfy that test.

Keep Windows feasibility, package-hook parent boundary, installed bootstrap,
signed SYSTEM upgrade, scheduled-tool contract, both trust jobs, Linux host
manual supervision and actual Mint 22.3 manual/signed-upgrade gates mandatory.
No test waiver, production fixture flag or new native inactivity exception is
introduced.

Local checks: 16 backend contracts and 20 workflow/scope tests passed; Linux
updater clippy passed. Linux updater unit harness: 28 tests passed in aggregate,
one native test filtered. The loopback HTTP test initially hit sandbox EPERM and
passed when rerun with network permission. These are not Windows/native proof.
Windows Rust compilation, PowerShell execution, installed supervisor and all
cross-platform gates remain pending CI.

## Durable resume checkpoint

The PR comment records the exact pushed SHA and initial Build URL. On resume,
read AGENTS.md, this document and the live head/run once. Diagnose failing
commands and handle routine fixes or evidenced transient infrastructure failures.
If only long CI remains, end with a checkpoint; no scheduled work is active.

After acceptance, review remaining T4 parity before T5 application-updater
integration. Diagnosis/guidance, automatic reports/history, Recovery UI and
consolidated exact-source CI/signing/owner UAT remain. No partial-stack merge,
signing, release, publication or owner UAT is authorized by this checkpoint.
Windows interruption evidence and Mint v1.2.18 35/0/0 acceptance remain intact.
