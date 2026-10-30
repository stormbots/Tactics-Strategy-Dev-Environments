# Interrupted-operation recovery: engineering status

Current increment: [application-updater recovery integration and T4 parity review](RECOVERY-APPLICATION-UPDATER.md),
branch `codex/recovery-application-updater`, pending native validation.
A completed-run notice authorizes Codex to validate/fix that checkpoint and start
the next planned engineering increment. Do not stop at a status-only handoff when
actionable planned work remains. Pause only for long pending CI, an actual owner
decision/signing approval, or owner UAT.
Windows direct Install/Repair (#123) passed at
`fd7762f41a85088655dd277e7c71f1319b7cd038` in
[Build 41015393940](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41015393940).
Both Windows installed manual markers, real nested provisioning, signed SYSTEM
upgrade and scheduled-tool contract passed, along with Linux host/actual Mint 22.3
manual/signed-upgrade evidence, both trust jobs and general checks. This is not
actual reboot or standalone real-package owner UAT evidence.
Windows package-hook parent boundary (#122) passed at
`26a769b773fa0500427c5a675348579a484bc508` in
[Build 41010290087](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41010290087).
The Windows package-hook, manual, installed bootstrap, signed SYSTEM and scheduled
markers passed, as did both trust jobs, general checks and Linux host/actual Mint
22.3 manual/signed-upgrade checks. No partial stack merge or release occurred.
Windows direct maintenance (#121) passed at `7c6d374185370893b610b5d59dc8245d3b0cbcff`
in [Build 41000952438](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41000952438).
The installed manual-maintenance, signed SYSTEM, scheduled-tool and inherited
Windows/Linux trust checks passed, as did host/manual and actual Mint 22.3
manual/signed-upgrade evidence. This is not full Windows Install/Repair parity.
Codex now owns both engineering and DevOps. The owner canceled the hourly
automation; active Cloud sessions must leave a durable checkpoint when only CI
remains pending. No separate CI-chat handoff is required.
Linux manual supervision (#120) passed at `dcd86bf141543ee6e8ecfbfeb7265e86d25fb7ee`
in [Build 40988511475](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/40988511475),
attempt 2. Host and actual Mint 22.3 manual markers/signed upgrade passed in
attempt 1; Windows Rust tests, signed SYSTEM and scheduled-tool markers passed on
the authorized infrastructure retry. All applicable checks passed. This accepts
that bounded increment, not complete T4 parity, a merged stack or owner UAT.
Scheduled tool supervision passed at `c3328f2c79d3093e92e1c8c8fbf3b56e77f093f1`
in [Build 40925960095](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/40925960095).
Windows signed SYSTEM upgrade and both scheduled-tool contract markers passed;
Windows observed activity then confirmed inactivity before its synthetic journal.
Actual Mint 22.3 installed bootstrap, signed upgrade and next-engine checks passed,
as did general checks and both trust jobs. This accepts #119's bounded checkpoint,
not the final Recovery UI or execution parity. No merge/release/UAT occurred.
Privileged GUI helper supervision passed at `fe0bee97a6d288e084feb7961ca95f04ea8da548`
in [Build 40881178483](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/40881178483).
Root Linux coordinator passed 54/54; Windows passed 51/51. Native Tauri spawn,
completion and streaming/redaction tests passed on both platforms, along with
all inherited installed bootstrap, native, trust and signed-upgrade checks.
Bootstrap integration passed at `46667078290536380583d6e6f0671f7c07845742` in
[Build 40831671161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/40831671161).
Required root Linux coordinator passed 52/52; Windows native coordinator passed
49/49. Both installed bootstrap markers (including actual Mint), feasibility,
native builds, signed upgrades and general/trust checks passed. No merge or owner
UAT occurred. The current helper task is only part of T4, not execution parity.
Safe transition passed at `c0a3ecd282409af436cac12a32ed8a771707ff06` in
[Build 40821734101](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/40821734101).
Windows trust passed 44/44; required Linux root coordinator passed 47/47.
Native restart-source availability, mutation/child coordination, production
storage and durable replay passed, as did native builds, feasibility markers and
signed-upgrade checks. These results do not prove an actual reboot/resumption or
the still-unimplemented full UI/execution integration.
Durable acknowledgment passed at `046d56bd4f5f723e1d21eadbbc95674c558016ac`
in [Build 40800652705](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/40800652705).
Windows trust reported 30/30; required Linux root tests, both native builds,
feasibility markers and signed-upgrade checks passed. This accepts that increment,
not the full recovery redesign. Normal installation preparation is connected;
the privileged GUI helper and scheduled tool work are supervised. The current
task connects Linux manual system scripts, not SDE installation. Windows outer
script, application-updater and final
report/history/Recovery UI work remains. T4 execution parity is still incomplete.
The [production backend foundation](RECOVERY-BACKEND-FOUNDATION.md) passed at
`59884166cd336153160238f7367dcec0b136744a` in Build run `40792896158`, attempt 2.
The record below is the historical
permission-feasibility increment, now accepted on exact-head native CI; it is not
the status of the full redesign.

Historical scope: first bounded task, T1 contract and native feasibility gate.
Branch: `codex/recovery-acknowledgment-contract`.
Base application source: `3b0e8d7ec05d1b6d62535cb5b1368056abe3ac04`.

## Implemented in this task

- Proposed the privilege/storage contract in
  [ADR 0001](adr/0001-interruption-acknowledgment-boundary.md).
- Added executable strict acknowledgment payload/binding contract tests.
- Added an isolated Linux root fixture with a real dropped-privilege child.
- Added an isolated Windows permission fixture with a real standard-user account
  and independent privileged reader, following existing native test conventions.
- Connected these probes to the existing Build Skyview Dev Setup workflow.

Production coordinator, installer bootstrap, journal behavior, Recovery UI, and
updater execution have not changed. The new writable acknowledgment slot is
created only in disposable probe fixtures, not in the real coordination root.

## Acceptance and evidence

The probe must establish that a non-elevated student can read a sanitized marker
and submit its incident ID into a fixed slot, while private journal/binding bytes,
the marker, root, slot identity, and permissions remain protected. A separate
privileged consumer must see the same persisted decision. A stale ID or changed
journal must not match the private binding.

Local verification completed:

- 9 payload/binding tests passed. The additional Linux root/CI permission fixture
  was explicitly skipped, not reported as a native pass.
- 12 CI-scope/workflow tests passed, including three regressions requiring the
  dedicated Windows NSIS step, nonzero-exit/missing-marker failures, and separation
  from Chocolatey packaging while retaining coordination checks.
- Python compilation and whitespace/diff checks passed.

At that increment Rust and PowerShell were not installed locally. Native
Windows, privileged Linux, PowerShell parsing/analysis, workflow lint, and full
existing application validation are pending CI. No tests were run against owner
workstations; Windows evidence and Mint's v1.2.18 35/0/0 pass remain intact.

DevOps reported the Linux root fixture passed at `8a88b27`, but requested an
explicit Windows evidence gate. The old Windows NSIS native job's Chocolatey
step succeeded in Build run `40775671361`; bundle selection did not exclude that
step. The revised workflow makes the probe separately visible and requires both
exact markers. Old-head success is not substituted for revised-head CI evidence.

DevOps subsequently accepted exact head `1f1e44918be9645069312a388601fdc7e1c2bc13`
in successful Build run
[40779104989](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/40779104989).
Windows NSIS job `123136019245` passed the dedicated step with both markers;
Linux root feasibility and all other applicable checks passed. No merge, release,
or owner UAT occurred. This historical native gate is complete.

## Required DevOps validation

Use the PR's exact latest source SHA, not this document's base SHA. Inspect the
existing Build Skyview Dev Setup run; do not create duplicate dispatches or
waive jobs. Relevant new assertions:

- `update-trust`: Recovery acknowledgment contract, plus Root-owned recovery
  acknowledgment feasibility on Linux. The required root invocation must fail
  if its privileged fixture cannot run; do not accept its local skip as evidence.
- Windows NSIS native job: the dedicated **Required Windows acknowledgment
  feasibility** step calls `Test-RecoveryAcknowledgmentFeasibilityCI.ps1` outside
  Chocolatey packaging. It requires exit code zero and both exact success markers;
  a missing marker fails even if the script exits successfully.
- Expected markers include `SDE_RECOVERY_WINDOWS_STANDARD_USER_INTENT_OK` and
  `SDE_RECOVERY_WINDOWS_PRIVILEGED_CONSUMER_OK`. Linux unittest must execute
  `test_student_submits_intent_without_access_to_private_evidence` without a skip.

Return results with head SHA, run/job URLs, and exact failure assertions. Native
Build jobs also retain existing protected coordination and signed-upgrade checks;
no new permission probe supersedes them. A download/runner failure is not a
permission-contract failure; diagnose it separately without waiving validation.

Do not merge, version, package a release candidate, publish, approve signing, or
request owner UAT for this partial implementation. Do not resume automation.
End while CI is pending rather than polling long-running jobs.

## Next engineering task after native evidence

If native probes pass, return to engineering to implement the production T1
contract, prove actual legacy deployment/bootstrap and crash behavior, and then
T2–T8. The layout probe alone does not prove those lifecycle requirements.
Translate test contracts into shared production validation; do not import a
test helper as a privileged production consumer. The ADR remains proposed until
the complete T1 deployment contract has authoritative evidence.

If a native probe fails, return its exact failing command and assertion to
engineering. No broad bypass, private-journal deletion, or extra acknowledgment
elevation prompt is an acceptable workaround. The plan's product decisions remain
unchanged.
