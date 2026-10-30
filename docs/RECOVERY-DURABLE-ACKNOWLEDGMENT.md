# Durable acknowledgment: engineering and native validation handoff

Accepted exact head `046d56bd4f5f723e1d21eadbbc95674c558016ac` in
[Build 40800652705](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/40800652705).
DevOps confirmed Windows trust 30/30, required Linux root storage/crash-replay
tests, permission checks, Windows feasibility markers, both native builds and
signed-upgrade checks. No merge, release, owner UAT, or evidence change occurred.
The scope below is historical; the next increment is
[safe transition](RECOVERY-SAFE-TRANSITION.md).

Branch: `codex/recovery-durable-acknowledgment`.
Base: verified PR #114 head `59884166cd336153160238f7367dcec0b136744a`.
Build `40792896158`, attempt 2, passed the production-storage native gate on that
base. This branch includes still-unmerged #113/#114 work; do not assume main
contains those changes. This document describes the next bounded increment,
not the completed redesign or a release/UAT candidate.

## Implemented

`coordination/src/recovery/acknowledgment.rs` provides production APIs to record
a submitted decision and inspect a sanitized acknowledgment. Recording holds
one operation lease, validates current private binding/hash/file generation and
public incident identity, and reconciles a valid student intent into:

1. A private byte-identical evidence copy at
   `recovery-archive/<incidentId>.journal`.
2. A private receipt at `recovery-archive/<incidentId>.receipt.json`, including
   original binding and committed acknowledgment time.
3. A protected publicly readable `recovery-disposition.json` containing only
   schema, incident ID, and acknowledgment time.

Final evidence/receipt publication never overwrites an existing destination.
Linux uses `renameat2(RENAME_NOREPLACE)` and Windows uses a write-through move
without the replacement flag. Files are flushed before publication. Linux also
syncs directories; Windows uses the existing write-through publication contract.
Unsupported Unix platforms fail rather than silently using replacing rename.

An existing committed receipt remains authoritative if the writable intent is
later lost/edited, but only for the same exact current journal generation and
its intact archived evidence. The public view can be reconstructed from that
receipt. No acknowledgment, archive directory, or receipt is invented when there
is no valid submission. New generations require a new decision; a stale receipt
cannot approve an identical-byte replacement journal.

Windows recovery file access now validates every directory between ProgramData
and the archive, including the coordination root. Raw journal and receipt data
remain private. Only opaque incident filenames may be listed in the archive.
No tokens or raw binding identities/hashes are exported in the public view.

## Deliberate safety boundary

This increment does not delete/rename/replace the active protected transaction
or start a new one. `operation()`/`installation()` and installed script/updater
guards remain unchanged. Tests require them to keep blocking even after an
acknowledgment is committed. This is not a bypass or a final continue action.

Normal app startup, bootstrap, GUI, scheduler, validators, and mutation consumers
do not call the new recording API yet. Fresh global activity/package observations,
lease-bound transition to a new transaction, automatic reports, history deletion,
and final UI/resumption are dependent work. Report-generation failure policy is
unchanged; reports are not authorization and are not implemented by this layer.

No owner workstation action occurred. Windows interruption evidence and Mint
v1.2.18 acceptance (35 passed, 0 warnings, 0 failed) remain preserved. There is
no version, signing, publication, fleet, automation, or milestone change.

## Targeted local checks

- Rust coordinator harness: 30 successful entries. The new pure public-schema
  test ran; protected fixture tests return early at the local non-root UID and
  are not reported as native proof.
- Linux and Windows GNU test-target Clippy passed with warnings denied.
- Rust formatting and diff checks passed.
- Existing fail-fast coordinator CI behavior and required feasibility markers
  remain unchanged. Cross-compilation is not Windows MSVC/native execution.

## Required DevOps evidence

Use this PR's exact head, not the base or a fixture-only workflow. Inspect the
existing Build Skyview Dev Setup run without dispatching duplicates or polling.
Require all existing coordination, trust, native build, and signed-upgrade checks,
including the dedicated Windows feasibility marker step.

For the new coordinator suite, require actual native Windows execution and the
Linux root-required invocation with `SDE_REQUIRE_COORDINATION=1`. A non-root test
harness result alone is not proof. Inspect these named tests:

- `durable_acknowledgment_survives_process_termination_at_every_commit_boundary`:
  a synthetic test executable is forcibly terminated after evidence, receipt,
  and public-view publication. Restart/replay preserves exact bytes, reconstructs
  the decision where committed, retains the gate until termination, and leaves
  both old execution guards blocking. No package process is launched or killed.
- `durable_acknowledgment_recovers_each_failed_publication_checkpoint`:
  deterministic post-publication errors leave a recoverable state. A receipt
  survives losing the mutable intent.
- `durable_acknowledgment_preserves_evidence_and_survives_intent_loss_and_restart`:
  receipt/time remain unchanged and raw current evidence is never cleared.
- `durable_acknowledgment_old_receipt_cannot_acknowledge_a_replacement_generation`:
  byte-identical new records do not inherit a prior decision.
- Archive no-replacement, corruption/missing-evidence, no-submission, busy-gate,
  and platform-specific parent-permission/link rejection tests also pass.

There are 30 test entries per supported target at this increment. Test helpers
with no fixture environment are intentional entry points, not the native proof;
the parent tests must actually run under the required privilege context.

Return exact head SHA, workflow/job URLs, command results, and any failing
assertions to engineering. Infrastructure issues remain DevOps diagnosis; do not
waive validation or infer success from the older accepted source. If CI is
pending, report its URL and next action, then end rather than polling.

Do not merge partial work, publish, sign, prepare a candidate, request UAT, resume
automation, or alter owner evidence. Continue engineering after this native
lifecycle gate: lease-bound safe transition, observation/OS adapters, installed
backend/updater/bootstrap integration, and report/history/Recovery UI work.
