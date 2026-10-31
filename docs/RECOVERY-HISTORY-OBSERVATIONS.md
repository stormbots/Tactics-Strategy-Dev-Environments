# Read-only report acknowledgment observations

Branch: `codex/recovery-history-observations`.
Accepted at `0a678c08a590ded2df3ac3e2cbb2788cb5f09070` in full successful
[Build 41210917994](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41210917994):
Windows trust 92/92, root Linux 107/107 and all inherited native gates passed.
The [user-journal lifecycle increment](RECOVERY-USER-JOURNAL-LIFECYCLE.md) follows;
pending-CI language below records this task's original checkpoint.
Base: #129 at `2d4da242b9f133d9ac42115c34fbdd84bb25a5df`, accepted in
[Build 41153070913](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41153070913).
Windows trust passed 84/84; root Linux passed 99/99, including eight per-user
acknowledgment tests on each platform. Both native jobs, general checks, actual
Mint 22.3 and Windows SYSTEM signed upgrades and inherited recovery gates passed.
The prior worktree-concurrency concern is cleared; no independent writer was
identified and the worktree was clean before this bounded task.

## Bounded T7 acceptance criteria

1. Add a fixed local-main command `read_recovery_report_details(reportId)`.
   Load and validate the selected committed per-account report, redact again,
   render fresh passive HTML, and separately return a typed acknowledgment
   observation with source, observation time and acknowledged time if established.
   No caller path, raw retained evidence, generation digest, command or HTML input.
   Preserve existing report-list/read/delete contracts and publication format.
2. Status is `observed`, `unknown` or `unavailable`, never a negative claim derived
   from missing evidence. Every response says continuation is `not_recorded`.
   No acknowledgment snapshot proves completion, package inactivity, private
   machine binding verification or permission to execute. A failed read or
   impossible timestamp is unavailable, not unacknowledged or repaired.
3. For machine-source reports, use only the existing sanitized public current
   acknowledgment observation and match the report's incident UUID. A different
   current incident or absent snapshot leaves historical status unknown. Do not
   open private machine archives from the GUI, invent historical acknowledgment,
   persist a UI cache as authority or create a machine-public history layout here.
4. For user-source reports, inspect only this account's retained decision tree.
   Require an explicit matching saved-report UUID in the receipt, incident and
   directory-generation agreement, valid acknowledgment time, preserved-byte hash
   and original source context equal to this report's context. UUID/context alone
   cannot associate a report with a recreated identical source object. A decision
   linked to another report is not an acknowledgment observation for this one.
5. User lookup does not require the current operation journal: a later operation
   can legitimately replace it while the earlier report/receipt remains. Observing
   the earlier receipt must not acknowledge the replacement. Retained-copy parsing
   is separate from current native identity capture and cannot construct an
   execution or journal-retirement capability.
6. Observation uses bounded strict private-file reads, validates ancestors and
   never creates/recreates directories. A read-only directory validator is shared
   with the existing store to avoid creating a directory that disappeared during
   inspection. Generation traversal is bounded at 128 entries per selected
   incident; excess returns unavailable, without deleting/purging any data or
   claiming a false negative. No report deletion changes minimum decision state.

## Verification and limits

Eight new tests execute locally without root: four source/status-policy tests,
three retained-store tests and a report-store read-only-open regression. They cover scope/ID/report binding, absent old schema,
unreadable/impossible observations, retained report association after identical
current-journal replacement, preserved-byte corruption, absent-state no-creation,
and bounded traversal without purge. The replacement remains unacknowledged.
The exact policy/store sources run in native Tauri and both coordinator trust jobs.

Affected regressions also passed locally: all eleven user-store tests, four
context tests and nine report-store tests. Linux and Windows-GNU coordinator
clippy, 26 backend contracts, four command/module wiring tests and formatting/diff
checks passed. Native Tauri compilation, Windows runtime/private file behavior,
root-required coordinator and all inherited signed-upgrade/Mint 22.3 gates remain
pending CI. No frontend change or new end-to-end IPC/UAT proof is claimed.

This is report-linked observation, not a complete all-incident timeline. Reports
without an explicit user receipt link (manual capture, save failure, an additional
report from an idempotent acknowledgment) remain unknown, even when some matching
incident decision exists. A corrupt receipt within the same incident can make
lookup unavailable. Machine historical public disposition, standalone retained
history after report deletion, and scalable indexed/paged decision lookup remain
future integration if needed for the final history UI; no private cross-account
evidence is exposed as a shortcut. The current 128-entry bound is an observation
limit, never a retention policy or a blocker imposed on native mutation execution.

## Durable continuation

On completed CI, verify exact head and final results once; fix evidenced defects
without weakening gates, then continue safe user-journal lifecycle integration
and final T7/T8 history/Recovery interaction. Before UI use, replace legacy
dismissal/overwrite behavior with evidence-preserving decisions, maintain distinct
machine/user IDs, and ensure unknown activity never becomes inactive. Final
pending-action resume must retain ordinary preflight, confirmation and OS
authorization; startup/cancellation must not automatically replay a mutation.

No frontend caller is added in this checkpoint. The PR comment records source
SHA, initial Build run and outstanding native validation. No scheduler, partial
stack merge, signing, publication, release or owner UAT. Owner Windows interruption
evidence and Mint v1.2.18 Install/Validate 35/0/0 remain intact.
