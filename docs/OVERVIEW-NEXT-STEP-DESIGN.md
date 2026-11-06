# Overview: one clear next step

Status: initial design proposal for owner review. No application changes approved
or implemented by this document.

Prepared November 6, 2026. Reference: the v1.2.22 interface, the owner's screenshot
and feedback, and the existing frontend/recovery contracts. Release source:
`2320297d5048d627124ff64dd907889e1abccad6`.

## 1. Recommendation

Replace the Install / Repair / Validate / Update tabs with a guided **Your next
step** card. Give the student one recommended action based on what SDE actually
knows. Keep individual operations available under **Other actions**, not as four
equal choices and not with Install permanently selected.

Overview should answer two questions immediately:

1. Is this computer ready for my work?
2. What should I do next?

This is a guided sequence, not an installation wizard everyone must repeat.
A ready computer should lead to coding, not another installation or maintenance
task. A new or unchecked computer should receive setup guidance, not an implied
recovery incident. Genuine safety blockers remain visible and enforced.

## 2. Problems this fixes

- Install is currently prominent even on a working computer. Its selection is
  not evidence that installation is necessary.
- The student must understand the difference between Install, Repair, Validate
  and Update before choosing an action.
- Overview mixes tool readiness, package activity, update availability and
  maintenance history in one busy area, with several competing links/buttons.
- Result, preflight and operation panels can duplicate status and actions instead
  of explaining one continuous task.
- Missing observations can look like a broken environment. Conversely, a passing
  tool check can be mistaken for permission to change an interrupted environment.

The screenshot reports both a Python finding and unknown package activity.
It does **not** establish that validation alone caused the Recovery warning.
This design must not assume that diagnosis or hide either observation.

## 3. Screen layout

Keep the familiar sidebar, branding, themes and zoom controls. Simplify the main
area rather than introducing a new dashboard or another status card.

```text
Your development workstation

┌──────────────────────────────────────────────────────┐
│ DEVELOPMENT ENVIRONMENT                              │
│ Setup needed                                         │
│ Some tools still need to be installed.                │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ YOUR NEXT STEP                                       │
│ Set up this computer                                 │
│ SDE will show you what is needed before making changes.│
│                                                      │
│ [Review setup]                                       │
│                                                      │
│ ▸ Other actions                                      │
│ ▸ Details                                            │
└──────────────────────────────────────────────────────┘
```

The first card is the existing workstation status card, made smaller and mostly
informational. The second replaces **Manage your environment** in its existing
location. It contains the only filled primary action in the main content area.

- Remove the four operation tabs and “Four simple ways to stay ready.”
- Remove duplicated editor/workspace buttons from the status and result cards.
- Put operation review, progress and result content in the next-step card. Do not
  stack a new preflight or success card above the old operation controls.
- Put check totals, observation times, tool versions and per-tool update counts
  behind Details or in the existing Validation page.
- Keep the detailed Development tools list collapsed by default, available below
  the main task. Do not lose the existing per-tool findings or update review.
- Keep Schedule and About available. Do not rename sidebar destinations in the
  first implementation; the UI may say “Check my setup” while Validation remains
  the detailed-results destination.
- Recovery remains available for diagnostics/history. Historical incidents alone
  do not make it the default destination or produce an attention badge.

Navigation, disclosure controls and contextual Back/Cancel are allowed. “One
action” means one obvious recommended action, not removing necessary escape routes.

## 4. Separate readiness from permission to make changes

Use two independent questions internally:

- **Work readiness:** Are the required tools and configuration present and checked?
- **Change safety:** Do current trusted observations permit an operation to enter
  its normal review and fresh native authorization path?

Neither answer substitutes for the other. Examples:

- Tools may pass validation while an interrupted operation still blocks changes.
- No active installer may be detected while required tools are missing.
- Unknown package health alone is not an interrupted operation or proof of damage.
- An unavailable maintenance record is not proof that setup failed.
- Installing the SDE application does not prove that the development tools have
  been installed. A missing local success record also does not prove a fresh PC.

