# esbuild and Node test-runner prototype

Research checkpoint for [#161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161) and the [#174 dependency blocker](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/174). This prototype is isolated from the installer scripts, manifests and workflows. It is not an adopted replacement or a release candidate.

## What passed

On Node 24.19.0 and Debian Chromium 154:

- The actual current production App compiled and ran under Node's built-in test runner with six demanding existing scenarios preserved.
- An intentionally incorrect App assertion caused a nonzero exit and included its expected failure marker. Exact-case-count guards prevent a silently skipped suite from appearing successful.
- esbuild 0.28.2 bundled the actual frontend, CSS and public logo. Its build graph contained 1,591 inputs and no Vite, Vitest, picomatch or tinyglobby input.
- The production bundle loaded at 390 and 1140 pixels under the unchanged Tauri CSP. Validation/About navigation, responsive CSS and logo loading passed without page errors or CSP violations.
- The isolated dependency tree audited with zero findings, with no picomatch/tinyglobby package in its lockfile. A distributed JavaScript scan found no picomatch/analyzeRepeatedExtglob identifiers after using playwright-core instead of the Playwright test runner. These checks are bounded evidence, not a complete software-composition audit.

The base is main `6aa9cefe69edfb3b82c1f426722addd76cebcc07`. Production source files are read directly from that checkout. No simplified App, native permit, settings writer or selective installer replaces them.

## Test crosswalk

The source scenarios are in [App.test.tsx](../installer/src/App.test.tsx). Their assertions are expressed with `node:assert/strict`, using Node mocks at the same native/read-adapter boundaries.

| Existing scenario | Prototype evidence |
| --- | --- |
| Wait for startup safety before validation; stay checking between phases | No early tool inspection, checking remains visible, no premature failure, Ready only after the tool result |
| Queued explicit check; duplicate clicks before admission | Busy message before admission, no early operation, exactly one Validate after admission |
| StrictMode effect replay | Exactly one safety read and one startup validation; no operation dispatched |
| Navigation during delayed validation | Late result cannot redirect from About; Overview later receives the result |
| Unmount while safety is pending | No tool inspection submitted after unmount |
| Known active native work | Tools remain unchecked; changes stay paused without inventing a failed tool check |

The actual recovery helpers are imported before their inspection boundary is mocked. App is imported afterward. A controlled admission hook replaces Vitest's post-import namespace spy. This is deliberate: Node does not retroactively replace existing ESM references. No Vitest compatibility shim is introduced.

## Reproduce locally

From the repository root, using Node 24.19.0:

```bash
npm ci --prefix tools/tooling-spike --ignore-scripts
npm audit --prefix tools/tooling-spike --audit-level=high
npm test --prefix tools/tooling-spike
npm run test:negative --prefix tools/tooling-spike
SDE_SPIKE_CHROMIUM=/usr/bin/chromium npm run smoke --prefix tools/tooling-spike
```

The smoke check needs a local Chromium executable, permission to start it and permission to bind a loopback port. It serves only generated prototype output on a temporary local port. It does not use an owner's browser session or invoke native workstation operations. Its browser sandbox flag is for the disposable Linux test host, not an SDE packaging change.

Generated files and installed packages stay under ignored `.output` and `node_modules` folders. The production installer `dist` is untouched. A normal npm install does not automatically run the build. Node module mocking requires its explicit experimental flag.

The test command uses direct single-file `node:test` execution. In this environment the process-isolated `node --test` reporter summarized this file as one file result; direct execution reports all six names. The exact-six completion guard and negative control both passed. Full multi-file isolation, discovery, reporting and cancellation still need verification before adoption; the prototype does not disable isolation in the production suite.

## Additional bundled-code finding

The earlier candidate audit did not expose every bundled matcher. The current project's Playwright 1.63.0 distribution includes picomatch code in `lib/matchers/expect.js`, despite not listing a picomatch package in the installed audit graph. The inspected 1.63.0 matcher file SHA-256 is `5ef2a695e787386367f4b1e03c79b05100b5526121462b24d7730a731689d941`. The same code family is also present in a separately inspected 1.65.1 distribution. Presence does not by itself establish an exploitable Playwright call path, but there is no basis here for calling that bundle remediated.

The prototype therefore uses **playwright-core 1.63.0** for browser automation and Node assertions for checks. It does not use `@playwright/test` or the affected matcher bundle. Migrating the real project would also require preserving the existing browser suite's locator waits, assertions, accessibility, layouts and platform coverage. Merely swapping Vite/Vitest while keeping a bundled affected matcher would be incomplete remediation.

## Required before adoption

This prototype proves a direction, not complete parity. It transpiles TypeScript; it does not replace the current `tsc -b` type-check gate. It has not ported the rest of the current unit suite, the two browser projects or the pending #174/VSCodium access-review tests. It provides no Windows/Mint packaging, real native permission, signing or owner UAT evidence.

A complete migration must preserve all assertions and supported execution paths. It needs a reviewed type-check configuration, module-mock semantics, per-file isolation, timer behavior, source/build assets, development server at port 1420, the full browser suite, both browser engines where currently required, and normal Tauri production packaging. Test enumeration and deliberately failing/canceled cases must fail the aggregate gate.

Only after clean install, audit, type checks, the complete retained frontend/browser suites and local contracts pass should a migration PR start full CI. That PR must pass common checks, Windows/Mint native, both trust jobs and acceptance; then protected merge and full exact-main evidence. Existing human signing, exact authenticated-candidate owner UAT and separate stable-promotion authorization remain mandatory. No security exception is requested.

## References

- [Upstream advisory](https://github.com/advisories/GHSA-fc5q-39xc-vjpf): no patched release was listed at the recheck; registry latest remained 4.0.7.
- [Node 24.19 test-runner API](https://nodejs.org/download/release/v24.19.0/docs/api/test.html).
- [esbuild API](https://esbuild.github.io/api/).
- [Published Playwright package metadata](https://registry.npmjs.org/playwright/1.63.0).
- [Earlier tooling investigation](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/0401154c9873a05ff019e8c971fff793f0aff643/docs/TOOLING-REPLACEMENT-INVESTIGATION.md).
