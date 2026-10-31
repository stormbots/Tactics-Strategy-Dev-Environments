# Selected history-view deletion, separate from operational authority

Branch: `codex/recovery-history-view-deletion`. Bounded T7/T8 increment; native/browser CI pending.
Base #136 `9f0fd91256af72538f98a1aca1708130fb25ad36` accepted in
[Build 41240901801](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41240901801).

## Acceptance criteria

- Offer explicit deletion of an eligible displayed history snapshot, with a separate
  confirmation naming its source, incident and per-account scope. Cancel preserves
  it and restores focus. Duplicate clicks cannot submit multiple native tasks.
- Deleting a view is **not data erasure**: original machine/user journals, private
  archives/evidence, minimum acknowledgment state, saved reports, exported copies,
  current Recovery findings and other accounts remain unaffected. Those minimum
  records are still needed by the existing evidence-verification/transition guard.
  Report-file deletion remains its own previously accepted explicit action.
- Bind the displayed row to a native-only fingerprint and an opaque, in-memory
  view token. The command accepts only that token and confirmation, not a source
  path, incident override, fingerprint or mutation option. Re-read the exact native
  source entry before writing cosmetic state; reject changed/expired views.
- Remember deletion privately under this account's fixed `recovery-history-views`
  directory. Separate source/UUID/fingerprint markers hide only matching history
  snapshots. New/changed snapshots reappear; same UUID across sources does not
  share a marker. Nothing reads these markers as operational acknowledgment.
- Filtering preserves the underlying pagination cursor, counts excluded views and
  never describes a filtered-empty page as absent/cleared evidence. Corrupt or
  unavailable cosmetic preferences leave native rows visible, warn explicitly and
  disable their view deletion; they do not erase diagnostic observations or gate
  application changes. Actual native source failures remain separately unavailable.

## Implementation boundary

`history_views` owns only private cosmetic state and a bounded 512-entry in-memory
token registry. Cache eviction/application restart expires tokens and requires a
fresh view, not new operational consent. Markers are typed, bounded, schema-checked
and published through a synced private staging file and rename. A failed task can
leave a staging file or a committed marker: report an unconfirmed outcome, then
refresh. Idempotent retry does not rewrite matching markers. No recursive cleanup,
archive deletion, gate release or privileged helper is involved.

Machine snapshot fingerprints use sorted known archive filenames plus directory-
enumeration length/creation/modification metadata, never private receipt/journal
contents. Final receipt publication changes the fingerprint from an earlier
partial archive observation. Account fingerprints bind the retained generation,
validated preserved bytes and receipt bytes. Fingerprints are skipped by serde;
only opaque UUID view tokens reach the frontend. Marker files remain private to
the current account and do not expose protected machine bindings or restart keys.

The native command also uses the existing application task guard to avoid local
operation overlap. Fresh lookup validates source identity/fingerprint; a later
source change cannot match an old cosmetic marker. This is not an atomic execution
permit: no protected lease is transferred into a cosmetic write, and admission,
mutation, bootstrap and scheduling never consult this module. Current incident
findings remain visible even if their historical archive view is suppressed.

Ambiguous, overflowed or unavailable account snapshots currently lack a deletable
view token: no fabricated generation is selected to make deletion succeed. Their
diagnostic row stays visible and explicitly unavailable/ambiguous. This limitation
belongs in the remaining completeness review, not an assertion that evidence was
cleared. A matching marker is not an undo mechanism or proof of completion.

## Validation and pending gates

Local: 170 frontend tests, production TypeScript/Vite build, Linux/Windows-GNU
coordinator clippy with warnings denied, 33 backend contracts, four permission
checks and whitespace pass. Six selected Rust test harness cases pass, but one
protected machine fixture returns early without root; five actually executed
locally. Coverage includes stable/source-separated native view binding, restart
token expiry, persistent markers, changed-generation reappearance, staging/commit
failure replay, corrupt-marker rejection, preserved account decisions and new
duplicate-generation visibility. UI coverage includes confirmation/cancel, duplicate
clicks, stale/unconfirmed failure, filtered-page counts/cursor and corrupt preference
visibility. Readiness/mutation source contracts reject cosmetic-state dependencies.

Required CI must execute `history_view_deletion_does_not_clear_machine_journal_receipt_or_gate`
under native root/admin: hiding a machine view must leave the original journal,
private receipt, acknowledgment and legacy blocking gate unchanged. The partial
archive publication test now also asserts a changed fingerprint. All inherited
real standard-user, trust, feasibility, bootstrap/manual/read-only, scheduled/
application recovery and signed SYSTEM/actual Mint 22.3 gates remain mandatory.

Local browsers remain known absent. Existing CI installs Chromium/WebKit and must
pass all browser checks plus four synthetic light/dark 640/1140px deletion
confirmation/cancel/focus/persistence/other-source/axe/reflow cases. Real reboot,
OS authorization dialogs and consolidated workstation behavior remain owner UAT.

## Remaining work

After exact-head acceptance, complete malformed/unavailable-source self-service
and edge-case coverage (including ambiguous/overflow history presentation and
view-deletion eligibility), then audit integrated recovery execution/UX, consolidate
verified changes and prepare the signed focused-UAT candidate. No milestone
completion or owner UAT readiness is claimed from this increment alone.

Owner Windows interruption evidence and Mint v1.2.18 Install/Validate 35/0/0 remain
preserved. Only disposable fixtures were changed. No partial-stack merge, signing,
release/publication, automation resumption or owner UAT was performed.