The frontend chooses an explanation and next action, never execution authority.
Native checks, locks, identity/signature rules and normal OS approval still apply.
This follows ADRs [0001](adr/0001-interruption-acknowledgment-boundary.md) and
[0002](adr/0002-lease-bound-recovery-transition.md); neither should be reopened
merely to make the interface simpler.

## 5. Recommended states and actions

The table describes the default presentation. A higher-priority safety finding
can replace the next action without erasing tool-readiness findings.

| Situation | Status | Next-step heading | Primary action |
| --- | --- | --- | --- |
| First read-only check is running | Checking your setup… | Finding your next step | None; show progress |
| No complete check is available yet | Not checked yet | Let’s check your setup | Check my setup |
| Checks could not finish | Check not finished | Try checking again | Check again |
| Fresh/incomplete setup is supported by current findings | Setup needed | Set up this computer | Review setup |
| Existing setup has an identified SDE-repairable problem | Setup needs a fix | Fix your setup | Review fixes |
| Finding cannot be fixed by an existing supported operation | Setup needs attention | Follow the recommended fix | Review the issue |
| Required checks pass; no safety blocker | Ready! | Start building | Open VSCodium |
| Ready with optional tool updates | Ready! | Install updates | Review updates |
| A package operation is known active | Changes are paused | Let setup finish | Check again |
| Activity is unknown | Changes are paused | Check whether setup has finished | Check again, with safe guidance |
| Safety records are unreadable/untrusted | Safety check unavailable | SDE couldn’t verify that changes are safe | Check again |
| A current incident needs acknowledgment | Review an interruption | Review what happened | Review interruption |
| Known incomplete package state blocks changes | Changes are paused | An installation needs attention | Review the issue |

Presentation priority:

1. SDE's own in-progress action or confirmation, so it does not disappear mid-task.
2. Authoritative current safety blockers before offering another change.
3. Missing, failed or incomplete readiness observations.
4. Identified setup/repair needs.
5. Ready-to-work state.
6. Optional updates and routine maintenance information.

Within safety findings, known active work takes precedence over repair/restart
instructions; untrusted/unavailable evidence cannot be treated as clear. Follow
the backend's combined decision rather than inventing a second safety policy.

### Color and wording

- Neutral: unchecked, checking, unavailable observation without confirmed damage.
- Amber: setup is needed, a correctable issue or a temporary safety pause.
- Red: verified blocking faults or trusted severity indicating a serious problem,
  not merely a missing timestamp, unavailable update count or first launch.
- Green: readiness was established. If changes are separately blocked, use a
  clear paused status instead of an unqualified Ready headline; explain that the
  tools passed but changes remain paused.
- Use text and icons as well as color. Never turn the screen green to dismiss a
  native blocker. Maintenance or update uncertainty is reported without inventing
  package health, successful work or a completion time.

## 6. The normal guided journeys

### A. Opening SDE

Land on Overview. Continue the existing bounded, read-only startup checks, without
requesting elevation or starting installation. Show one checking state while the
necessary observations load. Do not require a redundant Check click if a complete
startup check already succeeded.

Do not automatically redirect to Recovery when an initial query is slow, missing
or blocked. Show its specific finding and safe action on Overview. A real blocker
must still be obvious and block changes; changing the landing page is not a bypass.
Review interruption is an explicit route to Recovery when needed.

If the check cannot complete, offer Check again. Preserve partial results in
Details, but do not label them a complete pass. No indefinite background retry
loop, repeated elevation prompts or fabricated percentage progress.

### B. Setting up a computer

```text
Check → Review setup → Confirm installation → Install → Verify → Start building
```

The review identifies missing tools, intended configuration/workspace/schedule
changes, required network/space conditions and administrator approval. It must
not pretend Install changes only the missing items if the backend reapplies the
full baseline. Show that scope plainly.

Primary action on the review: **Install development tools**. Back returns to the
recommendation without starting anything. Starting uses the current preflight,
confirmation and privilege paths. Recheck changing safety conditions at execution.

During work, replace choices with a short stage message and honest progress:
“Installing development tools…” / “Checking your setup…”. Detailed output stays
collapsed and accessible. Do not claim completion from a successful process exit
alone.

