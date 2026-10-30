# Interrupted-operation recovery: self-service implementation plan

Status: engineering approved; native permission feasibility and production
storage foundation, durable acknowledgment and lease-bound safe transition passed;
normally privileged bootstrap and privileged GUI helper supervision passed;
T4 scheduled-tool, Linux manual, Windows direct maintenance/Install/Repair and
package-hook parent boundary passed native validation. The backend execution-parity
review and T5 application-updater backend integration passed native CI. Current
T6 read-only diagnosis/self-service guidance passed CI. The current bounded T7
per-user report storage foundation is pending CI; report/acknowledgment/history
integration and final frontend safety-observation/resume work remain.
See [current engineering status](RECOVERY-ENGINEERING-STATUS.md).
Prepared October 28, 2026. Source inspected: main commit
`3b0e8d7ec05d1b6d62535cb5b1368056abe3ac04`, including #109–#112.

This plan records the 15-question design interview. The owner subsequently waived
the prototype: there is no wireframe, mockup, or prototype approval phase.
The owner authorized engineering after plan review. Codex owns application engineering and
targeted tests. The owner subsequently delegated DevOps to Codex as well: existing
workflows remain authoritative for native verification and packaging, without
requiring the owner to relay work between chats. The hourly automation was canceled;
active Cloud sessions leave durable checkpoints when long CI jobs remain pending.
The owner performs focused UAT after the consolidated candidate is ready.

## 1. Goal and finish line

Replace the blanket mentor-clearance requirement with an information-sharing,
evidence-preserving, self-service recovery experience. Restore access to changes
as quickly as safety observations permit. No recovery instruction in this scope
may require a mentor to service the laptop.

Finish when the application implements the policy below, targeted tests pass,
the CI workflow validates the exact integrated source on supported platforms,
and the owner accepts the focused UAT results. Implementation completion,
successful CI, release signing, publication, and owner acceptance are separate
states. None implies milestone closure or stable promotion.

Preserve the existing Windows interruption evidence. Preserve Mint v1.2.18
Install/Validate acceptance: 35 passed, 0 warnings, 0 failed. Do not manufacture
crashes, package corruption, or lock contention on either owner workstation.

## 2. Approved decisions

| Interview | Decision |
| --- | --- |
| 1 | Acknowledgment replaces blanket mentor clearance, not execution safety checks. |
| 2 | Unknown activity blocks changes until a fresh check can establish inactivity. |
| 3–5 | One acknowledgment action automatically attempts to save a summary report. No save dialog or separate click. Save failure warns but does not block if original evidence remains preserved. |
| 4 | Summary includes interruption evidence, current safety findings, available validation, SDE/OS identity; detailed logs are optional. Never export transaction tokens. |
| 6 | Acknowledgment persists for that particular incident across restart and scheduled maintenance. A new incident requires acknowledgment. |
| 7 | After acknowledgment, remove its Overview message. Current checks determine readiness and card color. Keep history. |
| 8 | Known incomplete package state blocks changes and receives specific self-service instructions, not an automatic repair or generic mentor referral. |
| 9 | Unknown package health alone warns rather than blocks, once activity is established as inactive. Native package safeguards remain enforced. |
| 10 | Check Again refreshes findings; every attempted change rechecks. No recurring background polling. |
| 11 | Any SDE user can acknowledge without an additional administrator prompt. Actual privileged changes retain normal OS authorization. |
| 12 | Persistently unavailable activity detection gets save-work, restart, and recheck guidance. Restart does not certify health or clear evidence. |
| 13 | Resume the originally requested action after acknowledgment and fresh checks, retaining ordinary confirmations and privilege prompts. |
| 14 | Reuse Recovery for current incidents and history; no new top-level destination or status card. |
| 15 | Retain history and reports until explicit user deletion. Deletion is not acknowledgment and cannot authorize changes. |

Students have administrator/sudo-level access and should be self-servicing. That
product assumption does not mean processes are always elevated, or justify
changing permissions on protected state.

## 3. Current behavior and affected sources

There are three distinct mechanisms:

1. A machine-wide protected transaction journal records uncertain privileged work.
2. Handle-owned operation/session gates coordinate participating processes.
3. A per-user GUI operation journal records operation, stage, time, and log path.

