# VSCodium preferences access review

Part of [#161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161). This increment connects the accepted access-denied explanation and review flow on the Validation page. The later Overview card integration remains open.

## Student workflow

When the native check confirms that SDE cannot read the preferences file, Validation names VSCodium and explains that it is the app used to write code. The message says the check is incomplete and that the settings have not changed. It does not say that the editor is missing or broken.

**Review access problem** opens an inline review. It shows the affected file as text and asks the student to use the correct normal desktop account. If access needs attention, the student can ask a teacher or administrator to check it. The review does not recommend giving everyone access, deleting preferences, running SDE elevated, or using broad Repair to bypass permission checks.

**Check VSCodium again** runs SDE's existing normal validation, including its read-only safety sequence. The wording explains that these are normal setup checks, rather than a new editor-only installer. It stays on Validation. The review and earlier results remain visible during checking.

A complete fresh preferences observation replaces the earlier result. If access is still denied, the review stays open. If preferences can be read or are genuinely absent, that access finding can go away while unrelated tool failures remain. A missing preferences file means the editor can use defaults; it does not prove required editor features passed. Other preferences failures retain their own messages.

If collection fails, is deferred, has conflicting records or does not finish, the earlier results stay visible with a clear earlier-results label. They never become current readiness or execution authority. Operation-review buttons on these retained rows are disabled. The student can check again or create a support report in the same flow. Reports still use the existing review-before-sharing dialog.

Finishing a check after navigation does not redirect the user back. A newly active native operation can still send the user to Recovery; the access flow cannot override it. There is no automatic retry, installation or settings change.

## Evidence boundaries

The UI accepts one bounded, schema-checked `preferences` observation for VSCodium's standard user file, with a supported status/reason pair. Successful reads require the three supported recommendation records. Duplicate/malformed records, unsupported scopes and unsafe display strings are rejected. A terminal validation summary, normal validator result and collection time are needed before a fresh observation replaces retained evidence.

The confirmed access-denied record must also match its warning row before the special review is offered. Other messages retain existing diagnostic guidance. The path is displayed through React text; it is not supplied to Open, an elevated command, a writer or a shell.

The retained snapshot feeds only the Validation display. The existing current report, review fingerprint, request identity, native read queue and fresh native admission still control readiness and changes. Neither this view nor an old result can acknowledge an incident or resume policy.

## Test preservation and verification

This branch now includes main `6d1e775d546c6cb79a11f632070c594dd2f64222`, whose full exact-main run passed. The earlier dependency blocker was resolved by the merged tooling migration; this increment uses the esbuild/Node/Playwright-core stack and keeps the full npm audit gate.

The inventory explicitly registers the 19 prepared unit cases and two prepared Chromium scenarios. Every existing main App assertion remains in order, and the prepared parser/browser assertion expressions are unchanged. One additional regression rejects an array in the status field instead of allowing JavaScript property-key coercion to accept it. Malformed evidence cannot replace the retained display snapshot. The complete unit inventory is now 338 cases across 23 files; the default browser inventory is 130 cases (122 Chromium and eight WebKit).

- The complete local unit suite and its seven positive/seven failure controls passed, along with type checking, production build, installed-distribution checks and full npm audit (zero vulnerabilities).
- Production-App cases cover no action on opening review, duplicate rechecks, deferred results, unresolved access, collection failure, late navigation and independent required-tool failure after the preferences finding resolves.
- Browser verification covers the two prepared flow scenarios at 390 and 1140 pixels and existing Overview, validation-guidance, operation-lifecycle and combined safety flows. These are simulated backend observations, not native permission or owner UAT evidence. The flow's automated accessibility check excludes color contrast; the existing broader appearance/contrast checks remain required.
- Backend and CI-policy checks remain part of validation. Native/backend source, integrity files, IPC permissions, workflow gates and package versions are unchanged.

Full Windows/Mint native, both trust jobs, integrity and acceptance are required for the focused PR and the resulting exact main. The existing read-only validation path performs follow-up checks; this increment adds no writer, permission change, elevation path, installation action, automatic retry or safety acknowledgment. Later Overview integration remains open.

Human signing approval, owner UAT on the exact authenticated candidate and separate stable-promotion authorization remain required. No release version or publication is initiated by this increment.
