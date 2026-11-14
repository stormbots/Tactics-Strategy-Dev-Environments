# SDE review workflows — version 4

Open `index.html` in a browser. It contains all styling and behavior and needs no server. Earlier mockups and the production application are unchanged.

## Decisions used

- [#160: automatic startup and in-place recovery checks](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/160).
- [#161: the accepted plans, wording and review flows](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161).
- [Accepted shorter interruption flow](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161#issuecomment-6872640141).
- [Accepted shared workflow rule](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161#issuecomment-6872688825).

**Keep related steps together, automate required follow-up checks, and update findings in place.**

The top bar belongs to the simulation. It selects scenarios, platform and the result of the next action. Every observation and outcome is a sample. No device inspection or real operation occurs.

## What changed in version 4

Resolved findings now update automatically. A required Return to current findings step no longer stands between a successful check and its updated action list.

Failure results keep useful buttons in the current flow. They offer verification, troubleshooting, another installation choice or a new full-scope review as appropriate. They do not force the user to scroll back and reopen the same card.

Explicit decisions remain required for Repair approval, interruption acknowledgment, saving a location and leaving maintenance disabled. Follow-up verification is automatic after approved operations. Retrying a failed check still needs an explicit click; no retry loop is introduced.

## Suggested review paths

### 1. Installed Python and unresolved operation

Address Python requirement → Check Python 3.14. A successful check removes only the Python finding and updates Your next step immediately. With Still unresolved, the result offers Check Python 3.14 again directly.

The accepted version 3 safety route is unchanged: check operation status → direct Acknowledge interruption → automatic final safety check. Only successful fresh safety verification clears that finding. The original record is retained. Acknowledgment failure, changed incident, report failure and failed final safety checks remain distinct.

### 2. Missing Python or failed Node/npm setup

Locate an existing matching installation and check it, or review full Repair. Cancel starts nothing. Approval still needs the full scope checkbox and normal OS permission.

Repair runs through permission, operation and final verification in one sequence. Success removes the finding immediately. Select Final check fails to see a direct Check required features again action. That action does not restart Repair or request privilege approval again.

Download/operation failures offer the operation result and a fresh scope review before a new package-changing attempt. Denied permission means nothing started only because that specific sample native result confirms it. Unknown launch and changed safety require status review before another attempt.

A failed existing-installation check keeps the selected candidate for retry. The same result also lets the user choose a different installation or review setup. Wrong versions and inaccessible candidates do not pass.

### 3. VSCodium access

Review access problem → troubleshooting → Check VSCodium again. If unresolved, the result immediately offers recheck, troubleshooting and a support-summary preview. If successful, the access finding disappears without a Return click. Optional preference inspection does not falsely fail the already-verified app functionality.

### 4. Maintenance inspection and restoration

For unavailable status, read troubleshooting and Check maintenance status again. Success reads **Disabled** in this example, then immediately presents:

- Leave maintenance disabled.
- Review restoration operation.

Leave disabled records the explicit sample choice without enabling or running maintenance. The Disabled state remains visible under saved choices and on Schedule.

Review restoration uses full Repair scope and explicit approval. Final schedule verification runs automatically. A failed final check offers Check maintenance status again directly, rather than another Repair. Only successful verification clears the restoration finding.

Earlier maintenance results and automatic SDE app-update policy remain separate and unchanged.

### 5. Project location

Locate existing project → check the selected folder → explicit Save location. Changing the selected folder invalidates the earlier check. Unknown/inaccessible candidates cannot be saved.

Saving updates the location finding immediately and offers Open workspace beside the success message. That action previews the exact saved workspace. No file is moved, cloned or downloaded.

For an unavailable drive, troubleshooting and recheck stay together. After access is confirmed, Locate existing project is offered directly from that result.

### 6. Genuine startup check failure

Review check problem → Check setup again. This explicit recheck runs safety first, then required tool checks. Success updates findings immediately. Failure keeps recheck, details and support actions in the current result. Nothing retries on its own.

Normal startup remains automatic. Navigating during a check preserves the check and the current page. Resetting scenarios invalidates old simulation results so they cannot overwrite new state.

## Other scenarios and controls

All 14 scenarios remain in the same order. Ready coexistence, preferences and alternate application locations remain informational when the required capability is verified. Self-contained cards describe only their own situation; only Your next step connects findings.

Next action result applies to the matching action type. For example, Download fails affects the package-changing operation, while acknowledgment/report outcomes apply to safety review. Changing the result selector alone starts nothing.

Platform/scenario changes and Reset clear preview state. Save and Leave disabled are stored only in memory for this demonstration, not persisted to a device.

## Capability and evidence limits

Full Repair routes are design illustrations, not proof that the current backend meets every preservation requirement. Engineering must confirm actual scope, coexistence, configuration preservation and native authorization before offering real execution. No Python-only installer, schedule-only Enable API, new selective-repair engine, runtime-manager switch or arbitrary elevated path is introduced.

No commands, installs, permission changes, file writes, policy changes, report collection or network calls run. The owner established that Python 3.14.9 can run, not that all other sample checks passed.

Native code must still enforce fresh activity, package, trust, ownership and incident-generation checks immediately before changes. No UI result or acknowledgment grants execution permission. Existing human signing, exact-release owner UAT and separate promotion approval remain required.

Browser verification results are saved in `prototype-validation.json`. They cover prototype behavior only, not application/native/device or packaged UAT acceptance.

## Run the offline prototype checks

From the repository root, install the existing installer development dependencies if needed, then run `node docs/refine-ux-follow-up-demo/verify.cjs`. It uses the existing Playwright and axe packages. Set `SDE_CHROMIUM_EXECUTABLE` to use a specific Chromium binary. Outputs go under `verification-output/` unless `SDE_MOCKUP_OUTPUT_DIR` selects another directory. This runs browser simulation checks only; it never invokes native SDE commands or CI.
