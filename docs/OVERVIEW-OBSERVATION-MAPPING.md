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

## Refine UX #161: standalone Change Safety finding

The Overview Change Safety card consumes the existing `RecoveryState`, request
loading state and recovery read error. It does not change the task decision,
readiness classification, native inspection or acknowledgment behavior.

- A readable account incident supplies only its own known operation name, start
  time and last-recorded time. Unknown names or invalid/missing times are shown
  as unavailable. The system snapshot currently supplies no operation name or
  start time; the card says so instead of borrowing account-incident details.
- The native observation time is labeled as the system safety check time. It is
  never presented as the time an operation started or completed.
- Recognized native reason codes explain an unconfirmed earlier process lifetime,
  unavailable restart evidence or an incomplete native activity check. Unknown
  reasons remain unknown. Missing read access does not prove a failed operation.
- Active work, incomplete package state and retained interruption review keep
  distinct wording. The card does not infer failure from an interruption or
  request a restart without supporting evidence. It references no tool-readiness,
  Python or maintenance finding.
- **Address safety finding** opens existing Recovery review. Report creation
  opens existing support review. Neither action acknowledges or clears evidence,
  terminates work, submits consent or grants permission to start a change.
- Pending reads show checking without stale operation details. A fresh clear
  safety observation removes the card; unknown package health alone is not a new
  blocker. Read errors, untrusted/unreadable sources, active/unknown activity,
  incomplete package state or outstanding acknowledgment keep review available.

All 379 unit cases pass, including eight new source/uncertainty/action-boundary
cases. Two new browser cases at 390px/1140px verify the keyboard route into
Recovery, independent Python wording, no acknowledgment/operation, removal after
a fresh clear safety observation, accessibility and narrow layout. Every earlier
test inventory and assertion fingerprint remains intact. Build/type check,
audit (zero findings), backend contracts (35), metadata tests (68), CI-policy
checks (35), documentation and diff checks pass locally. Full CI must run all
138 browser cases and all native/trust/acceptance gates before merge.

This increment does not complete the broader procedural Your next step card,
restoration/preservation or application/project-location requirements. Human
signing, exact authenticated-candidate owner UAT and separate stable promotion
remain mandatory. Opening review is never an execution permit.

## Refine UX #161: structured Python readiness card

The Overview Python card consumes existing typed runtime events and collected
validation Reports. One complete, consistent Python runtime event and one paired
Python check are required. The collection must have its timestamp, terminal
summary, matching failure count and consistent exit/success status. Duplicate,
malformed, contradictory or partial evidence cannot establish a pass or a
confirmed supported-search result. Capability failures that claim a discovered
interpreter also require its verified-family version and executable evidence.

The card distinguishes a completed supported search that found no Python 3.14,
an unfinished check, confirmed timeouts, interpreter failure, test-environment
failure and a pip capability failure. It does not parse arbitrary diagnostic
text to invent a cause or an incompatible default version. A usable verified
3.14 family removes the card; another installed Python version is not an error.
The record does not provide a default-version inventory, so the card does not
invent a “3.15 is the default” finding.

Review opens existing Validation, Check setup again runs the existing read-only
validation path, and support opens report review. These controls do not install
software, change PATH/defaults, approve a full operation, acknowledge an incident
or grant native permission. Earlier Python findings remain labeled and disabled
while the new check runs; failed collection keeps an earlier result labeled with
retry/support guidance. That retained display Report never feeds readiness,
preflight or execution decisions.

This is a bounded presentation/read-only continuation increment. A complete
missing-family installation workflow, full-operation preservation, other tool
cards and the procedural Your next step integration remain separate completion
criteria. Review of a Python check does not promise that an installation has
been approved or completed.

Local evidence: all 387 unit cases (eight added structured/continuation cases),
two narrow/wide keyboard/read-only-follow-up/accessibility browser cases,
build/type check, audit zero, backend contracts 35, metadata tests 68, CI-policy
35, docs and diff checks pass. All original assertion fingerprints/inventories
remain unchanged. Full CI must run all 140 browser cases, Windows/Mint native,
both trust jobs and acceptance. Full exact-main validation, human signing,
authenticated exact-candidate owner UAT and separate promotion remain mandatory.

## Refine UX #161: VSCodium access review on Overview

The Overview card reuses `completeEditorPreferences` and the existing
`EditorAccessReview`. It appears only for a complete, confirmed access-denied
observation of the bounded preferences file. Partial/malformed data and generic
read failure cannot be presented as a newly confirmed permission denial. The
card names VSCodium and explains it as the app used to write code; it does not
refer to Python, maintenance or Change Safety.

Opening Review access problem starts no check or mutation. The explicit recheck
runs existing read-only validation, using the same display-only earlier Report
retention as Validation. The review stays expanded for the same path. A new
confirmed path requires a new review. Incomplete collection or an unavailable /
generic read failure cannot dismiss the earlier access finding; it stays clearly
labeled as earlier evidence with retry/support. A complete fresh access-denied
result replaces the earlier observation without claiming success. Confirmed
read/defaults/invalid-contents results can settle access denial, but do not prove
other editor capabilities or settings are healthy.

