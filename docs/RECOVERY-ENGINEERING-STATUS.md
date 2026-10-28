# Interrupted-operation recovery: engineering status

Scope: first bounded task, T1 contract and native feasibility gate.
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

Rust and PowerShell are not installed in this execution environment. Native
Windows, privileged Linux, PowerShell parsing/analysis, workflow lint, and full
existing application validation are pending CI. No tests were run against owner
workstations; Windows evidence and Mint's v1.2.18 35/0/0 pass remain intact.

DevOps reported the Linux root fixture passed at `8a88b27`, but requested an
explicit Windows evidence gate. The old Windows NSIS native job's Chocolatey
step succeeded in Build run `40775671361`; bundle selection did not exclude that
step. The revised workflow makes the probe separately visible and requires both
exact markers. Old-head success is not substituted for revised-head CI evidence.

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
