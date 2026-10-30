# Per-user recovery report storage foundation

Branch: `codex/recovery-report-storage`.
Base: accepted #125 at `281dcbe3bb182718b1aa8a97ac9f948d4263ad3c`,
[Build 41105464316](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41105464316),
full success. General/integrity, both trust jobs and both native jobs passed,
including Windows read-only validation, Linux host/actual Mint 22.3 read-only
validation, application recovery and both signed native upgrades.

## Bounded T7 storage task

This increment provides the automatic-save/history backend, not the final
one-click acknowledgment or Recovery UI. Reports are user artifacts, never
machine coordination or authorization state. The stack remains unmerged.

- Four fixed-path commands save a summary automatically, list a history page,
  read a selected summary as fresh escaped HTML, and delete a selected report
  only after explicit confirmation. No filename, directory, HTML or executable
  is accepted from the frontend. Only opaque canonical report/incident IDs and
  a bounded optional Validation snapshot are accepted. Permissions are granted
  only to the existing local main window, without shell/filesystem plugin grants.
- Save verifies the current public machine incident ID before capture. It gets
  app version, platform/device identity and read-only safety findings natively;
  the frontend cannot supply replacement current safety findings. Validation
  data is historical diagnostic input, not attestation or an execution permit.
  Preserve a supplied collection timestamp; if unavailable, explicitly say so
  rather than substituting report-capture time. No Validation is run to save a
  report. Original private bytes, source stage and completion are not collected;
  the report states those evidence limits instead of inventing provenance.
- The destination is the current account's fixed app-data `recovery-reports`
  directory, not Downloads or a caller path. Commands run off the UI thread and
  never request elevation, a save dialog or preview. Existing token/credential
  and personal-home redaction is applied before saving and on readback. Detailed
  logs are absent by default. Device/platform summaries can still identify a
  workstation; generated HTML explicitly warns before user-initiated sharing.
- Save failure returns `saved: false` with a warning, not a successful artifact
  or acknowledgment. The command does not decide whether later acknowledgment
  can proceed: that controller must separately verify original operational
  evidence and apply the approved nonblocking-report-failure policy.

## Publication, retention and deletion

Each fresh report UUID gets a new, never-overwritten directory containing
`summary.json`, `report.html`, and a last-written `committed.json`. Data files
are size-bounded, exclusively created and flushed before the commit marker;
the marker binds both hashes. Until all records validate, history labels the
bundle incomplete/unreadable rather than saved. Partial writes stay available
for diagnosis and explicit deletion; errors do not trigger a cleanup/purge.
This is a logical committed-bundle boundary, not a claim of tested power-loss
durability on every filesystem. Unix directory entries are also flushed;
Windows uses normal per-user AppData inheritance and file flushes. This adds
no machine ACL or administrator service. Full Windows ACL privacy and abrupt
power-loss behavior are not established merely by portable unit tests.

The store rejects links/reparse points, unexpected file types, hardlinked files,
invalid/traversing IDs, oversized records, changed hashes and unknown schema
fields. Unix directories/files must belong to this effective account and remain
0700/0600-private. Paths are not canonicalized through a link to make it trusted.
This is same-account user storage, not a privileged boundary against that user
editing their own app data. No stored report is later read as a native permit.

History uses bounded UUID-ordered pages and retains every bundle until explicit
deletion, with no age/count purge. A page cursor does not mean older records were
deleted. Deletion validates only the three fixed filenames before unlinking any
of them, never recurses, refuses unexpected contents, and does not touch other
reports or operational state. A partial deletion is reported for explicit retry.
Deleting report views must never reset machine incident IDs, protected evidence,
acknowledgment receipts/intents or the existing user operation journal.

The stored HTML is a passive artifact with restrictive CSP and escaped values.
The read command validates the committed snapshot, redacts again, and renders
fresh HTML from its typed data rather than trusting stored HTML as active
content. No scripts, network assets, links, automatic upload, recipient or remote
service is introduced. Viewing/export UI remains later work.

## Verification and scope limits

The exact standalone storage source is also compiled by the coordinator's test
harness on both native trust paths, without linking a GUI or adding it to
production machine-coordination code. These tests run as the current user and
do not return early at local UID 1000. Native Tauri also compiles/tests the same
source. Seven local tests passed: committed roundtrip/timestamps/passive HTML,
partial-publication failures, corruption/size/schema rejection, selected deletion
without touching an evidence stand-in or other report, pagination without purge,
hardlink rejection on both platforms, and Unix link/private-mode rejection.

Local Linux/Windows-GNU coordinator clippy, 21 backend contracts, 20 workflow/scope
tests, three command-permission wiring tests, locked offline Tauri metadata,
formatting and diff checks passed. The existing `sha2` version is now a direct
Tauri dependency for report integrity; no version/key/trust mechanism changed.
Native Windows execution, actual Tauri compilation/IPC and every inherited
cross-platform installation/trust gate remain pending CI. No unchanged frontend
or real native package suite was re-run locally and reported as new evidence.

Remaining T7/T8 work is explicit: machine-plus-user-incident report context,
one-action report-attempt plus intent submission/status cross-reference,
retained machine/history observations, actual Validation timestamps at the UI
boundary, report/history viewing and selected deletion confirmation, and final
acknowledgment/resume UX. This API currently captures machine incidents only;
do not wire a user-only incident into it or silently pretend that source exists.
Its immutable summary honestly says it was captured before acknowledgment;
it does not yet maintain later acknowledgment/continuation status. Saving,
listing, viewing or deleting a report cannot unblock changes in this increment.

## Durable continuation

The PR comment records exact source SHA and initial Build URL. On a completed-run
notice, verify current head/results once, resolve failures, then automatically
continue the next bounded T7 integration above. Do not return only status when
planned work is unblocked. End with a checkpoint if only long CI remains; no
scheduler is active. Signing and owner UAT remain human gates. No partial-stack
merge, release, publication, fleet rollout or milestone closure here. Preserve
Windows interruption evidence and Mint v1.2.18 Install/Validate acceptance 35/0/0.