| Surface | Current behavior and source |
| --- | --- |
| Windows backend | `windows/chocolatey/tools/Coordination.ps1` creates private `C:\ProgramData\SkyviewRoboticsCoordination\transaction.json` before mutation; normal completion removes it. Exceptions/crashes can retain it. Nested privileged work uses a private token and supervising gate. Read-only validators retain the journal and warn. |
| Linux backend | `linux/lib/coordination.py` creates root-owned `/var/lib/skyview-robotics-coordination/transaction.json`, flushes it, supervises children with inherited leases, and removes it on an ordinary exit, including a nonzero exit. Signal/supervisor failure can retain it. Validation currently uses a mode that rejects the journal. |
| Shared coordinator | `coordination/src/lib.rs`, `windows.rs`, and `main.rs` enforce trusted paths, operation/session leases, interruption detection, and application-installation transactions. Journal presence blocks new mutations/installations. |
| Native SDE updater | `updater/src/linux_install.rs` and `windows_install.rs` acquire installation leases, create their own protected intent, wait for native completion, and retain uncertain transactions. Linux also checks package locks/audit. Native identity, signature, policy, and postchecks are separate controls. |
| GUI journal | `installer/src-tauri/src/journal.rs` persists `operation-journal.json`; current acknowledgment deletes that user record. Activity errors currently collapse to false in inspection, which does not meet the new policy. |
| Recovery and readiness | `installer/src/App.tsx`, `safeOperations.ts`, `model.ts`, and `DetailsPages.tsx` route incidents, disable operations, show updater coordination, and sometimes treat successful Validation as resolution. #111 adds machine-only Recovery visibility but intentionally retains the mentor gate. |
| Preflight and scripts | `installer/src-tauri/src/preflight.rs`, `linux/lib/update_preflight.py`, Windows preflight, and backend script entry points perform partially separate checks. Repair must not become an unchecked alternative. |
| Reports | `installer/src/supportReport.ts` and `installer/src-tauri/src/support.rs` compose a report from available user incident, validation, maintenance, and an optional recent sanitized application log. Machine-only context and automatic report saving need additional support. |

An existing journal is evidence of an uncertain outcome, not proof of failure or
of an active process. An available SDE gate is not proof that detached package
children stopped. Validation checks installed capabilities, not transaction
completion. These distinctions must survive in the API, UI, reports, and tests.

## 4. Scope and non-goals

Include Windows 11 and supported Mint, manual Install/Repair/Update, read-only
Validation, installed script entry points, scheduled maintenance, and SDE's own
updater. Include the narrow diagnostic, report, history, and package guidance
changes needed to make these entry points agree.

Do not build a general remote-support service, automatic package repair engine,
new release pipeline, or new privileged background service by default. Do not
rewrite unrelated mentor references outside the recovery paths being changed.
Do not automatically upload diagnostics, force a restart, kill installers,
remove native package locks, loosen ACLs, disable signature checks, or interpret
report/journal content as commands. No automatic retry of an uncertain mutation.

Version selection, signing, publication, stable promotion, fleet rollout, and
milestone closure belong to separate release/owner decisions. Do not assume
v1.2.19 is still unused; never overwrite a published candidate.

## 5. State and safety contract

Represent activity as `active`, `inactive`, or `unknown`, with reason and
observation time. Represent package health independently as `healthy`,
`incomplete`, or `unknown`. Represent coordination trust independently. Do not
encode these conditions as a single boolean or infer them from Validation.

| Finding | Changes | Available next action |
| --- | --- | --- |
| Active SDE gate or relevant package operation | Block/defer | Explain activity; Check Again; diagnostics. Do not terminate it. |
| Activity unknown, inspection denied, timeout, or incomplete coverage | Block/defer | Explain the failed check; Check Again; save-work/restart/recheck instructions. |
| Known incomplete package configuration | Block | Explain evidence and platform-specific recovery steps; Check Again. |
| Untrusted coordination state | Block | Explain trust failure and supported self-service remediation; no permission loosening. |
| Activity inactive; package health unknown | Warn, allow | Record uncertainty; retain native checks and ordinary confirmations. |
| Unacknowledged interruption; otherwise safe | Await acknowledgment | Acknowledge and continue. |
| Acknowledged interruption; otherwise safe | Allow | Normal workflow, with a fresh backend check. |

Other existing security/eligibility blockers remain in force: unsupported OS,
invalid candidate/signature, disabled installation policy, insufficient disk,
or failed native identity/postchecks are not overridden by this policy.

Read-only diagnostics, sharing, and history remain accessible. Validation may
wait while work is active or activity cannot be established, but journal presence
alone must not prevent it on either OS. A failed or passed Validation never
creates acknowledgment or silently clears machine evidence.

