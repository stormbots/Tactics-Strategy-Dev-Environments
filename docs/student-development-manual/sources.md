# Source record and example limits

This manual was checked against repository files and selected GitHub records on November 14, 2026. It is a learning draft, not a live CI dashboard or release acceptance record.

## Fixed historical examples

| Example | Verified source | What the manual uses it to teach |
| --- | --- | --- |
| Startup requirement | [Issue #160](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/160) and [implementation record at merged startup source](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/9f1c316b13edfcbc221eef9eb6ffccfae125b399/docs/STARTUP-CHECK-IMPLEMENTATION.md) | Observation versus hypothesis, read ordering, retained safety rules and evidence limits. |
| Startup PR | [PR #162](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/162) | A focused implementation plus a test-helper correction. Verified merged as `9f1c316b13edfcbc221eef9eb6ffccfae125b399`. |
| Original failure | [Run 43568067928](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/43568067928) | The protected test's successful-exit assertion failed and acceptance failed. |
| Corrected startup checks | [Run 43581367274](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/43581367274) | Applicable checks passed for head `2c4dec71db8ff340be3d45b6f3fb52cee3b08f72`. |
| Actual queue assertions | [nativeReadQueue.test.ts at the merged startup source](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/9f1c316b13edfcbc221eef9eb6ffccfae125b399/installer/src/nativeReadQueue.test.ts) | Deterministic ordering rather than a guessed delay. |
| Delayed startup behavior | [App.test.tsx at the merged startup source](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/9f1c316b13edfcbc221eef9eb6ffccfae125b399/installer/src/App.test.tsx) | Safety-before-validation, repeated effects, navigation and outdated results. |
| Compatible Python installation | [PR #163](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/163) and [its contract at merged source](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/4502d741793fb0f8d30216a9947ae140770b4354/docs/PYTHON-RUNTIME-VERIFICATION.md) | Presence, default selection and complete required verification are different facts. PR verified merged as `4502d741793fb0f8d30216a9947ae140770b4354`. |
| Windows Python PR checks | [Run 43605957472](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/43605957472) | Applicable checks passed for head `458cc538a03fc147a7bbf9a77cb212a1dfb951d8`. This does not accept an owner's exact device or a later candidate. |

Issue comments can change over time. The pinned implementation records preserve the technical context used in the lessons.

## Repository instructions behind the lessons

| Topic | Source |
| --- | --- |
| Main jobs, dependencies, build/test commands and release behavior | [build-dev-setup.yml](../../.github/workflows/build-dev-setup.yml) |
| Scope, runner cost and shorter PR validation | [CI-VALIDATION-POLICY.md](../CI-VALIDATION-POLICY.md), [ci_scope.py](../../tests/ci_scope.py) |
| Actual interface scripts and tool dependencies | [installer/package.json](../../installer/package.json) |
| Native Rust dependencies | [installer Cargo manifest](../../installer/src-tauri/Cargo.toml), [coordination manifest](../../coordination/Cargo.toml), [updater manifest](../../updater/Cargo.toml) |
| Acknowledgment and fresh native authority | [ADR 0001](../adr/0001-interruption-acknowledgment-boundary.md), [ADR 0002](../adr/0002-lease-bound-recovery-transition.md) |
| Existing standalone CI introduction | [CI Student Guide](../CI-STUDENT-GUIDE.md) |

The local source references above were inspected from authoring checkout `505bbfe72cc431798be9f74904782efef4dfebf3`. That checkout includes proposed follow-up work; the manual's historical implementation claims use the explicitly pinned merged records above. This draft does not declare PR #164 merged or its candidate accepted.

## How to read the illustrations

- The lifecycle and release diagrams summarize the required process. They do not record an approval or run status.
- The startup sequence diagram summarizes successful ordering and deferral. Source tests and implementation records cover additional errors and stale-result handling.
- The failure excerpt puts two real relevant lines together for readability. It is not presented as a complete contiguous log.
- The classroom issue, help document, PR description and candidate forms are teaching exercises. They are not production issue submissions or release authorizations.
- The manual includes diagrams and text annotations, not screenshots purporting to show a current GitHub page.

## Evidence that remains separate

A unit pass, browser simulation, controlled native fixture, installed package check, authenticated release and owner UAT each support different claims. The manual does not treat any one as a replacement for all the others.

Required signing approval remains human. Owner testing must cover the exact authenticated candidate. Stable promotion needs separate authorization. No manual exercise changes those boundaries.