Reuse installation's existing final validation if it is complete and suitable.
If a separate read-only check is necessary, chain that check only—not another
mutation. Avoid making students press Validate after an already verified install.

If installation completed but verification did not, say:

> Setup finished, but SDE couldn’t finish checking it.
> Check your setup before starting another installation.
> [Check my setup]

Use that message only if installation completion is known. If the outcome is
unknown, say it is unknown and preserve the incident/recovery path.

### C. Fixing an existing setup

```text
Check → Explain the finding → Review fixes → Confirm repair → Repair → Verify
```

Show the problem first, in ordinary language: “Python needs attention,” with the
actual reason when known. Recommend Repair only if that finding maps to an
existing supported repair. Do not translate every FAIL into a generic Repair.

Review fixes shows the real scope of the repair operation, preservation behavior
and any documented effects on standard configuration. No new selective-repair
engine is implied. Show **Repair setup** as the review's primary action only
after that scope is clear. Finish with the same readiness verification rules.

An unsupported or unresolved issue gets specific instructions and optional
support. Do not loop the student through Repair automatically or promise that a
restart/reinstall will fix unknown conditions.

### D. Working on a ready computer

The main status is **Ready!**. The next-step card says:

> Start building
> Your required tools and configuration passed the latest check.
> [Open VSCodium]

Open Development remains available under Other actions. No Install button appears
in the default ready view. When optional tool updates are available, use the
owner-reviewed update presentation below instead. The environment remains Ready.

### E. Updating tools

Owner feedback recorded November 6, 2026; this revises the initial proposal,
not the existing HTML demo.

Keep the top **Development environment** card and its prominent **Ready!**
headline. Available updates do not imply that the working setup is broken.

In **Your next step**, show exactly:

> Install updates
> Your setup works, but there are updates available if you would like to install them.
> [Review updates]

Replace the Open VSCodium primary button with the existing Review updates action;
do not also repeat Review updates as a separate link below it. Review opens the
existing tool-update preview in the task area, not a second dashboard of buttons.
Identify what updates and the approved runtime boundaries before **Update tools**.
Never present an app update and a development-tool update as the same operation.

Updates remain optional. The heading and primary action recommend a review, not
automatic installation or a prerequisite for using the editor. Keep Open VSCodium
and other alternatives available in **Other actions**. If no updates are available,
retain the normal Start building / Open VSCodium presentation.

App-update discovery/notification and pause policy remain functional. Avoid
duplicating the notice in multiple cards. Do not invent urgency or silently hide
an existing important notice to maintain the one-button aesthetic.

## 7. Secondary actions and detail

**Other actions**, collapsed by default, contains the available existing tools:

- Check my setup (Validate): read-only readiness check.
- Install development tools: explicit full setup review, never a default selection.
- Repair setup: existing repair review, with its actual scope.
- Review tool updates: existing preview and confirmation.
- Open Development: workspace shortcut, when its destination is available.
- Open VSCodium: editor shortcut when it is not already the primary action.

The owner explicitly endorsed this grouping: alternatives in **Other actions**;
results, logs and reports under **Details**. Retain that separation.

Do not duplicate the current primary action here. Mutating choices are disabled
or routed to an explanation while safety blocks them. They are not an escape
hatch. Retain ordinary diagnostic access even when changes are blocked.

**Details**, collapsed by default, explains the current recommendation: latest
check time, counts, relevant failures, safety observations and maintenance/update
status. Link to the existing detailed Validation, Recovery and Schedule surfaces
when relevant. Full logs, report generation/export and history remain reachable;
they do not need to crowd the default card.

An unavailable maintenance history gets a quiet explanation, not a red environment
failure by itself. A known maintenance failure must remain visible with a relevant
details/log route and next action. Do not classify maintenance as optional if its
underlying finding also establishes a real safety or readiness problem.

## 8. Recovery within the guided interface

Recovery is for current incident handling and safety findings, not ordinary
onboarding. Keep the accepted v1.2.22 no-recovery card and its exact wording when
the user voluntarily opens Recovery and nothing requires attention.

For real findings, preserve the existing reviewed behavior:

