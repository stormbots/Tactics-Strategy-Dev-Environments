# Guided Overview — new Codex chat handoff

Prepared November 6, 2026. Documentation/planning only; no application changes,
demo edits, CI runs, signing requests or release actions were made for this update.

## Starting point

- Repository: `stormbots/Tactics-Strategy-Dev-Environments`.
- Cloud workspace: use the repository root selected by Codex; do not assume a
  particular local path. All file paths below are repository-relative.
- GitHub planning branch: `codex/overview-next-step-design`. Fetch/select this
  branch in Codex Cloud before reading the design or beginning implementation.
- Existing planning commits: `c692a19` (design), `af0a231` (offline prototype),
  `58d349b` (owner's update-state correction), `69b4651` (31-workflow UAT draft).
- Lifecycle refinements and the initial handoff: `a44cfd4`. This cloud handoff is
  a subsequent documentation commit; resolve the remote head rather than guessing
  its SHA. The publishing chat records the verified exact remote SHA on #146.
- The branch contains the design, prototype, UAT draft and this handoff. If the
  initial cloud checkout is main, fetch the planning branch normally. If access
  fails, diagnose configured GitHub access; do not recreate the design from memory
  or assume this chat's filesystem is available in a new cloud environment.
- Stable v1.2.22 source: `2320297d5048d627124ff64dd907889e1abccad6`.
  It has separate accepted UAT; that acceptance does not cover this new interface.

## GitHub work queue

[Refine UX milestone #8](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/milestone/8)
and [tracking issue #146](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/146)
are the durable project entry points. Native sub-issue/dependency links are set.

| Ticket | Work | Required predecessors |
| --- | --- | --- |
| [#147](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/147) | Shared observation/recommendation logic | None; start here |
| [#148](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/148) | Guided Overview UI | #147 |
| [#149](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/149) | Operation lifecycle and return paths | #147, #148 |
| [#150](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/150) | Full workflow/native evidence | #147, #148, #149 for final acceptance |
| [#151](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/151) | Authenticated candidate and owner UAT | #150 plus human signing/UAT gates |

Read live ticket bodies/comments and dependencies before claiming work. Existing
related issues #7, #8, #10 and #87 are references, not permission to reopen their
whole backlogs or override current ADR/released safety contracts. No engineering
ticket was started, assigned or closed by this housekeeping handoff.

## Read first

1. Root `AGENTS.md` and its applicable domain/issue-tracker instructions.
2. [Design](OVERVIEW-NEXT-STEP-DESIGN.md), including sections 9, 10 and 13.
3. [Draft validation/UAT plan](OVERVIEW-NEXT-STEP-UAT-DRAFT.md), all WF01–WF31.
4. [Offline prototype notes](overview-next-step-demo/README.md) and
   [demo](overview-next-step-demo/index.html).
5. [Accepted Recovery clear state](RECOVERY-CLEAR-STATE.md) and the linked ADRs.

## Copy into the new chat to authorize implementation

```text
Begin engineering and DevOps work on the Refine UX milestone (#8), tracking issue
#146, for stormbots/Tactics-Strategy-Dev-Environments. Start with #147, then follow
the native dependencies through #148–#151 in bounded, verifiable increments.

Use the GitHub branch codex/overview-next-step-design and read
docs/OVERVIEW-NEXT-STEP-HANDOFF.md. Work from the actual repository root, not a
hard-coded workspace path. Verify repository status, configured GitHub read/write
and workflow access, and the remote planning head. Fetch/select the branch if the
initial checkout is main. Preserve unrelated changes; no reset, force push or
invented credentials. If access is missing, report the concrete blocker.

Read AGENTS.md and issue-tracker instructions before reading/claiming live tickets.
Keep the published planning baseline intact; use a scoped implementation branch
based on it, checking current main for relevant intervening changes. Record the
base and any integration decisions. Do not drop planning docs or overwrite newer
work to recover the old baseline. Claim #147 only when actually beginning work.

Read AGENTS.md and applicable instructions, then the complete
docs/OVERVIEW-NEXT-STEP-DESIGN.md and
docs/OVERVIEW-NEXT-STEP-UAT-DRAFT.md. Follow the owner-reviewed prototype journeys
with the recorded update-state correction. Implement the real application, not
another demo. Keep the prototype unchanged; it is not the production acceptance
oracle.

Replace the Install/Repair/Validate/Update tabs with one clear next-step card,
in-place review/progress/result, Other actions and Details. Preserve current
native operations, honest review scope, confirmations, elevation, diagnostics,
history and the accepted Recovery clear card. Startup remains bounded/read-only
on Overview; unchecked setup is not a fabricated recovery incident.

For ready-with-tool-updates, keep the top “Ready!” status and use exactly:
Heading: “Install updates”
Body: “Your setup works, but there are updates available if you would like to
install them.”
Primary action: “Review updates”
Keep editor access under Other actions; updates stay optional. Do not repeat the
Review updates action below the primary button or conflate app and tool updates.

Implement and test explicit failed/partial/incomplete outcomes, proven-not-started
versus uncertain cancellation, fresh reconstruction after reopen, changed evidence
at execution, combined-finding precedence, and current complete verification
before Ready. Reject stale asynchronous results and duplicate submissions. Every
secondary mutation uses the same busy/review/admission boundaries. No automatic
replay, repair loop, repeated elevation, invented backend facts or safety bypass.

Work in bounded verifiable phases: first map real typed observations and identify
evidence/fixture gaps; then implement/test the shared presentation decision; then
integrate the real UI and operation lifecycle. Use all WF01–WF31 as the acceptance
checklist. Keep native safety authoritative. Report any missing observation that
requires a materially broader backend change before expanding scope.
Keep issue acceptance criteria, native dependencies and evidence up to date; do
not close blocked tickets or the milestone because a prototype or partial test
passes. Fixture planning may proceed early, but #150 final acceptance requires
all integrated predecessors and #151 requires the full validation evidence.

Own engineering and DevOps: run targeted tests, push scoped changes/open a PR and
run existing authoritative CI; diagnose failures and retry justified transient
infrastructure failures. Preserve every applicable acceptance gate, including
Windows feasibility/bootstrap, trust/coordinator checks, signed SYSTEM upgrade
and actual Mint 22.3 bootstrap/manual/scheduled-tool and signed-upgrade coverage
where required by the existing workflows. Do not waive, skip or weaken gates.
Keep synthetic browser, native fixture and installed owner evidence distinct.

Do not continuously poll or occupy a session waiting for CI. Record exact branch,
SHA, run URLs, completed/pending checks, defects/coverage gaps and the next action
in a durable checkpoint before handing back. A later “jobs done” message means
inspect results and continue authorized engineering, not merely report status.

Stop for human signing approval when required and for owner UAT on the exact
authenticated candidate. Prepare one consolidated candidate and the focused owner
checklist after automated/native validation. Never approve signing yourself, infer
UAT acceptance from prototype approval, or promote a release without separate
owner authorization. No fleet action, automation/policy resumption or unrelated
CI optimization. Preserve original Windows interruption evidence and historical
Mint v1.2.18 35/0/0 acceptance. Do not manufacture failures on owner laptops.
```

The prompt above is intended for the owner to paste when ready to begin coding.
Writing it does not initiate implementation or authorize release promotion.