Scheduled work cannot interactively acknowledge a new incident. It records a
clear deferred reason and retries at its existing next invocation. Previously
acknowledged incidents do not permanently disable it; current safety checks and
any explicit pause setting still apply.

## 6. Architecture and transaction lifecycle

### 6.1 Separate evidence, acknowledgment, and authority

Use a versioned incident identity that binds acknowledgment to one exact journal
generation. New records should have a unique generation ID. Legacy records
without IDs need a stable identity derived by trusted code; a PID, timestamp
alone, file presence, or the Windows nesting token is not a sufficient public ID.

Retain original protected bytes and provenance privately. Expose only sanitized
facts and an opaque incident identity. Never expose private transaction tokens
to JavaScript, reports, history, or the acknowledgment payload.

Acknowledgment is a user decision, not a privileged execution capability. Use a
strict, bounded payload naming an observed incident, not caller-controlled paths,
commands, package names, or executable arguments. Any user's acknowledgment may
apply machine-wide, as explicitly selected by the owner; do not require the
original initiating account. The executing backend independently matches the
current incident and rechecks safety.

### 6.2 Prompt-free acknowledgment feasibility checkpoint

Protected Windows journals are private to administrators/SYSTEM; sudo-level
Linux access also does not make the GUI root. An unelevated GUI cannot simply
write a protected acknowledgment or read a private legacy journal without some
existing supported mechanism. Do not conceal an extra elevation prompt here.

Preferred implementation direction: a bounded, non-authoritative acknowledgment
intent recorded without elevation, bound to a sanitized incident identity; an
existing normally privileged operation/maintenance entry point validates and
reconciles it under its operation lease. This is not a general skip flag. Define
fixed storage, ownership, no-follow/reparse defenses, strict parsing, and request
consumption rules before coding privileged consumption. Machine-wide scheduled
consumers must discover the decision without trusting arbitrary profile paths.

Before implementing this direction, prove how a fresh install and an existing
private legacy transaction obtain a stable public identity without a new prompt,
and how the installation/upgrade path can deploy it while preserving evidence.
If existing mechanisms cannot meet that contract, document the exact limitation
and request a narrowly scoped architecture decision. Do not silently add a
service, weaken storage permissions, substitute an unverifiable ID, or ship a
UI-only acknowledgment that the scheduler cannot honor. This is a technical
feasibility gate, not permission to revisit the approved product policy casually.

### 6.3 Reconcile under a lease; preserve before replacing

At execution time acquire the trusted operation/installation lease, verify the
incident generation and applicable acknowledgment, and establish inactivity and
package status again. Retain the lease through the corresponding transaction.
Native package managers still acquire and enforce their own locks. Process
checks narrow uncertainty but cannot make unrelated software cooperate with SDE.

Before opening a new transaction, durably archive the prior protected evidence
and its identity without overwriting another incident. Make archive, acknowledgment
reconciliation, and new transaction creation crash-consistent. A crash between
any steps must recover to a recognized state, not lose evidence, suppress a new
incident, or accidentally authorize the next operation. If original evidence
cannot be preserved, do not replace it or start a mutation.

A report-save failure is nonblocking; evidence-preservation failure is not.
These must be distinct results. Preserve the existing normal completion rules
unless a narrowly reviewed change is necessary for this lifecycle.

### 6.4 Activity checks and package guidance

Combine SDE leases with relevant native process/lock observations and available
supervisor/child identity. PID reuse must not make an old record look active or
inactive incorrectly; use process creation identity where available. Denied
access, truncated enumeration, missing required tools, and timeout are unknown,
not negative findings. Define supported detection coverage per platform and
test detached-child cases rather than promising detection of every installer.

Separate a failed package-health query from positively identified damage.
Update the updater's current fail-closed audit handling only where needed to
implement the approved unknown-health warning policy; never classify active
package locks as merely unknown health.

Build a small reviewed guidance catalog for recognized conditions. Each entry
provides what was found, the exact supported next step, normal privilege needs,
and how to verify resolution. Use fixed instructions, not journal-supplied shell
text. Prefer vendor-supported repair/restart actions; unknown conditions receive
honest diagnostics and supported next steps, not invented universal repair
commands. No force flags, lock deletion, process killing, or mentor prerequisites.

## 7. User interaction and diagnostic report

