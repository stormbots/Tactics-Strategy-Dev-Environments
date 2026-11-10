# Guided Overview observation mapping — #147

Implementation base: planning head `d7cd425f56a992a233804132eeadd2918fe25cd3`.
Remote main checked at `2320297d5048d627124ff64dd907889e1abccad6`; no intervening
application changes to integrate. Planning documents and prototype are retained.

## Real inputs and limits

| Input | Existing source | Presentation use / limit |
| --- | --- | --- |
| Required check rows, terminal summary, process outcome | `Report`, `checksFrom`, `parseEvent`, `reportPassed` in `model.ts`; Windows `Validate-SkyviewEnvironment.ps1` and Linux `Validate-SkyviewStudentDev.sh` | Complete collection requires rows, a valid collection time, and a final validation/summary/error event that is a summary with the matching failure count. Tool metadata may follow. Ready additionally requires existing `reportPassed`. No hard-coded check count. |
| Collection time | `Report.validation_collected_at`; native `protocol::validation_time` | Dates actual check output, including partial/failed checks. It is not completion evidence or an age-based lease. |
| Native safety, sources, activity and acknowledgment | `RecoveryState`, native `recovery_state::assemble` | Native combined readiness/decision controls review availability. Known active work gets wait guidance even with another finding. Other blockers retain native guidance and details; unknown health alone does not create an incident. Ready-for-native-recheck is never execution permission. |
| Repairability | `validationGuidance` | Only recognized repair findings suggest Repair. Missing tools use neutral Review setup with full scope; unsupported/manual findings route to Validation. No inference from account history, installed SDE, selected tab or absent timestamps. |
| Tool updates | `ToolRecord[]`, `ToolPreview`, report tool events | Only current confirmed update records drive Review updates. Unknown discovery stays explicit in Details without invalidating otherwise established readiness. App discovery remains separate and cannot create a tool-update recommendation. |
| Maintenance | `Schedule` / `MaintenanceObservation` | Preserve the complete observation in Details. Known failures must remain visible there with the existing Schedule route. Missing history does not fabricate damage. A failed required schedule check still counts as a required failure and routes to its supported guidance. |
| Owned task | Existing review flags, `State.stage`, `Mode`, pending operation | The caller identifies an actual review/running/verification/result owner; that task stays in place with new safety findings retained in Details and no competing actions. Task/result rendering belongs to #148/#149. |

The existing `State.validationComplete` means passing, not merely fully collected.
The new decision consumes the original Report rather than guessing completion
from State/check totals. Retain the Report in the integration layer.

## Freshness and dispatch integration contract

`overviewDecision.ts` exports the pure decision shared by both future cards,
fixed action destinations, and request-bound observation helpers. No native
operation, journal, permission, policy, acknowledgment or report storage changes.

For #148/#149:

1. Initialize slots with request 0, null value and pending false (never checked).
   A settled null after a request means unavailable, not unchecked.
   Keep an in-memory epoch for the current workstation/operation context. Advance
   it before an operation invalidates observations, and on context replacement.
   Never hydrate readiness, a pending request or authority from UI storage.
2. Start each observation with `beginObservation`, synchronously retaining the
   returned slot/ticket. Settle only through `settleObservation` against the latest
   slot. Both successful and failed responses must use that same ticket. A failed
   inspection settles to null. Requests supersede old values immediately.
3. Refresh affected validation, recovery and tool observations in the new epoch.
   Unchanged old slots are ignored by the decision. Bounded read-only startup
   queries remain; do not add timer retry loops or time-based safety assumptions.
4. Capture `overviewReviewBinding` and the fixed action/scope at review time.
   Compare again on activation. Changed evidence means explain/review afresh,
   without silently changing the focused control. This binding is deliberately
   conservative and is not a receipt or native capability.
5. Route IDs via the existing `start`, reviews, navigation and destination APIs.
   Primary and Other actions share the existing synchronous in-flight guard,
   supported scopes, confirmations, preflight and fresh native admission.
   Never invoke a mutation directly from the presentation decision.
6. Render task lifecycle outcomes from actual native `mutation_outcome` and
   operation evidence. A complete check is not proof that a mutation completed;
   uncertain cancellation and partial/failed outcomes need the #149 result view.

## Evidence gaps and bounded scope

- There is no reliable prior-setup/new-machine field. Missing tools therefore
  use Review setup, not a fabricated first-install/repair classification.
- Reports have a terminal validator summary, but no independent required-check
  manifest or validation-run identity. This increment uses the existing trusted
  validator contract plus caller request/epoch identity; arbitrary fabricated
  rows are not a completeness oracle. A future manifest would require a separately
  specified read-only backend change, not a guessed count here.
- #148 supplies explicitly synthetic collection times in the browser preview
  Reports. Native collection semantics are unchanged. The offline prototype
  remains unchanged and is not an acceptance oracle.
- #148 connects the shared presentation decision to retained Reports and existing
  observations in App. Validation and safety queries use request/operation-context
  guards; focused action IDs are held until blur or explicit re-review. Generic
  helper contracts above remain guidance for #149's fuller lifecycle/review binding.
  Native races/admission and integrated reopen remain #149/#150 evidence obligations.
- No new backend observations are needed for this bounded decision module.

## Acceptance and evidence ownership

Decision tests cover WF01–WF02, WF06–WF07, WF09–WF10, WF14–WF17, WF20–WF22 and
WF27 at the synthetic decision layer only. In particular: missing/failed/stale
checks, current required verification, combined blockers, safe unknown health,
unsupported guidance, exact optional-update copy, late responses and changed
review bindings. Production-component browser evidence added in #148 is recorded separately in
OVERVIEW-GUIDED-UI.md. Complete WF01–WF31 integrated/native/owner acceptance
remains #150/#151; these decision tests do not satisfy it by themselves.

Keep every existing Build/native/trust/Windows SYSTEM/Mint 22.3 upgrade gate.
Human signing approval, authenticated candidate owner UAT and separately
authorized stable promotion remain distinct mandatory gates. Original Windows
interruption evidence and historical Mint v1.2.18 35/0/0 remain untouched.
