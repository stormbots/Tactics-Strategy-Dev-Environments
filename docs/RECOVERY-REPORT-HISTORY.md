# Retained summary history and explicit share-copy export

Branch: `codex/recovery-report-history`. Bounded T7/T8 integration accepted at
`c069922659eac695f33ff4eff6682d4cf506832a` in
[Build 41234049333](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41234049333).
All 159 frontend/93 browser tests, Windows trust 121/121, root Linux 135/135,
native Tauri Windows 94/94 and Linux 91/91 passed. New listing/export tests and all
inherited recovery/signed SYSTEM/actual Mint 22.3 gates passed. Real save-dialog
and manual sharing acceptance remains owner UAT, not automated fixture proof.
Base #134: `d954c6d768c8c70dae50ca7835babf00cc4171e9`, accepted in
[Build 41226670429](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41226670429).

## Acceptance criteria

- Use the existing Recovery destination for this account's retained report list,
  bounded 25-entry pages, explicit refresh and recent saved report references.
  Opening history does not create missing report storage. Missing is empty;
  unreadable/unsafe existing storage is an error, not an empty history claim.
- Load only the selected committed report by canonical ID through existing native
  fixed-directory APIs. Show the source, separately observed acknowledgment status
  and timestamp, and explicitly say continuation/completion is not recorded.
  A missing current machine disposition is unknown, not "never acknowledged".
- Display fresh native-rendered escaped HTML in an opaque-origin sandboxed iframe,
  with no script/same-origin capability or referrer. Never inject report HTML into
  the main application DOM. Retain the passive document CSP. No private journal,
  binding, restart key or detailed log is added to the summary.
- Export is an explicit optional share-copy action after review. The native command
  accepts a report ID only, reloads/verifies the bundle, reapplies redaction and
  renders a new passive copy; it accepts no caller HTML, input path or command.
  The normal file-save window selects the destination. Cancel is not success.
  Sharing is manual: SDE never uploads the file or sends it to another person.
- Copy export requires a new absolute .html filename outside canonical SDE account
  application data. Exclusive creation rejects existing files, hard/symbolic links
  and overwrites. An incomplete copy may remain after a write failure; report that
  failure and leave the retained source untouched, without recursive cleanup.
- Deletion requires a separate confirmation naming the selected local report.
  It removes only that bundle's known report files under existing validation; no
  bulk purge or recursion. Cancel keeps it; partial/unconfirmed failure is not
  success. Existing exported copies cannot be recalled. Protected original evidence
  and minimum acknowledgment state survive; deletion cannot enable mutation.
- None of list/view/export/delete acknowledges an incident, clears a gate, alters
  readiness or launches/continues work. No recurring status polling is introduced.

## Implementation and validation

`RecoveryReportHistory` is embedded below current Recovery findings. Readiness and
acknowledgment controllers are not imported by the history component. Separate
serialized UI actions prevent duplicate deletion or exporting while another report
action is pending. Recently captured report IDs can be opened directly even when
UUID paging places them outside the first page. Incomplete bundles are labeled,
cannot be previewed/exported and remain eligible only for explicit validated deletion.

The native history list now uses an existing-only constructor and bounded listing;
view/export/delete also avoid provisioning storage after disappearance. Export uses
the existing OS save chooser but a distinct `export_copy` writer: unlike general
support-report saving, it never truncates an existing file. It renders verified
typed summary data, not a stored HTML payload or frontend-supplied document.
This protects against accidental overwrite; it is not a claim of isolation from
malicious same-account filesystem changes or a privileged execution capability.

Local validation: 159 frontend tests, production TypeScript/Vite build, 11 portable
report-storage/export tests, Linux and Windows-GNU coordinator clippy with warnings
denied, 31 backend contracts, four permission checks and whitespace checks pass.
Coverage includes missing/unsafe directory observation, committed/partial/corrupt
bundles, selected deletion, paging, native passive copy generation, no-overwrite,
hardlink and internal/aliased-directory rejection; UI unknown/unavailable findings,
sandboxed preview, explicit export/cancel, confirmation/cancel/duplicate deletion,
partial errors and direct recent-report references. A test-created hardlink must
make normal report readers fail closed until that disposable alias is removed.

Local browsers are known absent in this Cloud executor; no browser or real save
dialog acceptance is claimed. Existing CI installs Chromium/WebKit and must pass
the full browser suite, including four test-only synthetic report light/dark
640/1140px review/export-cancel/deletion/axe/reflow cases. Native Windows/Linux
tests must exercise the actual export-copy source and all inherited standard-user,
bootstrap/manual/scheduled/application and signed SYSTEM/actual Mint 22.3 gates.
The native save window and manual file sharing remain focused owner UAT later.

## Remaining work, not hidden by this report list

This is **report history**, not a complete incident ledger. A failed save or deleted
report cannot erase its original operational evidence or minimal decision, but the
current list cannot discover every such incident. Next: report-independent minimal
history (including older machine dispositions and bounded user-history lookup),
explicit history deletion semantics, unavailable/malformed-source self-service and
remaining generic exit-75/error-copy review, then consolidated native/UX acceptance
and focused owner UAT preparation. Do not claim milestone completion from this UI.

Owner Windows interruption evidence and Mint v1.2.18 Install/Validate 35/0/0 remain
preserved. All filesystem fixtures are disposable. No partial-stack merge, signing,
release/publication, automation resumption or owner UAT was performed.