Recovery shows a concise explanation, known/unknown findings, actionable blockers,
Check Again, Validation when safe, and existing log/report access. Keep the
prominent primary action consistent with the current button hierarchy and themes.

When eligible, one **Acknowledge and continue** action:

1. Captures the displayed incident ID and the pending requested operation.
2. Attempts automatic summary generation and local save; no file chooser or
   mandatory report preview. Detailed logs remain off unless the user opts in.
3. Durably records acknowledgment for that incident and reports any save failure.
4. Rechecks safety through the execution path. Changed incidents require fresh
   acknowledgment; new blockers stop continuation with actionable findings.
5. Resumes the pending operation through normal confirmation/OS approval. An
   acknowledgment is not an extra confirmation to provision packages silently.

If Recovery opened at startup with no pending request, acknowledge and return to
Overview without initiating a change. Do not automatically replay a pending
mutation after app restart or OS-approval cancellation. Disable duplicate clicks;
retain the decision and allow an explicit retry if execution was cancelled.

The summary includes schema/report ID, capture time, incident identity and
available provenance, application/OS versions, safety findings and timestamps,
available Validation results with their actual collection time, missing evidence,
and acknowledgment/report status. Do not fabricate a stage or label a newly
captured old Validation result as freshly run. Include device identity consistent
with existing reports; flag that even summaries may contain identifying data.

Save automatically in an application-managed per-user reports directory using
unique filenames and atomic writes. Show the saved report in Recovery history
with Open/report-folder and optional shareable copy/export actions. Sharing is
user initiated: no upload, recipient, or external service is configured by default.
Reports open safely escaped, with no active scripts or embedded private tokens.
No report content is consumed as execution authority.

Keep Recovery accessible when retained history exists. No new Overview card or
navigation destination. After acknowledgment, suppress that incident's Overview
warning without masking a current safety blocker or unrelated failed check.
Do not call an uncertain earlier operation completed, repaired, or successful.

Retain history and reports until explicit deletion, with no age/count purge.
Provide explicit selection and deletion confirmation. Deleting a report/history
view is separate from deleting minimum operational identity/acknowledgment state;
that minimum state remains as necessary to prevent renewed prompts, accidental
authorization, or loss of an unresolved transaction. Explain this distinction.
No supported history action deletes the current protected transaction. Across
user accounts, show only diagnostics that the viewer is authorized to read;
machine-wide acknowledgment does not grant access to another user's raw logs.

## 8. Bounded implementation tasks

Implement on focused branches from then-current main. Recheck AGENTS.md and
preserve unrelated work. Each task has targeted tests and a reviewable commit;
integrate them into one coherent candidate, not partially functional UAT builds.

| Task | Dependencies / affected areas | Acceptance criteria |
| --- | --- | --- |
| T1: Contract and feasibility | Source map above; coordinator, updater, installed permissions | Record storage/identity/API contract and an architecture decision. Prove legacy prompt-free acknowledgment and safe deployment path on disposable Windows/Linux fixtures. Resolve the feasibility checkpoint before dependent implementation. |
| T2: Explicit safety model | T1; coordinator, preflight adapters, GUI types | Activity, health, trust, and acknowledgment are separate typed observations. Unknown activity never becomes false. One policy table is enforced by all adapters with parity tests. |
| T3: Durable incident lifecycle | T1–T2; Rust coordinator and platform wrappers | Legacy/new incident identity, preserved evidence, persistent acknowledgment, fresh-incident detection, and crash-safe reconciliation work. New transaction cannot overwrite old evidence. |
| T4: Platform execution integration | T2–T3; Windows PowerShell, Linux Python/shell, installed entry points | Manual Install/Repair/Update and scheduled tool maintenance use the same decision contract. Gates and nesting protections remain valid; no environment-variable bypass. |
| T5: SDE updater integration | T2–T4; updater Linux/Windows, observation/Details UI | Application installation honors acknowledged history and current blockers while retaining pause, signatures, package identity, session leases, and postchecks. Unknown-health handling matches policy. |
| T6: Read-only diagnosis and guidance | T2–T4; both validators, guidance, protocol | Both platforms can validate a retained interruption without acknowledgment or mutation when safe. Known package blockers have reviewed self-service steps; restart guidance never promises recovery. |
| T7: Reports and history | T3; Rust support, report schema/rendering, safe file operations | Automatic summary save is atomic and best-effort; optional logs, redaction, machine-only context, actual timestamps, retention, export, and deletion semantics are tested. |
| T8: Recovery interaction | T2–T7; App, safeOperations, DetailsPages, readiness model | Single action resumes the intended flow; no extra acknowledgment elevation, save click, mentor clearance, status card, automatic crash retry, or stale incident suppression. Keyboard/focus, themes, zoom, and compact layout work. |
| T9: Consolidation and engineering review | T1–T8; contract tests, docs | Review full diff and privilege boundary, run affected targeted suites/build, document compatibility and limitations, update UAT guide without overwriting historical results. Commit and supply CI handoff. |
| T10: External validation and owner UAT | Codex through existing CI workflows, then owner | Applicable Windows/Mint native, coordination, fixture, updater and signed-upgrade checks pass on exact source. Deliver one authenticated candidate with a short focused UAT sheet; preserve all previous evidence. |