- Known active work: wait and Check again. Never suggest killing installers.
- Unknown activity: explain uncertainty; offer the existing normal-Restart
  guidance only when applicable. Never restart automatically. Legacy provenance
  can require another restart after first capture; keep that explanation in details.
- Unreadable records: recheck/support. Do not promise that restart repairs trust.
- Acknowledgment: explain what happened and that evidence is preserved. Summary
  generation remains automatic as part of acknowledgment, not a second task.
- Matching submitted intent is not a privileged receipt or permission to execute.
  Source-specific partial failures and report-save warnings remain visible.
- Passing Validation does not acknowledge or clear an interruption.

Returning from Recovery recomputes the recommendation. It never replays a change
just because an incident was acknowledged or a safety observation improved.

## 9. Busy, failure, cancel and restart behavior

- One operation at a time; disable duplicate submissions and competing mutations.
- Cancelling a review cancels only the pending request and returns to Overview.
- Navigating away does not stop a running installer or erase progress/evidence.
  Returning shows the active task; a persistent running-status cue remains visible.
- Do not add a Stop button that kills package operations. If a supported safe
  cancellation path exists, describe its actual effect rather than promising rollback.
- Close/reopen or OS restart discards an unstarted request. Inspect fresh state
  before any new recommendation; never restore execution permission from UI storage.
- A stale click or changed evidence sends the student to the newly applicable
  explanation, without silently executing an old action.
- Network, download and authorization failures are described distinctly. A denied
  administrator prompt is not a broken installation when nothing started.
- Read-only diagnostic failure does not imply damage. Unknown mutation outcome
  does not imply cancellation or success.
- Support sharing stays optional and includes the existing privacy reminder.

## 10. Recommendation logic and evidence limits

Create a single presentation decision used by the status and next-step cards,
not independent conditionals that can recommend Install while showing Recovery.
Its inputs are existing typed readiness, incident, native safety, operation,
maintenance and update observations, with source availability/freshness.

The decision produces a headline, plain-language explanation, one primary action,
relevant secondary actions and a reason suitable for testing/details. Action IDs
map to existing reviewed commands; no dynamic commands, new privileged grants or
browser-derived safety overrides.

Do not hard-code the current count of checks or assume the slowest background
query determines readiness. A complete readiness result requires all required
observations; optional update discovery may still be unavailable.

“First-time setup” versus “repair” needs reliable evidence, not the current tab,
first GUI launch, absent report history or a missing timestamp. Prefer supported
missing-tool/prior-setup observations. If evidence is insufficient, use the
neutral **Review setup** route and explain the actual operation scope. Do not
invent a new “fresh machine” flag that authorizes changes or clears a blocker.

Persist only harmless presentation preferences, if necessary. Every operation
keeps its current preflight, source-bound consent, native recheck and OS approval.

## 11. Accessibility and responsive behavior

- One filled primary action in the visible task area, with a descriptive label.
- Readable normal/hover/focus/disabled styles in all existing themes. Preserve
  the recently fixed Recovery button contrast and existing zoom support.
- Native buttons and disclosure semantics; no hover-only actions or color-only status.
- Focus the new task heading after explicit navigation. Do not steal focus during
  a background refresh, collapse a section the student is reading or change a
  button's action under their pointer. Revalidate when it is activated.
- Announce important stage changes politely, not every log line or counter update.
- On narrow displays, use one column and keep the primary action near its
  explanation. No horizontal scrolling for normal text or hidden action labels.
- Keep the recommendation, review, result and source findings reachable by keyboard.

## 12. Scope and trade-offs

Proposed first implementation: Overview presentation, shared recommendation logic,
in-place operation/review/result layout and student-facing copy. Reuse existing
native operations, previews, diagnostic/report/history pages and safety contracts.

Not included: a new recovery bypass, journal lifecycle changes, selective package
repair, rollback/uninstall, automatic mutation, a new service, expanded OS support,
update-policy changes, a release rebuild, fleet action or another CI optimization.

The main trade-off is less choice on the default screen in exchange for more
responsibility in SDE's recommendation. Other actions preserves expert control.
Neutral fallback language handles uncertainty instead of pretending the software
knows which operation will succeed. Recommendations may be conservative; safety
cannot be simplified away.

