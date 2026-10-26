# Safe Operations, Recovery and Support — Phase 1 wireframes

Status: **Approved by the owner; production implementation in progress**.

Open [`index.html`](index.html) to review the complete package, or inspect the
individual rendered boards:

1. [`overview-board.png`](overview-board.png) — Overview and maintenance health
2. [`preflight-board.png`](preflight-board.png) — progressive preflight
3. [`recovery-board.png`](recovery-board.png) — interrupted-operation recovery
4. [`report-board.png`](report-board.png) — support-report preparation and preview
5. [`responsive-board.png`](responsive-board.png) — compact layout and state flows

This package records the directed-Q&A decisions for milestone 3 and translates
them into proposed screens, words and transitions. It is a static design
artifact. It does not modify the application, native commands, platform scripts,
coordination state or release behavior.

## Approval boundary

Approval covers:

- the reuse of the existing Overview Development Environment card;
- a prominent primary readiness heading, visually stronger than the secondary
  maintenance-health reason;
- progressive Install/Update preflight;
- the temporary Recovery destination and its evidence-first flow;
- the self-contained HTML support report and exact-content preview;
- the state taxonomy, primary wording, actions and transitions below; and
- compact, theme, zoom, keyboard and screen-reader behavior described here.

Implementation can refine spacing, wrapping and platform-native save-dialog
details without changing the approved behavior. A changed user decision, new
action, or changed safety boundary returns to design review.

## State matrix

### Overview card

| Readiness | Maintenance | Card | Primary heading | Secondary line | Action |
|---|---|---|---|---|---|
| Passed | Healthy | Green | Ready! | Maintenance is current | None |
| Passed | Latest run failed | Yellow | Ready! | Maintenance failed + observed time | Open maintenance logs |
| Passed | Missing or disabled | Yellow | Ready! | Maintenance missing/disabled | View schedule |
| Passed | Overdue | Yellow | Ready! | No success in previous 14 days | Review managed-tool updates |
| Passed | Running | Yellow | Ready! | Maintenance is running | View status |
| Passed | History unavailable | Yellow | Ready! | Maintenance history unavailable | Refresh |
| Failed | Any | Red | Needs attention | Readiness failure first; maintenance remains distinct | View validation results |

The 14-day grace period for a new schedule remains part of the milestone
contract. If schedule age or successful-run history cannot be established, SDE
reports unavailable history instead of asserting overdue status.

### Preflight

| Result | Presentation | Continue? |
|---|---|---|
| All passed | Compact summary with optional detail | Yes |
| Warning | Expanded result and review | Yes; confirmation when applicable |
| Unavailable | Expanded result, reason, log evidence and checkbox | Yes, for one operation attempt only |
| Known unsafe/impossible condition | Expanded blocking result | No bypass |
| Preflight itself fails to return a valid result | Unavailable—not passed | Yes only through the same explicit unavailable-result confirmation |

Refreshing, cancelling, restarting SDE, changing an input or beginning another
attempt invalidates an unavailable-result acknowledgment. Race-sensitive native
conditions are checked again immediately before changes. Repair remains outside
the new Phase 1 preflight scope.

### Recovery

1. On launch, determine whether the recorded backend is still running.
2. If it is active, show active status and prevent conflicting work.
3. If it is no longer active and completion is not established, mark the
   operation interrupted and expose Recovery in navigation.
4. Offer read-only validation first.
5. A passing fresh validation resolves the incident automatically. It proves
   current readiness, not completion of the interrupted operation.
6. Offer Repair only if fresh validation recommends it and existing native
   safety gates permit it.
7. Route package-manager, coordination or other unsafe uncertainty to mentor
   guidance, logs and support-report export.
8. Explicit acknowledgment fully dismisses the incident UI without asserting
   recovery. It first confirms that dismissal does not establish success.
   Normal retained logs remain available.

SDE never automatically resumes, repeats or terminates package work, deletes
locks, forces package-database repair, or treats acknowledgment as success.

### Support report

- Entry points: Validation results, operation failure and Recovery only.
- Output: one bounded, escaped, script-free HTML file.
- Preview: every final section and redacted value in the normal app UI.
- Default content: workstation/SDE facts, exact device name, latest available
  validation, relevant operation outcome and maintenance status/history.
- Diagnostic logs: excluded by default; the user can deliberately include
  bounded sanitized logs.
- Redaction: credentials, tokens, passwords, credential-bearing URLs,
  usernames and personal home paths. Omitted or unsafe data is identified.
- Transport: local user-selected save only; no automatic upload or message.

## Refresh policy

Maintenance and operation status refresh on application launch, after relevant
operations and on explicit request. There is no periodic background polling.
Every observation that can become stale includes its collection time.

## Owner UAT boundary

One consolidated candidate receives one compact native UAT cycle on Windows 11
and Linux Mint. The owner reviews real happy paths, one safe attention/blocker
flow, Overview behavior, Recovery navigation, report export and representative
accessibility/appearance. Codex owns the broader exceptional-state matrix through
automated tests and controlled fixtures.

## GitHub routing after approval

- Put shared sequencing and milestone exit criteria in milestone 3.
- Put preflight requirements and evidence in #7.
- Put operation-state/recovery requirements and evidence in #8.
- Put report format/privacy requirements and evidence in #9.
- Put Overview maintenance-health requirements and evidence in #10.
- Production implementation began after approval was recorded.
