# Windows package-hook parent boundary

Branch: `codex/recovery-windows-package-hook`.
Base: accepted #121 head `7c6d374185370893b610b5d59dc8245d3b0cbcff`,
[Build 41000952438](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41000952438).
The recovery stack remains unmerged. Codex owns engineering and DevOps; no owner
relay to another CI chat, scheduler restart or routine approval is required.

## Bounded T4 task and acceptance criteria

Chocolatey's configuration hook executes after the package manager has already
started work. It must not create an independent SDE transaction or treat active
package-manager processes as evidence that a new mutation is safe. This increment
requires the hook to reuse a genuine existing SDE parent.

- The actual `chocolateyInstall.ps1` entry point always requests `-RequireParent`.
  The coordination function rejects combining that request with non-mutation use.
- For this mode, even a same-process global lease reference must pass the existing
  elevated-token, protected journal/token match and physically held operation-gate
  checks. A FileStream with the right name is not permission. Same-process and
  cross-process valid parents continue to work.
- No valid parent means `SDE_SUPERVISOR_REQUIRED` with a supported Install/Repair
  instruction, before Action execution, native outer delegation or legacy journal
  creation/clearing. A retained journal remains unchanged. No environment boolean
  grants authority, and no automatic acknowledgment, lease reset or retry is added.
- Existing shared native mutation/retirement/completion policy and the legacy
  standalone Install/Repair wrapper are unchanged. Those outer Install/Repair
  paths remain the next profile/provisioning-sensitive integration task; do not
  claim complete Windows T4 parity here.

Direct invocation of the metapackage through an arbitrary external `choco`
command is not a supported SDE orchestration entry point. The hook cannot
retroactively prevent dependency changes that Chocolatey made before calling it.
Use the installed SDE application/approved Install or Repair entry point so the
supervisor exists before package work. No universal OS/package-manager interception
is claimed. Existing GUI and scheduled recovery-aware paths are unchanged.

## Required verification

The existing native Windows coordination fixture now proves:

- no-parent and forged-global-lease rejection without creating a journal;
- actual hook invocation rejects before configuration progress is emitted;
- real same-process and child-process parent reuse;
- parent-required rejection retains byte-identical interrupted evidence;
- every pre-existing contention, crash, private permissions and read-only
  Validation assertion remains required.

The existing Rust Windows nesting fixture also requests `-RequireParent`, proving
the shared Rust guard's private token and held gate are accepted. No test bypasses
or weakens native activity, receipt, generation or completion decisions.

The Windows NSIS workflow must retain the native exit code before emitting logs
and require BOTH `WINDOWS_COORDINATION_SUPERVISION_OK` and the new
`SDE_WINDOWS_PACKAGE_HOOK_PARENT_REQUIRED_OK`. No missing marker or masked native
error can be accepted. Keep real Node/baseline provisioning, Windows installed
manual-maintenance proof, signed SYSTEM upgrade, root/trust/feasibility/bootstrap,
Linux host/manual and actual Mint 22.3 signed-upgrade checks mandatory.

Local verification: fifteen backend contracts, twenty workflow/scope tests and
diff checks passed. PowerShell and real Windows package-hook/nesting execution
remain pending native CI. No unchanged passing Rust suite was rerun merely for
this PowerShell-only production change.

## Durable resume checkpoint

The PR's latest comment records the exact pushed SHA and initial Build URL. On
resume, read AGENTS.md and this handoff, verify the live head and that run once,
then diagnose any failure-specific evidence. Handle ordinary fixes and justified
infrastructure reruns without owner supervision. If only long CI remains, end
with the checkpoint rather than polling. The owner canceled scheduled work;
do not recreate it.

After acceptance, continue Windows Install/Repair outer integration, then the
remaining updater, diagnosis/guidance, report/history and Recovery UI work.
No partial-stack merge, release preparation, signing, publication or owner UAT
is part of this checkpoint. Preserve Windows interruption evidence and Mint
v1.2.18 Install/Validate acceptance (35 passed, 0 warnings, 0 failed).
