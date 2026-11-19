# Local leave-disabled choice

Part of #161. Schedule now offers an explicit “Leave maintenance disabled” choice, using the read-only inspection and machine/definition context merged through #178 and #180. Full exact-main validation of that context passed at `e031209bf7f7c9bf5b512b3d9db0036c97997f1a`: [Build evidence](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/44585391535).

An explicit choice can settle the current user's display decision while the observed schedule remains Disabled. It is a preference in that user's local app profile, not native policy, a signed receipt, proof of intent or consent to any operation. Editing it can affect only that local display. No native consumer may use it to enable maintenance, resume SDE updates, acknowledge an incident or authorize execution.

## Contract implemented here

- A read does not write. Saving is a separate function reserved for an explicit user decision.
- Applying or saving requires a fresh, complete, verified Disabled observation for the fixed owned task/timer. Missing, unavailable, history-only, stale and future observations cannot settle the decision.
- Context requires opaque bounded machine and definition identifiers, plus the fixed task/timer identifier. The local record stores a SHA-256 context fingerprint and observation/choice times. It contains no raw identity, command, path or native permit.
- Another machine, definition or target does not match. The app profile supplies user isolation. The record cannot express another user's system-wide decision.
- The exact five-field schema is bounded to 1024 characters. Malformed, extra-field, unknown-decision, inconsistent-time and future records are ignored. Invalid data is not automatically rewritten.
- Storage failures and failed readback return an unsaved result with a useful message. They cannot manufacture a successful save. Existing history and schedule observations remain unchanged.
- The choice can be recognized again after a temporary unknown read only when new verified Disabled evidence and the same context are available. It never changes that state to Enabled or settles an active-work finding.

## Save workflow

Opening Schedule reads the current status and any matching saved choice. It does
not write. For a verified Disabled schedule with recognized context, the student
can choose **Leave maintenance disabled**. That click checks the schedule again.
Only fresh, complete Disabled evidence for the same machine, target and definition
can save the choice. Changed or incomplete results require a new review; no old
choice is applied as proof that the check succeeded.

The check and save stay in the same card. Duplicate clicks cannot start another
request. Leaving the page invalidates the request, including a save waiting for
its hash, before it can write. Storage denial or failed readback stays unsaved
with a retry. A failed native check retains the existing check/support path.
Success moves focus to the schedule heading and confirms the choice in place.

The status still says Disabled. Earlier failures and a Mint timer that remains
active in the current session stay visible. The card explains that saving does
not enable, disable or start anything. An unsupported context offers check/support
guidance without a new required-tool warning. A saved choice is recognized again
only alongside fresh matching Disabled evidence. The Overview maintenance card recognizes the same saved choice without reporting
maintenance as healthy or settling its history/current-session findings. The
broader procedural Your next step integration remains a separate criterion.

Full restoration remains subject to the [scope and preservation audit](MAINTENANCE-RESTORATION-SCOPE.md). This local preference cannot silently block or permit a future installer action. Actual operation review, normal OS permission, fresh native admission and all signing/UAT/promotion gates remain independent.

## Native context increment

The existing read-only schedule readers now provide optional `choiceContext`.
Context is used only to bind the local display preference. Its native CI and
full exact-main evidence passed before this UI integration.

Windows reads the OS installation's MachineGuid through the read-only 64-bit
registry view and hashes it with a domain prefix. It hashes the bounded task XML
separately. Context is returned only for a SYSTEM task owned by SYSTEM or
Administrators whose single action matches one of SDE's fixed maintenance
launchers. A denied registry/owner/XML read or another action omits context
without hiding the independently readable schedule. No ACL or task is changed.