Proposed defaults for owner review: Overview always opens first; startup checks
remain automatic/read-only; ready users without updates see Open VSCodium; ready
users with updates see Install updates / Review updates while keeping editor
access under Other actions. Existing sidebar labels and accepted Recovery page
are retained. The November 6 update-state feedback supersedes the original
secondary-update-link recommendation; the demo is intentionally not updated yet.

## 13. Acceptance criteria

1. A fresh app launch does not select or imply Install by default. Checking and
   unchecked states do not claim an interruption or successful setup.
2. A complete passing startup check skips redundant validation steps and leads
   to Start building. Opening the editor does not trigger setup or elevation.
3. Missing tools, an identified repair need and an unreadable check each produce
   appropriate guidance. No unsupported finding is blindly mapped to Repair.
4. Each main-content state has at most one filled primary action; old tabs and
   duplicate status/result/editor controls are absent from the default view.
5. Install/Repair/Update stay accessible under Other actions and retain their
   actual review scope, confirmations, supported platform rules and OS approval.
6. Progress and verification replace the same task card. No unnecessary second
   validation runs when existing final verification is complete.
7. Known active/unknown/untrusted/incomplete native states never authorize a
   mutation through primary or secondary controls. New setup does not bypass them.
8. Unknown package health alone and unavailable maintenance/update history are
   not fabricated incidents, proof of damage or full readiness evidence.
9. Existing incident acknowledgment, automatic summary attempts, retained evidence,
   source-specific warnings, diagnostics/history and no-replay behavior remain.
10. Check Again or successful Validation never clears an interruption. Changing
    evidence after review is caught by fresh native checks.
11. Keyboard, screen-reader, theme, zoom, contrast and narrow-screen tests pass;
    background refresh does not create focus churn or duplicate operations.
12. Windows interruption evidence and Mint v1.2.18's accepted 35/0/0 result stay
    untouched. UAT does not require manufacturing an incident or reprovisioning
    a healthy laptop merely to test this interface.

## 14. Suggested implementation and review sequence

This is a future plan, not authorization to begin coding.

The [draft workflow validation and UAT plan](OVERVIEW-NEXT-STEP-UAT-DRAFT.md)
records the reviewed demo scenarios, failure/escape paths, responsible testers
and release evidence gates. Prototype walkthrough approval is not native UAT.

1. Owner reviews this document's layout, default actions and uncertainty handling.
2. Implement/test the presentation decision table separately, including unknown,
   stale, partial and contradictory observations. Keep the backend authoritative.
3. Integrate the existing cards and action/review/result views. Remove duplicated
   controls; preserve all native paths and the accepted Recovery clear state.
4. Test representative browser states in both themes, existing zoom levels and
   narrow/desktop widths. Test cancellation, changed evidence and diagnostics
   while blocked; run the complete existing native/trust/upgrade CI gates.
5. Provide one consolidated signed UAT candidate after normal human signing
   approval. Owner checks a normal ready path, existing naturally occurring
   attention state and the short setup-review flow without destructive actions.
   Codex handles fixtures and regression testing; do not repeat the owner's
   already accepted tool provisioning solely for UI coverage.

If current observations cannot distinguish unchecked setup from a genuine native
unknown state, document that evidence gap before implementing the affected branch.
Do not close it by weakening the existing safety decision or fabricating backend
facts. Any required new observation must be separately specified and read-only.

## 15. Source references

- [Current Overview and operation controls](../installer/src/App.tsx).
- [Validation/readiness presentation model](../installer/src/model.ts).
- [Typed recovery observations](../installer/src/recovery.ts).
- [Current Recovery guidance](../installer/src/RecoveryPage.tsx).
- [Accepted no-recovery card contract](RECOVERY-CLEAR-STATE.md).
- [Prompt-free acknowledgment boundary](adr/0001-interruption-acknowledgment-boundary.md).
- [Fresh safety and lease-bound transition](adr/0002-lease-bound-recovery-transition.md).

This proposal diagnoses a presentation/design problem, not the specific native
cause of the screenshot's unknown activity or Python failure. Those findings must
remain honest during the redesign.
