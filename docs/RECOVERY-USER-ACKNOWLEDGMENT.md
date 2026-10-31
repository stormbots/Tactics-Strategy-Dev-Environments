# Evidence-preserving acknowledgment for this account's incident

Branch: `codex/recovery-user-acknowledgment`.
Base: accepted #128 at `36a23adcce4aeec74baea32beb84fcfa3b28f287`,
[Build 41143508845](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41143508845).
Windows trust passed 76/76; root Linux passed 91/91. User/report context and native
Validation timestamp tests passed, as did general checks, both trust/native jobs,
actual Mint 22.3 and Windows signed SYSTEM upgrades and inherited recovery gates.

## Bounded T7 acceptance criteria

Add a separate per-account decision store and native single-action controller.
This does not change protected machine coordination or grant execution authority.
The recovery stack remains draft/unmerged and is not yet an owner UAT candidate.

1. `acknowledge_user_recovery_incident` accepts the displayed canonical user ID,
   explicit confirmation and optional bounded Validation snapshot. It holds the
   existing per-application Busy guard and runs off the UI thread. It captures
   the exact original user evidence and a matching sanitized summary, attempts
   one automatic save, then preserves evidence before recording the decision.
   No file chooser, separate save click, extra elevation or automatic operation.
2. A report-save failure warns but does not waive preservation. Original-source,
   evidence-publication or acknowledgment failures leave the decision unconfirmed;
   keep any successfully saved report reference and a fixed actionable error.
   Do not infer absence from a failed write/flush. Check Again after interruption
   or an unconfirmed result, rather than replaying a mutation automatically.
3. New `recovery-state/<incident UUID>/<native generation digest>/evidence.json`
   retains exact original user-journal bytes privately. `acknowledged.json` is
   published second and binds schema, generation, preserved-byte hash, incident, actual acknowledgment
   time and optional report UUID. Native file identity plus bytes, not UUID/hash
   alone, distinguish a recreated identical record. No generation, raw bytes or
   source log path enters the returned decision or shareable report.
4. Never modify, chmod, unlink or retire `operation-journal.json` in this flow.
   Keep its opened handle through capture/preservation. Recheck the current path
   before and after commit; changed data/generation rejects confirmation. Windows
   denies source writer/delete sharing while held; Unix rechecks native identity
   and bytes. A decision for old evidence never acknowledges replacement evidence.
5. Stage exclusive private records, flush files, then publish without replacement
   (`renameat2(RENAME_NOREPLACE)` on Linux; `MoveFileExW` without replacement on
   Windows). Verify evidence before acknowledgment. Partial stages remain private
   and do not count as consent; replay verifies committed records and completes
   missing steps without overwriting them. First committed time/report reference
   wins. Unix flushes the directory chain; Windows flushes files and uses write-
   through rename. This is not a universal filesystem/power-loss guarantee.
6. Use the accepted per-user private-file primitives: bounded reads, strict
   records, regular single-link files, no linked ancestors/reparse points, Unix
   effective ownership and 0700/0600 state. Windows uses normal AppData inheritance;
   full ACL privacy and unelevated end-to-end Tauri IPC remain validation limits,
   not guarantees established by an administrator runner's unit tests.
7. `inspect_user_recovery_acknowledgment` takes only the current user incident ID
   and returns a sanitized matching decision, absent decision, or explicit error.
   Normal absent-state inspection does not create a state tree. A corrupt receipt,
   missing/changed evidence, links or impossible receipt time fail closed. This
   per-account observation is not a machine acknowledgment or cached mutation permit.
8. Keep minimum identity/evidence/decision separately from `recovery-reports`.
   Selected report deletion cannot reset acknowledgment or erase original evidence.
   No purge, delete-state command, other-account log access or machine write API.

## Verification

Eight tests executed at local UID 1000: original bytes/mtime and sanitized decision;
replay after evidence/receipt publication checkpoints; report failure versus required
preservation failure; identical recreated generation; corrupt/missing/linked/future-
dated records; genuine report deletion retaining minimum state; no-replace atomic
publication; Unix source change during the report attempt. Windows runs a live-
writer rejection test instead of the Unix source-change test, keeping eight tests.

The exact source also runs in both coordinator native trust suites and native
Tauri. Context/store regression tests (4/8 locally), Linux and Windows-GNU static
analysis, 25 backend contracts, four command/module wiring tests, formatting
and diff checks passed. Full native Tauri compilation, Windows file-sharing and
publication execution, root Linux and inherited signed-upgrade/recovery gates are
pending CI. No frontend change means unchanged frontend tests were not rerun and
claimed as new evidence. No real reboot, process-termination or power-loss test is
implied by injected publication-boundary errors.

## Remaining integration / durable continuation

No frontend caller uses the new commands yet. The existing legacy user-dismissal
path and `Active::begin` overwrite behavior are unchanged in this bounded step;
they must be replaced/reconciled with preserved evidence and separate decisions
before production UI use. Do not claim that the legacy frontend now preserves
history, suppresses prompts or safely resumes. The source's old `acknowledged`
field remains unchanged; final observations must read this separate disposition,
not delete the source or treat a successful Validation as acknowledgment.

Next: retained machine/user/report history and honest status cross-reference,
safe user-journal lifecycle integration, then final T8 tri-state admission and
single-action/resume/history UI. Preserve independent IDs when both user and
machine incidents exist. A user decision cannot clear a protected transaction;
the normal native mutation path still checks authorization, source signatures,
fresh activity/health, incident binding, evidence retirement and real package
locks. Unknown/active activity is not dismissed by this record. Never replay a
pending mutation after restart or OS-approval cancellation.

The PR checkpoint records exact source, initial CI URL, local evidence and native
acceptance criteria. On completed jobs, verify exact head once and continue if
accepted; diagnose actual failures instead of waiving gates. No scheduler or
partial-stack merge. No signing, release, publication, UAT, fleet rollout or
milestone closure. Owner Windows evidence/journal and Mint v1.2.18 35/0/0 stay intact.
