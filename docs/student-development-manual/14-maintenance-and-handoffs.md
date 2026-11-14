# 14. Maintain software and leave a handoff

**Goal:** Help the next person continue with accurate evidence.

Release work continues after publication. Users may report new problems. Dependencies may need updates. A change in one operating system can reveal a new compatibility issue.

Turn each new finding into a clear issue. Record what the report proves and what remains uncertain. Keep the earlier release record so someone can understand which version had which behavior.

## Current health and maintenance are different questions

A working tool does not prove its scheduled maintenance is enabled. A successful earlier maintenance run does not prove today's tool checks pass. An extra Python installation does not establish that the required interpreter is missing.

These distinctions matter when designing messages. Each finding needs its own evidence and useful next action. A general plan can connect findings without mixing their causes.

## Preserve the original evidence

SDE retains interrupted-operation records for a reason. Acknowledging an interruption records a decision; fresh native safety checks still govern another change. A normal restart does not automatically certify package health or grant permission to proceed.

A rollback means returning to an earlier version. It can affect data, compatibility and update policy. Use the project's reviewed recovery path rather than assuming any older installer is an approved remedy.

## Leave a durable checkpoint

A checkpoint lets another person continue without reconstructing a long chat.

| Field | Useful content |
| --- | --- |
| Completed work | What changed and where. |
| Code identity | Branch, exact commit and PR. |
| Evidence | Commands, run links and results. |
| Limits | What did not run or what the result does not establish. |
| Pending work | Jobs, owner evidence or approvals still needed. |
| Next action | One concrete continuation step. |

For example: “The focused local tests passed. Windows and Mint CI are still running at this commit. Review their final results before merge. Owner UAT has not started.” That is more useful than “Waiting” or “Should be fine.”

SDE keeps checkpoints in repository documents and GitHub issue/PR comments. Useful historical evidence stays available, even when a later correction becomes the current implementation.

## Practice

Write a handoff for your practice document. Include the commit, review result, unresolved wording and the next person's action. Give it to a classmate and ask whether they can continue without asking what you meant.

## Check your understanding

- Why does the next person need both a result and its limits?
- What should remain recorded when a later version fixes a problem?

[Next: complete the workbook](workbook.md)
