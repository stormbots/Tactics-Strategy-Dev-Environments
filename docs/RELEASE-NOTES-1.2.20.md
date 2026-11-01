# SDE 1.2.20 — Self-service interrupted-operation recovery

Consolidated Safe Operations recovery redesign for focused Windows 11 and Linux
Mint owner UAT. This candidate replaces mentor clearance with explicit,
incident-bound acknowledgment while preserving safety and original evidence.

- Recovery separates machine and account findings, current activity, package
  health and trust. Users can review diagnostics and acknowledge eligible
  interruptions without an extra elevation prompt or mentor-servicing step.
- Acknowledgment automatically attempts a local summary. No separate save click
  or report dialog is required. Save failures are visible; original-evidence
  preservation failures still prevent a new change.
- Pending requests return to ordinary review and OS authorization. Startup
  acknowledgment without a request returns to Overview without starting work.
  Cancel, restart, passing Validation and Check Again never silently replay a
  request, acknowledge an incident or clear its evidence.
- Active or unknown activity, known package damage and untrusted state still
  block changes. Unknown package health alone warns after inactivity is
  established. Overview explains current warnings inside the existing status
  card; a successfully acknowledged old incident does not alone keep it blocked.
- Safe read-only Validation, support diagnostics, retained report/history views
  and user-initiated export remain accessible. Sharing is never automatic.
  Explicit report/view deletion does not delete minimum decisions or the current
  protected transaction. Ambiguous/unavailable history can remain non-deletable.
- Manual, scheduled-tool and application-updater paths share fresh native checks,
  protected gates and evidence-preserving transitions. Signatures, pause policy,
  package identity, native locks and postchecks remain required.

Use the [focused Recovery UAT sheet](RECOVERY-FOCUSED-UAT.md). The historical Mint
v1.2.18 **35/0/0** result and Windows interruption evidence remain preserved.
A legacy interruption may require a further normal Restart after its initial
provenance is captured. Acknowledgment/restart does not repair packages, certify
the earlier outcome or provide a bypass for malformed/unreadable evidence.

Only v1.2.20 is eligible for publication by the protected candidate workflow.
The same-source rebuilt v1.2.19 is an **unpublished upgrade fixture**, not the
published v1.2.19 package. Published v1.2.18/v1.2.19 assets remain immutable.
Application installation enables automatic SDE updates as before; the tool
baseline and working student environment are not provisioned by app installation.
This prerelease is not stable promotion, fleet rollout or milestone acceptance.
