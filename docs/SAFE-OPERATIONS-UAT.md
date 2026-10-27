# Safe Operations, Recovery and Support — consolidated UAT

This is the single owner UAT cycle for milestone 3. Run it once on Windows 11
and once on Linux Mint after Codex supplies the authenticated candidate and
checksums. Codex owns diagnosis, fixes, regression testing and evidence updates.

Do not manufacture an interruption, damage a workstation, fill a disk, hold a
package-manager lock, or run Repair only to exercise an error path. Durable
recovery and known-blocker enforcement are covered by automated tests. If a real
interrupted-operation notice appears, include it in the report and stop before
making another change.

## Record

| Field | Windows 11 | Linux Mint |
| --- | --- | --- |
| Candidate version and source commit | Supplied by Codex | Supplied by Codex |
| Installer authentication and SHA-256 | Supplied by Codex | Supplied by Codex |
| Result: Pass / Finding | Pending | Pending |
| Finding notes or saved support report | — | — |

## One compact pass per platform

1. Install and open the supplied candidate. On Overview, confirm **Ready!** is
   prominent in the existing status card. There must not be a second status
   card. A maintenance-only concern is yellow; red is reserved for a readiness
   failure. The card gives the reason and at most one maintenance action.
2. Select **Install**, start it, and review the preflight without continuing.
   Passed checks are collapsed; anything needing attention is expanded. Use
   **Check again**, then **Cancel**. Cancel must not start installation or request
   administrator approval.
3. Select **Update** and open its preflight. Temporarily disconnect the network,
   then use **Check again**. Connectivity should be **Unavailable**, never shown
   as passed. Continuing must require the explicit one-attempt acknowledgement.
   Do not acknowledge or continue: cancel, reconnect, and check again. A known
   blocker, if naturally present, must have no bypass.
4. From the contextual support action, open **Create support report**. Confirm the
   exact device name is shown, logs are off by default, and the preview is
   readable. Turn logs on and inspect the preview for usernames, home paths,
   credentials or tokens; none may appear. Save the `.html` report to a chosen
   location, open it offline, and confirm it is self-contained and matches the
   preview. Keyboard focus must stay within the dialog until it is closed.
5. Refresh Overview manually. Confirm status changes only after launch, an
   operation, or this explicit refresh—there is no distracting polling. If the
   workstation is healthy, the card returns to green **Ready!**.

## Result to send Codex

For each platform, reply with only **Pass** or **Finding**. For a finding, attach
the saved support report and describe the last numbered step completed. Do not
collect extra diagnostics unless Codex asks after reviewing that report.

Passing both platforms authorizes Codex to record acceptance and prepare the
milestone closeout. It does not by itself authorize stable promotion or fleet
rollout.
