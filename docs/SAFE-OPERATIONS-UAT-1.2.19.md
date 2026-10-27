# v1.2.19 replacement UAT

Install only after Codex confirms the signed candidate is published, authenticates
its five release assets, and supplies the installation commands and hashes.
Confirm About shows **1.2.19**. Do not use development-version CI packages.

## Windows 11: resume the blocked path

1. Open SDE. If the existing machine interruption remains, Recovery must appear
   even without an app operation log. It should explain that mentor review is
   needed before Install, Update or Repair.
2. Run validation from Recovery or Validation. It must produce actual workstation
   check results and a completion summary rather than the previous guard exception.
   An interruption warning may remain, and real missing tools may fail checks.
   Report those results; do not use Repair or remove the protected record to obtain
   a pass. Successful validation alone must not clear the system interruption.
3. Confirm logs and Create support report are available. Preview and save the
   report, with logs initially off. Follow the original report checks in the
   [consolidated guide](SAFE-OPERATIONS-UAT.md).
4. If startup validation naturally fails, its action must say Retry validation,
   never Retry install. No need to manufacture another failure to test this.

An unresolved machine interruption can intentionally keep mutating operations
blocked. This candidate restores diagnosis and support access; it does not repair
or certify the unknown earlier system operation. Codex reviews the resulting
support evidence before proposing any workstation recovery action.

## Mint and any Windows workstation cleared for normal operations

Open Install preflight and stop before confirming installation. Expect buttons in
this order: **Continue with Install**, **Check Again**, **Cancel**. Continue should
be the obvious filled primary button. Check Again refreshes the observations;
Cancel returns without provisioning or elevation. Update preflight uses the same
hierarchy with Continue with Update. On an interrupted Windows workstation, do
not attempt to bypass Recovery to reach preflight; Mint supplies this UI check.

Preserve the successful Mint v1.2.18 installation/validation result. Complete any
remaining safe, previously unreported checks from the consolidated guide once.
Do not manufacture crashes, package locks or disk exhaustion.

## Return results

Reply with **Windows: Pass / Finding / Blocked** and **Mint: Pass / Finding**.
Attach a support report for findings and identify the step. Codex maintains the
evidence record and handles diagnosis. Full acceptance, milestone closure and
stable promotion remain pending the applicable owner decisions.
