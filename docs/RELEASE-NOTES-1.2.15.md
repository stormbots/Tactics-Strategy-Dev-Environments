# SDE 1.2.15 — deployment readiness and self-update acceptance

Proposed immutable candidate; publication and owner acceptance are pending.
This release prepares a repeatable mentor migration/UAT/pilot process and a real
application version transition while preserving the existing managed-tool baseline.

- Reconciles the Windows legacy Logs migration already shipped in v1.2.6 with
  native tests and owner evidence; keeps its narrow protected-file trust boundary.
- Replaces stale initial-pair commands with current candidate authentication,
  native installation and preservation checks, plus explicit fresh-install limits.
- Prepares unpublished same-source 1.2.14/1.2.15 Windows SYSTEM/Mint userland upgrade
  fixtures and fresh v1.2.15 prerelease publication after exact-main verification
  and protected human signing review.
- Provides a device-scoped pilot packet, pause/recovery instructions and a
  criterion-level acceptance matrix. Retains actual v1.2.14 Windows/Mint installs
  for the later live newer-stable discovery test tracked in #99.

App/activated engine identity: **1.2.15**. Managed-tool baseline: **1.2.1**.
App installation preserves an existing applied baseline, student files/settings,
schedule and application-update policy. An incompatible legacy baseline may
correctly require separately authorized Repair. Tool provisioning/Update, policy
resume and maintenance triggers remain separate operations.

No new application feature or migration production-code change is proposed.
Prior accepted v1.2.14 UI behavior and sidebar correction are retained. Full native
checks and owner Windows 11/booted Mint Cinnamon UAT have distinct evidence scopes.
Manual installation does not prove automatic installation or retained signed
recovery. Current execution state and limits: [acceptance ledger](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/v1.2.15/docs/DEPLOYMENT-READINESS-EXECUTION.md),
[owner UAT](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/v1.2.15/docs/SELF-UPDATE-UAT.md), [pilot packet](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/v1.2.15/docs/SELF-UPDATE-PILOT.md).

Publish only as a prerelease with five signed distribution assets. Stable/latest
promotion requires exact-candidate owner acceptance/authorization and preserves
the same source/tag/assets. Device resume/pilot and any later fleet expansion
require their own scoped decisions. #43/milestone closure additionally requires
representative rollout evidence or an explicit owner-approved scope disposition.
