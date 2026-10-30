# Windows direct maintenance recovery: checkpoint

Branch: `codex/recovery-windows-manual-supervision`.
Base: accepted #120 head `dcd86bf141543ee6e8ecfbfeb7265e86d25fb7ee`,
Build `40988511475`, attempt 2. The recovery stack remains unmerged.

Accepted #121 head: `7c6d374185370893b610b5d59dc8245d3b0cbcff`, Build
`41000952438`. The installed Windows maintenance marker, version/nesting checks,
signed SYSTEM upgrade and scheduled-tool marker passed. Linux host and actual
Mint 22.3 manual markers/signed upgrade, general and both trust jobs passed.
This supersedes historical pending language below. No merge/release/UAT occurred.

## Scope and acceptance criteria

This bounded T4 increment connects the direct `Update-SkyviewTools.ps1` and
`Update-Node24.ps1` wrappers to native supervision. It does **not** claim that
Install/Repair or Chocolatey's outer configuration entry point is integrated.
Those retain their conservative legacy behavior until a separate increment
preserves and tests their provisioning/profile context. The authenticated GUI
helper and scheduled tool paths already use native supervision.

- Reuse `sde_coordination::manual`'s existing mutation, evidence-preserving
  transition, completion policy, sanitized errors and exit codes on both OSes.
  Shared coordinator receipt/journal/retirement/gate logic is unchanged.
- Windows command construction lives in `updater::manual_windows` to reuse the
  existing installed-file/ancestor ACL validator, including its established
  TrustedInstaller handling on Program Files directories. No permission rule
  for coordination state or private receipts is relaxed.
- Require a currently elevated administrator/SYSTEM token before private-state
  access, diagnostic collection, temporary files or command execution. Admin
  group membership on a filtered token is insufficient; no elevation is added.
- Only maintenance script names are accepted. Tool update takes no extra args;
  Node update optionally takes `-Version` and a numeric 24.x.y value. No scriptblock,
  interpreter, arbitrary command or bypass flag comes from IPC. No frontend
  handler/capability is added. Absolute protected ProgramData/Program Files paths,
  each ancestor's ACL, regular-file type, no reparse point and a single link are
  required. UNC/device/alternate-stream/traversal spellings are rejected.
- Launch fixed in-box Windows PowerShell 5.1, no profile/interactive startup,
  fixed system environment/search paths and private per-invocation temp storage.
  Only system maintenance is supported here: no desktop-profile phase is moved
  into SYSTEM. Temporary evidence is retained; no error/Drop cleanup can delete
  files still needed by an uncertain package operation. Storage uses one child
  namespace under the coordination root, not an unbounded number of root entries.
- Existing global leases and private-token/held-gate nesting checks run **before**
  outer delegation. GUI/scheduled children do not recursively acquire the gate.
  The outer wrapper reruns its original protected script once, with literal
  parameter arguments, and propagates the real native exit code. It does not
  invoke its Action again or clear the native guard's journal.
  A shared session lease covers capability negotiation and launch, preventing
  coordinated application replacement between them; a busy installation defers.
- Compatibility negotiation uses existing non-GUI `--coordination-init`; require
  its explicit Windows maintenance capability before sending the new mode.
  Old apps return no capability and fail closed without opening a root GUI.
  Initialization prepares only; it cannot acknowledge or retire evidence.
- The GUI-subsystem app is launched with explicit redirected stdout/stderr.
  Both streams are drained concurrently line by line and forwarded to existing
  logs; no package-log accumulation, process timeout, package termination or retry
  loop. An absent console during NSIS initialization cannot make capability output
  an installation failure. The native CLI reuses normal 75/76 deferral/error codes.

Current templates gain this behavior when installed/applied. Existing legacy
deployed script generations are not silently rewritten by app installation.
They remain conservative until an explicit baseline Repair; the current GUI and
scheduled native supervisors remain the supported recovery-aware paths meanwhile.
No final acknowledgment/report/history interaction is enabled by this increment.

## Verification

The existing Windows NSIS workflow requires
`SDE_RECOVERY_WINDOWS_MANUAL_MAINTENANCE_OK` after installed bootstrap and before
real provisioning/signed upgrade. It invokes the installed release app through
private, root-owned synthetic no-package scripts, not a checkout executable.

The fixture establishes native package inactivity with the same read-only source
compiled into the coordinator; unavailable/incomplete observations and a bounded
busy setup fail closed. It tests actual standard-user rejection, unsupported
arguments, effective student script-write rejection, real token/gate nesting,
sanitized environment, Node version-data preservation, forged-token rejection,
known completion and consent-required deferral with unchanged legacy evidence.
Synthetic previous-boot provenance cannot substitute for intent. Explicit intent
then permits continuation and requires original bytes in both archive copies plus
a private receipt. This is not an actual reboot or owner UAT. Only successfully
verified synthetic history is cleaned under the gate; no active journal is cleared.

Pure Windows argument tests run in the updater suite. Source/workflow regressions
require nesting-before-delegation, explicit capability negotiation, streaming both
pipes, no package Kill/Action replay and the mandatory installed marker. Keep all
inherited root/coordination, feasibility, installed bootstrap, signed SYSTEM,
scheduled-tool, Linux host/Mint manual and actual Mint 22.3 signed-upgrade gates.
No skipped native requirement or old-head result constitutes acceptance.

Local results: ten Linux manual test entries succeeded, with root-required
fixtures returning early at UID 1000 (not native proof). Coordinator Linux and
Windows GNU all-target Clippy and updater Linux all-target Clippy passed with
warnings denied. Fourteen backend contracts, nineteen workflow/scope tests and
three frontend permission-wiring tests passed. Coordinator/updater formatting
and diff checks passed. Windows adapter typechecking/execution, PowerShell
parsing/analysis, the installed marker and full Tauri/native builds remain
authoritative CI work; no local Windows/installed pass is claimed.

## Durable resume instructions

The owner consolidated engineering and DevOps under Codex. Do not send the owner
back to a separate CI chat or ask for routine test/rerun permission. The hourly
automation was canceled because it could not retain Codex Cloud access; do not
recreate or resume it. Work in active Cloud sessions.

1. Read current AGENTS.md, this handoff, and the PR's latest checkpoint comment.
2. Verify the live branch/PR head and exact-head workflow results once. The PR
   comment records the pushed SHA and initial Build URL without changing that SHA.
3. If CI is pending with no independent unblocked work, end promptly; do not poll
   or hold the session. If failed, inspect failure-specific evidence, distinguish
   infrastructure from application defects, fix within scope and run existing CI.
4. Require this installed Windows marker plus every inherited native gate before
   recording acceptance. Do not partially merge the recovery stack.
5. After acceptance, implement Windows Install/Repair/Chocolatey outer supervision,
   then remaining updater, diagnostics, reports/history, Recovery interaction and
   consolidation. Do not declare T4, the full redesign or owner UAT complete here.

Preserve owner Windows interruption evidence and Mint v1.2.18 35/0/0 acceptance.
Stop for actual human signing approval, owner UAT, or a genuine authority/blocker
issue. No release preparation, signing, publication, stable/fleet promotion or
milestone closure is part of this checkpoint.
