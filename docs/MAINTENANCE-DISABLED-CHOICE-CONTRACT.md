# Local leave-disabled choice: preparatory contract

Part of #161. This branch builds on the maintenance inspection implementation in #178. The module is preparatory: it is not connected to the UI or a native context provider and does not complete the leave-disabled workflow.

An explicit choice can settle the current user's display decision while the observed schedule remains Disabled. It is a preference in that user's local app profile, not native policy, a signed receipt, proof of intent or consent to any operation. Editing it can affect only that local display. No native consumer may use it to enable maintenance, resume SDE updates, acknowledge an incident or authorize execution.

## Contract implemented here

- A read does not write. Saving is a separate function reserved for an explicit user decision.
- Applying or saving requires a fresh, complete, verified Disabled observation for the fixed owned task/timer. Missing, unavailable, history-only, stale and future observations cannot settle the decision.
- Context requires opaque bounded machine and definition identifiers, plus the fixed task/timer identifier. The local record stores a SHA-256 context fingerprint and observation/choice times. It contains no raw identity, command, path or native permit.
- Another machine, definition or target does not match. The app profile supplies user isolation. The record cannot express another user's system-wide decision.
- The exact five-field schema is bounded to 1024 characters. Malformed, extra-field, unknown-decision, inconsistent-time and future records are ignored. Invalid data is not automatically rewritten.
- Storage failures and failed readback return an unsaved result with a useful message. They cannot manufacture a successful save. Existing history and schedule observations remain unchanged.
- The choice can be recognized again after a temporary unknown read only when new verified Disabled evidence and the same context are available. It never changes that state to Enabled or settles an active-work finding.

## Required before UI integration

The native context increment below adds bounded read-only machine/definition identifiers. Its required native CI evidence must pass before offering Save. A hostname, a timestamp or displayed frequency alone is insufficient. Do not add privileged write authority for this preference.

Connect it only to the explicit leave-disabled decision. Recheck fresh status before saving, reject duplicate/late submissions and invalidate the displayed choice on changed context or state. A disabled-but-active Mint timer still needs truthful current-session guidance. Respect support/report, navigation and storage-denial paths in the same flow.

Full restoration remains subject to the [scope and preservation audit](MAINTENANCE-RESTORATION-SCOPE.md). This local preference cannot silently block or permit a future installer action. Actual operation review, normal OS permission, fresh native admission and all signing/UAT/promotion gates remain independent.

## Local evidence

Eight focused cases pass: read-only opening; explicit save and unchanged history; context separation; unsupported evidence states; stale/future observations; malformed/oversized/future records; storage/readback failures; missing identity/unsupported targets. Type checking and production build pass. The module is not imported by the application entry point, so this is contract evidence, not a shipped workflow or owner UAT result.

The original preparatory branch was published without a code PR or CI dispatch. The current native context increment requires full validation before UI integration. Preserve the passing inspection implementation and complete the explicit user flow separately.

## Native context increment

The existing read-only schedule readers now provide optional `choiceContext`.
This is a foundation for the explicit user choice; the Save control is still
unavailable and the module remains unconnected to the application UI. Native
context CI must pass before that integration.

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
UI integration still needs explicit Save, fresh rechecking, duplicate/late-result
handling, storage-denial guidance and truthful Disabled/current-session/history
messages in place. All existing release gates remain required.

Local validation of this increment: all 353 unit cases and the seven positive /
seven required failure runner controls pass; type checking and build pass. Six
Rust schedule cases pass. Python scheduling has 21 passing local cases and six
protected/systemd cases deferred to disposable CI. Backend contracts (35),
metadata tests (68), CI-policy tests (35), PowerShell parsing/refusal, document
and diff checks pass. The Linux integrity manifest includes the updated reader.
These checks do not substitute for Windows standard-user/native evidence or the
required protected/systemd cases. Full native/trust/acceptance CI is required.