Order T7/T8 work so that no final user-visible button promises persistence before
the backend contract exists. No prototype is required. Do not stop for routine
implementation preferences; use this plan's defaults. Stop for an actual safety
contract failure, unsupported privilege architecture, or material scope expansion.

## 9. Verification matrix

Run destructive/privileged fixtures only on disposable runners. Never invoke
fixture initialization or cleanup against an owner machine's coordination root.

| Area | Required cases |
| --- | --- |
| Policy | Every row in section 5; independently unavailable activity and health; current trust failure; positively identified damage; stale observations. |
| Concurrency | Live SDE supervisor, inherited child, detached package child, gate released before child exits, PID reuse, process inspection denied, another process starts after UI check, two GUIs acknowledging concurrently. |
| Incident lifecycle | Windows/Linux legacy system and installation records; new IDs; machine-only and user-only incidents; multiple incidents; changed record between display and click; malformed/oversized state; missing metadata. |
| Persistence/crashes | Crash before/after report, acknowledgment, archive and new transaction; disk full; partial write; restart; evidence archive failure; acknowledgment persistence failure. Failure cannot silently authorize execution. |
| Authorization | Non-elevated acknowledgment with no new prompt; normal mutation elevation retained; multi-account machine effect; no cross-user raw-log disclosure; forged paths, symlinks/reparse points, weak ACLs, nesting token misuse, request replay against a new incident. |
| Reporting | Machine-only interruption, missing logs, optional log opt-in, redaction/escaping, actual Validation dates, automatic report failure warning, unique saves, export, explicit deletion, no time/count purge. |
| UI | Eligibility, blocker-specific next step, Check Again, pending operation resume, startup with no pending action, duplicate click, cancellation, report failure, retained history navigation, no acknowledged Overview warning. |
| Validation | Windows and Linux interruption diagnosis; active/unknown activity defers safely; PASS/FAIL does not acknowledge or remove evidence; actual check summary retained. |
| Scheduling | New incident defers; acknowledged incident survives logout/reboot and permits next safe scheduled invocation; pause remains respected; no background retry loop or interactive scheduler prompt. |
| Self-update | Signed Windows/Mint upgrade, blocked activity, unknown health warning, known incomplete state, native nonzero/unknown exit, reboot indication, identity/postcheck failure, subsequent new interruption. Existing trust gates stay enforced. |

Use existing suites and extend them rather than creating a parallel test harness:

- Rust: `coordination/Cargo.toml`, `updater/Cargo.toml`, and installer Tauri tests.
- Python: `tests/test_coordination.py`, `test_update_preflight.py`, and affected
  schedule/runtime/command-permission contracts.
- PowerShell: `tests/Test-CoordinationCI.ps1` and affected native fixture tests.
- Frontend: `App.test.tsx`, `safeOperations.test.ts`, `supportReport.test.ts`,
  `SelfUpdate.test.tsx`, relevant model/guidance tests; production build and
  affected browser/accessibility flows.

Update tests that currently require permanent mentor blocking to require explicit
acknowledgment plus preserved evidence and fresh checks. Do not merely delete
their safety assertions. Maintain required native signed-upgrade and protected
coordination coverage. Existing wrappers' different known-failure cleanup
semantics need regression coverage, not an incidental policy rewrite.

During engineering run only tests relevant to changed code, then broader local
checks once the change is ready. Planning-only edits need document/diff checks,
not application test runs. Full native builds and packaging belong to CI.

## 10. Focused owner UAT

CI must first exercise crash, malformed-state, denied-access, concurrent-child,
report-failure, and deletion tests using fixtures. Do not ask the owner to create
those failures or rerun previously accepted unrelated scenarios.

