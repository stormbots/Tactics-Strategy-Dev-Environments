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

## Local verification and remaining gates

- Full local frontend suite: 332 passed. Production TypeScript/Vite build passed. The final additional collection-success/result-code checks passed their 16 focused parser cases and the browser flow afterward.
- Production-App tests cover no action on opening review, duplicate rechecks, deferred results, unresolved access, collection failure, late navigation and independent required-tool failure after the preferences finding resolves.
- Two browser simulations passed in Chromium 154 at 390 and 1140 pixels, with keyboard entry, focus, long-path layout, accessibility checks and failed-check continuation. Color-contrast rules were excluded from these automated accessibility checks. These are simulated backend observations, not native permission or owner UAT evidence.
- Backend contracts and CI-policy tests: 35 each passed. Native source and integrity files are unchanged.

This branch starts from main `6aa9cefe69edfb3b82c1f426722addd76cebcc07` and does not depend on unmerged #174. It uses the unchanged development toolchain for local tests. The known high-severity dependency advisory still blocks release CI; no audit exception is implied by successful local tests.

No PR or new CI is needed merely to preserve this checkpoint. Opening the eventual code PR requires full validation under the current policy, including Windows/Mint native, both trust jobs and acceptance. Refresh the branch and rerun checks after dependency remediation. Signing, exact authenticated-candidate owner UAT and separate stable promotion authorization remain required.
