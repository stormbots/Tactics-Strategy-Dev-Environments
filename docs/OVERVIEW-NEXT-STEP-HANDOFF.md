# Guided Overview — new Codex chat handoff

Prepared November 6, 2026. Documentation/planning only; no application changes,
demo edits, CI runs, signing requests or release actions were made for this update.

## Starting point

- Repository: `stormbots/Tactics-Strategy-Dev-Environments`.
- Workspace: `/workspace/Tactics-Strategy-Dev-Environments`.
- Planning branch: `codex/overview-next-step-design`.
- Existing planning commits: `c692a19` (design), `af0a231` (offline prototype),
  `58d349b` (owner's update-state correction), `69b4651` (31-workflow UAT draft).
- This handoff and the lifecycle refinements are in the subsequent documentation
  commit; resolve its exact SHA with `git log -1` rather than guessing it.
- Planning commits are local at this handoff; verify availability before coding.
  A new cloud workspace may not contain them. If missing, obtain this branch/docs
  from the owner/source workspace; do not recreate the design from memory.
- Stable v1.2.22 source: `2320297d5048d627124ff64dd907889e1abccad6`.
  It has separate accepted UAT; that acceptance does not cover this new interface.

## Read first

1. Root `AGENTS.md` and its applicable domain/issue-tracker instructions.
2. [Design](OVERVIEW-NEXT-STEP-DESIGN.md), including sections 9, 10 and 13.
3. [Draft validation/UAT plan](OVERVIEW-NEXT-STEP-UAT-DRAFT.md), all WF01–WF31.
4. [Offline prototype notes](overview-next-step-demo/README.md) and
   [demo](overview-next-step-demo/index.html).
5. [Accepted Recovery clear state](RECOVERY-CLEAR-STATE.md) and the linked ADRs.

## Copy into the new chat to authorize implementation

```text
Begin engineering and DevOps work on the guided “Your next step” Overview for
stormbots/Tactics-Strategy-Dev-Environments. Use the existing planning branch
codex/overview-next-step-design and docs/OVERVIEW-NEXT-STEP-HANDOFF.md as the
handoff. First verify repository status and that the full planning documents and
prototype exist. Preserve unrelated changes. If the local planning branch/docs
are absent, stop and request their transfer rather than reconstructing them.

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