Focus stays with the Overview card during its recheck and at its result. If the
card clears, focus returns to the page heading. Navigation invalidates that focus
request, so a late result cannot pull the student back from another page. The
existing Validation route keeps its behavior. Earlier Report retention remains
presentation-only and never feeds readiness, preflight, native admission or
operation consent.

No permissions, settings, app installations, native commands or IPC path
arguments are added. Normal-account and teacher/administrator access guidance
remains in the shared review. Support opens the existing report-review flow.
Other editor findings and broader procedural/setup/restoration/location work
remain separate #161 completion criteria.

Validation includes all 395 unit cases, eight new card cases, two new narrow/wide
browser cases and the two existing Validation access-review browser cases.
Browser coverage includes keyboard/focus, failed collection, generic read failure,
continued access denial, fresh defaults, navigation during a late result,
accessibility/layout and zero modifying operations. Build/type check, audit zero,
backend contracts 35, metadata 68, CI-policy 35, docs/diff pass; earlier assertion
fingerprints/inventories remain intact. Full CI must run all 142 browser cases
and the native/trust/acceptance gates. Exact-main validation, human signing,
exact authenticated-candidate owner UAT and separately authorized promotion
remain mandatory.

## Refine UX #161: Node.js/npm finding on Overview

The Node.js/npm card consumes the existing bounded runtime observation. A
confirmed result requires one structured record, one matching Node.js check,
a collection time, a terminal summary with the actual failure count, and
consistent success/exit status. The original Windows/Linux executable and
associated npm path checks remain intact. Contradictory negative states cannot
become a confirmed cause. A usable Node.js 24/npm pair hides the finding; an extra
installed version alone creates no error. Recognition remains verification only,
with maintenance eligibility explicitly not evaluated.

The card distinguishes a supported search that did not find the required family,
a Node.js command failure, an associated npm failure and an unfinished check.
Missing or malformed metadata cannot establish absence or blame another runtime.
Main wording explains npm without requiring raw technical details. The card
refers only to its own finding.

Review opens existing Validation. Check setup again uses existing read-only full
validation and updates the finding on Overview. Earlier observations stay labeled
while the check runs or if collection fails; they never feed readiness or native
admission. Support opens the existing report-review flow. These actions install
nothing and change no defaults, package permissions or operation consent.
Supported installation, full-operation preservation/restoration and the broader
procedural summary remain separate completion criteria; this increment does not
promise a Node.js-only Repair.

Validation adds eight unit cases and two narrow/wide browser cases covering
keyboard review, timeout, npm failure, in-place successful recheck, accessibility,
layout and zero modifying operations. All original assertions and inventories
remain intact. Full CI must cover all 403 unit and 144 browser cases and preserve
Windows/Mint native, trust, integrity and acceptance gates. Exact-main evidence,
human signing, authenticated exact-candidate owner UAT and separately authorized
promotion remain mandatory.

Local evidence: all 403 unit cases, the two new Node.js/npm browser cases and four
existing Python/VSCodium Overview browser cases pass. Build/type check, audit
(zero vulnerabilities), backend contracts 35, metadata 68, CI-policy 35 and offline
document/diff checks pass. Native and full-browser evidence remain CI requirements.

## Refine UX #161: procedural Overview action plan

After complete structured collection, Your next step lists the current supported
Overview review items and links directly to their card headings. The singular or
plural heading uses the actual list length. Python, Node.js/npm, VSCodium access,
Change Safety and maintenance share their existing card visibility predicates
with the plan. A passing runtime removes its own item without dismissing safety.
Each card still explains only its own situation.

The plan is navigation only: a keyboard or pointer activation focuses and scrolls
to the existing card. It does not run validation, acknowledge an incident, save a
preference or approve a setup change. Card review actions retain those explicit
steps. Weekly maintenance uses the neutral View weekly maintenance details label:
a saved disabled choice is not converted into a broken-tool claim. Existing
supported actions remain available under Other actions.

The ordinary plan does not replace progress, operation review or result screens.
Unsupported platforms, pending or partial collection, legacy diagnostic-only
reports and failures without a corresponding card keep the existing guidance.
Earlier display-only findings retained by cards are not counted as fresh results.
No operation/default/native API, safety decision or consent authority changes.

Eight new unit cases cover combined and single findings, independent resolution,
editor and maintenance links, fallback states, disabled links and actual focus.
Two narrow/wide browser cases verify the combined Python/safety flow, changing
counts after read-only validation, focus, accessibility, layout and zero mutation
or acknowledgment. All original assertions and test inventories remain intact.
The full suite now requires 411 unit and 146 browser cases. Supported installation,
full-operation preservation/restoration, other tool/editor findings and app/project
locations remain open #161 criteria. Full PR and exact-main native/trust/integrity/
acceptance validation, human signing, authenticated exact-candidate owner UAT and
separate promotion authorization remain required.

Local evidence: all 411 unit cases, the two new plan browser cases and ten existing
card browser cases pass. Build/type check, audit zero, backend contracts 35,
metadata 68, CI-policy 35 and offline document/diff checks pass. Full browser and
native evidence remain CI requirements.
