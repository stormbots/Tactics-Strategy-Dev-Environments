# Maintenance inspection and in-place retry

Part of [#161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161), following the [restoration scope audit](MAINTENANCE-RESTORATION-SCOPE.md).

This increment adds confirmed inspection causes and a read-only continuation on Schedule. It does not complete the separate leave-disabled decision or full restoration workflow.

## Student flow

If SDE cannot read weekly maintenance, the page explains what is known. A confirmed permission problem asks the student to keep using their normal account and get help from a teacher or administrator. A timeout says the check took too long. Other collection failures stay uncertain; they do not become proof of a missing or disabled schedule. Technical diagnostics remain available separately.

**Check maintenance status again** reads the schedule in place. It does not start maintenance, install tools, change task permissions or save the SDE app-update preference. The existing page-wide **Refresh** remains available. The new continuation does not reread or remount the separate SDE-update policy panel.

The result shows the actual state. A new Disabled result replaces the access/collection finding with a disabled-schedule explanation. Enabled-but-inactive remains distinct from Disabled. A failed history read can coexist with a verified Enabled or Disabled schedule. Working tools are not marked broken by these findings.

While the continuation is checking, the current review stays visible and the buttons are disabled. Repeated clicks admit one read. If a new read fails, a clearly labeled earlier observation remains available with its observation time and earlier result. It is not presented as a current successful check. A complete new schedule observation replaces the earlier display. A late response after leaving the page cannot update the departed flow or redirect navigation.

**Create maintenance support report** opens the existing review-before-sharing flow. Fresh observations update the parent display/report snapshot; an older pending parent read cannot replace them. These snapshots do not control native execution or clear recovery evidence.

## Native observation contract

The existing fixed-target readers add two bounded optional fields:

| Field | Values |
| --- | --- |
| `inspectionScope` | `schedule`, `history` |
| `inspectionReason` | `verified`, `notInstalled`, `accessDenied`, `timedOut`, `readFailed`, `unknown` |

Current readers emit both fields. The native adapter accepts legacy records with both fields absent, without inventing a specific failure cause. One missing field, an unknown enum, an array in place of a string or a contradictory combination is rejected. The frontend never infers a permission cause from arbitrary diagnostic text.

A verified schedule pairs with Enabled/Disabled. A confirmed missing schedule pairs with Missing. A failed schedule read pairs with Unavailable. History inspection can fail while the separately read schedule remains Enabled/Disabled. History records and receipt trust checks keep their existing behavior.

Windows maps the actual COM missing/access HRESULTs and otherwise reports a failed read. Mint distinguishes operating-system permission errors, named D-Bus access denial, timeouts and other failures. A nonzero systemctl result is not enough to claim a missing unit. Unsupported timer states remain unknown instead of becoming verified Disabled. The command targets, read permissions and existing ten-second systemctl limit are unchanged.

The Linux helper checksum is refreshed. No scheduling writer, native command, capability, privilege grant, dependency, version or workflow is added.

## Verification and limits

- Existing unit/browser inventories and original assertion fingerprints remain intact. Seven added continuation cases bring the unit inventory to 345; two added browser scenarios bring the default browser inventory to 132 (124 Chromium, eight WebKit).
- Unit cases cover denied-to-disabled continuation, duplicate clicks, retained earlier results, repeated failure, history scope, abandoned StrictMode reads and navigation. They also verify that unavailable/inactive observations are not mislabeled Disabled in the existing Overview health summary.
- Browser cases at 390 and 1140 pixels cover keyboard entry, focus, full accessibility checks, failed collection, Disabled, history failure, Enabled-but-inactive and successful completion. Existing Schedule/About, SDE-policy and Overview/combined-safety checks remain part of regression evidence.
- Linux contract cases cover error causes, missing and unsupported states and history failure without losing verified timer state. Rust tests reject contradictory/malformed metadata and preserve legacy compatibility. Windows fixture contracts verify cause values; disposable standard-user task probes exercise actual OS access and still deny task execution/permission changes. Only the task name is parameterized in the disposable reader copy; the production reader remains fixed-target.

Browser and mocked reader cases are simulations. Local Rust reader execution is not actual Mint desktop or Windows 11 owner UAT. Privileged/systemd and standard-user Windows fixtures remain required in CI. Full Windows/Mint native, both trust jobs, integrity, acceptance, protected merge and full exact-main gates apply.

The restoration audit's preservation and ownership gaps remain open. This UI offers rechecking and supported troubleshooting, without promising an unsupported restoration action. Human signing approval, exact authenticated-candidate owner UAT and separately authorized stable promotion remain required.