Mint hashes the bounded `/etc/machine-id` with the same domain prefix. It binds
the complete bytes of the fixed timer and service files, including the known
installed history-hook drop-in when present. These files and their ancestors
must be root-owned and not writable by other users; linked, oversized, changing,
missing or unreadable files omit context. Other fragment/drop-in layouts and a
pending systemd daemon reload also omit context. This conservative recognition
can leave Save unavailable for an unsupported custom layout. It does not mean
that layout is broken, and it must not produce a new required-tool warning.

The native bridge accepts only complete fixed-target contexts with lowercase
64-character hexadecimal hashes, alongside a verified Enabled or Disabled
schedule observation. Old records may omit context; explicit null, malformed,
partial, mismatched-target and extra-field context objects are rejected.
The frontend preference still requires fresh verified Disabled evidence to save.
History, PID, next-run time and a hostname do not supply machine identity.

The identifiers bind an OS installation, not physical hardware. An image cloned
without regenerating its OS machine identity can duplicate this context. This
is one reason the record is only a local display preference and must never
serve as authority, ownership proof, an acknowledgment or operation consent.
The normal application profile supplies the user boundary. No raw machine
identifier or task XML is placed in the local saved-choice record.

Required native evidence includes standard-user Windows context reading without
control permission, changed-definition invalidation and unchanged task state;
Mint protected-file refusal cases and systemd state regressions remain required.
The UI keeps explicit Save, fresh rechecking, duplicate/late-result handling,
storage-denial guidance and truthful Disabled/current-session/history messages
in place. All existing release gates remain required.

Local validation of this increment: all 353 unit cases and the seven positive /
seven required failure runner controls pass; type checking and build pass. Six
Rust schedule cases pass. Python scheduling has 21 passing local cases and six
protected/systemd cases deferred to disposable CI. Backend contracts (35),
metadata tests (68), CI-policy tests (35), PowerShell parsing/refusal, document
and diff checks pass. The Linux integrity manifest includes the updated reader.
These checks do not substitute for Windows standard-user/native evidence or the
required protected/systemd cases. Full native/trust/acceptance CI is required.

## UI validation

All 363 unit cases pass, including ten new flow/cancellation cases and the eight
saved-choice contract cases. The seven positive/seven required failure runner
controls pass. Both new keyboard/persistence/storage-denial/accessibility cases
pass at 390px and 1140px, along with the two existing maintenance-inspection
browser cases. Every earlier assertion fingerprint and test inventory is retained.
Type checking/build, dependency audit (zero findings), backend contracts (35),
document and diff checks pass. Full CI must run all 134 browser cases and the
native/trust/acceptance gates before merge. Exact-main evidence, human signing,
exact authenticated-candidate owner UAT and separate promotion remain required.


## Overview maintenance card

The Overview card presents only maintenance findings. Review opens Schedule;
support uses the existing report review. Neither action starts maintenance,
changes settings or writes the preference. The card reads a saved choice only
alongside fresh, matching Disabled evidence. It immediately drops the displayed
confirmation for a pending read or a different observation/context. Storage
failure, stale data, missing context and incomplete history cannot claim the
choice is settled. Late preference reads cannot update an unmounted card.

A matching saved choice changes the display heading to “You chose to leave weekly
maintenance disabled.” The actual Disabled state, a Mint timer still active in
the current session, running work and earlier failed/unavailable results remain
visible. A preference never changes the health classifier, required-tool
readiness, task-card decision, native admission or operation review. Earlier
history and observed time are available in the card's own Details.

All 371 unit cases pass, including eight added display/context cases. Two new
browser cases at 390px/1140px pass through Overview, Schedule Save and back,
then test changed context and failed inspection. They verify keyboard/focus,
accessibility, no horizontal overflow and zero modifying operations. Build/type
check, audit (zero findings), backend contracts (35), metadata tests (68),
CI-policy tests (35), docs and diff checks pass. Every original assertion
fingerprint and inventory remains intact. Full CI must run all 136 browser
cases and all native/trust/acceptance gates. Exact-main, signing, owner UAT and
separate promotion requirements remain unchanged.
