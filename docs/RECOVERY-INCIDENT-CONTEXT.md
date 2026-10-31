# Recovery incident provenance and Validation collection time

Branch: `codex/recovery-incident-context`.
Accepted at `36a23adcce4aeec74baea32beb84fcfa3b28f287` in full successful
[Build 41143508845](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41143508845).
Windows trust 76/76, root Linux 91/91, native timestamp tests and inherited gates
passed. The subsequent [user-acknowledgment increment](RECOVERY-USER-ACKNOWLEDGMENT.md)
continues T7. Pending-CI language below records this context increment's original handoff.
Base: accepted #127 at `996ec223261d15605cf12a6f3c281b5eb3a06825`,
[Build 41139930489](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41139930489).
Windows trust passed 72/72; root-required Linux passed 86/86. Both protected
controller tests, portable controller tests, native builds, feasibility,
bootstrap/manual/read-only recovery, application/scheduled-tool recovery and
Windows SYSTEM/actual Mint 22.3 signed upgrades passed. The stack is unmerged.

## Bounded T7 acceptance criteria

- Automatic-summary capture can explicitly select `machine` or `user` evidence.
  The optional selector defaults to machine for the existing backend API. It is
  an enum, not a path, executable, override or permission. No new command grant.
  The machine acknowledgment controller remains hard-wired to machine evidence;
  selecting user report capture cannot submit machine consent or clear a journal.
- Machine context exposes only the current public incident UUID. The original
  private operation/stage/time/completion are unavailable, not reconstructed from
  report capture or a potentially unrelated account journal. User context reads
  only this account's fixed `operation-journal.json`, requiring the displayed
  canonical ID and valid original operation, stage and timestamps. Keep original
  start/last-observed times distinct from report capture and safety observations.
  Do not infer that a recorded stage proves completion or package inactivity.
- The report omits the source log path and raw journal bytes. Parsing is bounded
  at 16 KiB including a bounded read after opening; reject unsupported schema,
  unknown fields, stale/missing IDs, invalid/impossible times, acknowledged records,
  links/reparse points, hardlinks and unexpected types. Unix requires current
  effective ownership and no group/other write; legacy 0644 journals remain
  readable without chmod. Reject linked ancestors. Windows validates the opened
  handle and denies concurrent writer/delete sharing. This is per-user diagnostic
  input, not a privileged trust/authorization boundary or a new Windows ACL proof.
- Capture never writes, chmods, removes, archives or acknowledges the source
  journal. Missing/unreadable/malformed evidence fails explicitly without making
  up provenance or falling back to another source. Report saving still uses the
  accepted fixed per-user store, redaction, publication and retention behavior.
- Schema-1 summaries gain optional typed `context`; absent context remains
  readable and is honestly labeled unavailable in older reports. Context identity
  must match the summary's incident ID. Render fresh passive HTML with explicit
  source and evidence limits; never interpret this context as an execution permit.

## Actual Validation timestamps

Native operation results now include `validation_collected_at`: the Unix seconds
at which the last valid structured Validation check was collected from output.
Partial/failed checks count as collected; success/summary/progress events alone
do not. An unavailable clock leaves the time unavailable, not a previous fake
time. This is output-collection time, not a claim about the exact instant each
underlying package probe ran.

Frontend state retains that native timestamp with the corresponding final check
snapshot, including failure results; a new run resets it. Absent/invalid legacy
timestamps and streamed checks before a final result remain unavailable. Browser
preview data does not acquire a real native-validation timestamp. Support report
generation and reopening no longer stamp old checks with the current time; this
fixes the previous `new Date()` substitution. PASS/FAIL and timestamp collection
do not acknowledge or change operation admission. Recovery's final controller/UI
must reuse the same snapshot/time, not introduce a separate fabricated clock.

## Evidence and remaining work

Four user-context tests and eight report-store tests executed locally at UID 1000.
They cover original provenance and bytes/mtime preservation, stale/malformed/
oversized/impossible evidence, link/permission rejection, report context roundtrip,
old-report compatibility and existing storage safeguards. Windows runs three
context/seven store tests because two tests are Unix-only. Exact sources compile
in both native coordinator trust jobs, as well as native Tauri.

Local Linux/Windows-GNU coordinator clippy, 24 backend contracts, three command
permission tests, 138 frontend tests, production frontend build, formatting and
diff checks passed. The new native protocol-timestamp unit test and full Tauri
integration compilation require CI. Native execution, actual Windows file-sharing
behavior and every inherited Mint 22.3/Windows signed-upgrade gate remain required;
portable harness results do not substitute for those gates or owner UAT.

This is capture/provenance, not user-only acknowledgment/resume. Reports explicitly
select one source; simultaneous machine/user incidents are not silently joined
or assumed to describe the same operation. Final UX must preserve those separate
identities and handle both before continuing. No protected private bytes or other
account's logs are exposed. Later protected acknowledgment/continuation status,
retained history observation, user-only evidence-preserving acknowledgment, safe
history viewing/deletion and final tri-state Recovery admission/resume remain.

On completed CI, verify exact head/results, fix evidenced defects or transient
failures, then continue T7 retained history/status and user-only acknowledgment
integration before final T8 UI. Leave a durable PR checkpoint if only CI remains.
No polling scheduler, partial-stack merge, signing, release or UAT action. Owner
Windows interruption evidence and Mint v1.2.18 Install/Validate 35/0/0 remain intact.
