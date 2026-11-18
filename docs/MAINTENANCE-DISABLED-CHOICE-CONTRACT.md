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

The native readers do not yet provide the required stable machine/definition identifiers. A hostname, a timestamp or displayed frequency alone is insufficient. Establish a bounded read-only provider and its ownership/context-change contract before offering Save. Do not add privileged write authority for this preference.

Connect it only to the explicit leave-disabled decision. Recheck fresh status before saving, reject duplicate/late submissions and invalidate the displayed choice on changed context or state. A disabled-but-active Mint timer still needs truthful current-session guidance. Respect support/report, navigation and storage-denial paths in the same flow.

Full restoration remains subject to the [scope and preservation audit](MAINTENANCE-RESTORATION-SCOPE.md). This local preference cannot silently block or permit a future installer action. Actual operation review, normal OS permission, fresh native admission and all signing/UAT/promotion gates remain independent.

## Local evidence

Eight focused cases pass: read-only opening; explicit save and unchanged history; context separation; unsupported evidence states; stale/future observations; malformed/oversized/future records; storage/readback failures; missing identity/unsupported targets. Type checking and production build pass. The module is not imported by the application entry point, so this is contract evidence, not a shipped workflow or owner UAT result.

The branch is published without opening a code PR or dispatching CI. Preserve the passing inspection implementation and integrate this contract only after its native context and UI completion requirements are ready for review.
