# Single-action machine acknowledgment controller

Branch: `codex/recovery-acknowledgment-controller`.
Accepted at `996ec223261d15605cf12a6f3c281b5eb3a06825` in full successful
[Build 41139930489](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41139930489).
Windows trust 72/72, root Linux 86/86 and all inherited native gates passed.
The subsequent [incident-context increment](RECOVERY-INCIDENT-CONTEXT.md) continues
T7. Pending-CI language below records this controller's original handoff.
Base: #126 at `adbc52aa8699fc972af52697388ca4865383a297`, accepted in
[Build 41117670454](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41117670454).
Windows trust passed 64/64 including six report-store tests. Root-required Linux
passed 78/78 including seven report-store tests. Both native jobs, general checks
and trust jobs passed. Actual Windows SYSTEM and Mint 22.3 signed upgrades,
application recovery and the inherited manual/bootstrap/read-only markers passed.

## Bounded T7 task and acceptance criteria

Connect the accepted per-user report store to the existing machine intent API in
one native command, without exposing a final button before its remaining UX and
history contracts exist. This is a backend controller checkpoint, not completed
T7/T8 or permission to merge the partial stack.

1. `acknowledge_recovery_incident` accepts only the canonical public incident ID,
   explicit confirmation and a bounded optional historical Validation snapshot.
   It runs off the UI thread, holds the existing per-application Busy guard, and
   requests no separate elevation, file chooser, report preview or extra click.
2. Capture checks the current public machine incident and sanitizes native
   identity/read-only findings before attempting one report save. Invalid IDs,
   absent/changed/unreadable public evidence or invalid diagnostic input stop
   before intent submission. Observation failures remain unknown findings, not
   proof of inactivity or damage. No new Validation is run.
3. Storage failure produces a fixed warning and still attempts the existing
   generation-specific native intent submission once. Its gate, trusted-path,
   current public ID and protected journal-presence checks remain mandatory.
   Report failure cannot waive any of those checks. A standard-user controller
   does not attest private journal contents/binding; normal privileged consumers
   still verify and preserve the original evidence before any transition.
4. Return the captured incident ID, saved report ID if present, separate report
   warning, and `intentStatus: submitted | unconfirmed` plus submission warning.
   A later submission failure must not discard a successful report reference.
   A failed write/flush may be ambiguous: never claim no bytes were written,
   durable protected acknowledgment, execution permission, repair or completion.
5. No journal deletion, private receipt commit, archive/retirement, new operation,
   pending-action replay, OS authorization, automatic retry or publication occurs.
   The existing native mutation consumers remain solely responsible for fresh
   safety, evidence preservation, private binding and normal authorization.

## Tests and limits

The exact standalone controller source is compiled in the coordinator's two
native trust suites and in native Tauri. Six portable tests cover ordering and
exactly-once calls, storage failure, capture failure, retained report reference
on unconfirmed submission, both failures independently, and confirmation/strict
ID rejection before I/O. Two protected native tests exercise the real report
store and actual native submission against synthetic state: successful/save-failed
submission retains original bytes and blocks the legacy installation gate; a
gate acquired after report save prevents submission while retaining the report.
No archive or protected disposition appears just from the controller.

The protected tests require native Windows/root Linux. Local UID 1000 returns
early for these two tests; local harness counts are not native acceptance. The
six portable tests execute locally. Existing standard-user production-storage
probes remain required but are not a new end-to-end unelevated Tauri IPC proof.
Local static command wiring is not runtime UI evidence. Native CI must also pass
all inherited feasibility, manual, installed-bootstrap, read-only validation,
application and scheduled-tool recovery, actual Mint 22.3 and signed upgrades.

## Remaining integration / durable continuation

No frontend caller uses this command yet. Machine-only context remains explicit;
user-only incidents must not be routed here. Immutable reports still say they
were captured before acknowledgment. This response supplies the report/intent
cross-reference, not a durable history of later privileged acknowledgment or
continuation; abrupt application termination can lose the response while a saved
report and/or intent remain. Reinspection, not automatic retry, must handle that
case in the final UX.

Next: extend capture for user-only provenance and actual Validation timestamps;
connect retained report/history observations with honest later acknowledgment
status; then wire a single final action and resume through ordinary preflight,
confirmation and OS authorization. Keep selected deletion separate from minimum
operational state. Startup/cancellation must never replay a mutation. Final
frontend tri-state admission and report/history viewing remain T7/T8 work.

On a completed-run notice, verify exact head and results once, diagnose any
failure, then continue the next bounded task above if accepted. The PR comment
records source SHA, initial Build URL, local evidence and pending native gates.
No scheduler is active. No signing approval, release, UAT or partial-stack merge.
Owner Windows interruption evidence and Mint v1.2.18 35/0/0 remain untouched.