Provide a single result sheet with Windows / Mint and Pass / Finding / Blocked /
Not run. Prefill historical acceptance separately from new results.

1. Windows: the existing interruption remains available; Recovery explains
   evidence and uncertainty without requiring mentor clearance. Inspect and run
   safe Validation; no private token or fabricated success appears.
2. When checks permit, acknowledge once. Confirm there is no report dialog or
   extra acknowledgment elevation. Verify the automatic report/history entry and
   resumption of the deliberately selected action, with ordinary confirmations.
3. Restart/reopen SDE and confirm the same incident stays acknowledged; Overview
   reflects current readiness without the old interruption warning. History and
   the report remain accessible from Recovery.
4. Mint: preserve the v1.2.18 pass. Check the normal healthy path and the new
   history/report affordances without manufacturing an interruption or reinstalling
   development tools unnecessarily. Use fixture evidence for absent failure cases.
5. Scheduling: accept authoritative automated evidence where manual checking
   would require waiting or changing a working schedule. Owner only reports
   naturally observed scheduling findings.

If real safety checks block the owner's Windows machine, report the precise
finding and supported self-service step. Do not clear evidence or relax detection
to manufacture a UAT pass. UAT cannot guarantee that the historical unknown
operation completed safely.

## 11. Engineering and CI handoffs

Role update: Codex owns both engineering and DevOps. The handoff below is now
an internal durable checkpoint, not a request for the owner to relay prompts
between chats. Continue unblocked work; when only long CI remains, record exact
source/run evidence and end the active Cloud session without continuous polling.

Engineering stops when implementation is committed, targeted verification is
complete, and full external validation is pending. Supply branch, exact SHA,
completed tests, changed contracts, remaining risks, and a copyable CI prompt.
Do not occupy the session polling long jobs or independently manage signing.

CI handoff template (replace placeholders with actual values):

> Validate the interrupted-operation recovery redesign on branch BRANCH at SHA.
> Read docs/INTERRUPTED-OPERATION-RECOVERY-PLAN.md and the implementation handoff.
> Use existing workflows for complete applicable Windows and Mint native,
> protected coordination, fixture, and signed-upgrade validation. Do not waive
> required checks. Diagnose infrastructure failures in CI; return evidenced
> application defects to engineering with exact failing commands/assertions.
> Preserve the owner's Windows interruption evidence and Mint v1.2.18 pass.
> Inspect current candidate/tag state before selecting an unused version; do not
> overwrite published assets or assume 1.2.19 remains available. Follow the
> separately authorized merge/candidate process and stop at human signing approval.
> Report source SHA, workflow URLs, completed/pending checks, and the specific next
> action; if CI is pending, end instead of polling. Do not promote stable, roll out
> to the fleet, close the milestone, or resume paused automation.

Engineering is authorized. T1's initial contract, isolated permission probes, and
native-validation handoff are recorded in
[the engineering status](RECOVERY-ENGINEERING-STATUS.md). This is not a completed
feature or UAT candidate. No release action is authorized by this document alone.

## 12. Risks, compatibility, and fallback

- Prompt-free, machine-wide legacy acknowledgment is the principal architecture
  risk. Resolve T1 with real permissions and installation paths before promising
  the feature; do not assume administrator membership equals elevation.
- Activity inspection is not exhaustive. Document supported coverage; missing
  required coverage is unknown and blocks. Native locks remain the final package
  concurrency control, not something SDE removes.
- Shared Rust, Python, PowerShell, GUI, and updater consumers can drift. Use a
  common versioned contract and parity fixtures. An older consumer must fail
  safely, not interpret a new incident as permission to proceed.
- Mixed-version installations and rollback must be tested. Old versions may
  restore conservative blocking, but must not destroy archives, acknowledgments,
  or active evidence. Do not automatically downgrade an interrupted machine.
- Incomplete package repair varies by cause and OS. The plan provides recognized
  self-service guidance, not a promise that every damaged OS can be repaired by
  SDE. Escalate an implementation limitation with evidence and options, not a
  mentor servicing requirement in the application.
- Indefinite history retention can consume storage and retain personal details.
  Bound individual records/reports, report storage failures, and provide deliberate
  deletion; do not silently purge contrary to the approved retention policy.
- If implementation cannot satisfy a safety invariant, keep the old guard on
  that path and do not ship the incomplete experience as accepted. Report the
  specific gap for owner direction; do not hide it behind a generic success state.
