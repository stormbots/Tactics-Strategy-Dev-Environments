# Frontend tooling migration

Part of #161. This change replaces the frontend build and test engines so work can continue without the affected `picomatch` dependency or its known bundled copies. It does not change the installed application's setup authority or resolve the remaining Refine UX findings by itself.

## Why change tools?

The npm advisory [GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf) blocked the existing audit gate. Replacing a named dependency is not enough when another tool includes the same code inside its distributed files. The reviewed alternative build/test engines also contained such copies. This implementation removes those engines rather than allowing the audit failure or suppressing the advisory.

This is a development-tool dependency finding. Its presence alone does not establish an exploitable path in an installed student's application.

## What runs now?

| Task | Tool | Command from `installer` |
| --- | --- | --- |
| Type checking and production bundle | TypeScript and esbuild | `npm run build` |
| Unit tests | Node's test runner, JSDOM and maintained assertion/mock libraries | `npm test` |
| Browser tests | Node's test runner and Playwright core | `npm run test:browser` |
| Local preview | A small localhost esbuild server | `npm run dev` |
| Native development and packaging | Existing Tauri commands | `npm run tauri dev` / `npm run tauri build` |

Use Node **24.19 or newer within the 24 family**. The harness uses Node's experimental module-mocking API, so Node upgrades require compatibility review. This requirement is for building/testing the repository; it does not change a student's global runtime selection.

The Vite and Vitest engines, Playwright test-runner package and unused repository Prettier dependency are removed. Standalone `@vitest/expect` and `@vitest/spy`, Chai and Sinon fake timers remain maintained libraries. Their installed distributions are checked along with the other dependencies. Removing the unused formatter dependency does not change VSCodium's managed editor settings or extensions.

Production still bundles the same React entry point into `installer/dist`. TypeScript remains a required build step. Test helpers are rejected from the production bundle graph. Native backend resources, IPC permissions, Tauri CSP and package version remain unchanged. No release version is reserved by this change.

The preview server uses port 1420 and rebuilds source on the next request after a source change. **Refresh the page after editing**; this server does not provide hot module replacement. Its stable read-adapter endpoints retain the existing browser tests' simulated native responses. They are not included in the production bundle.

## How existing tests are preserved

`installer/testing/baseline.json` records the original test inventory from main commit `6aa9cefe69edfb3b82c1f426722addd76cebcc07`:

- 313 unit cases in 22 files.
- 124 browser cases: 118 Chromium and six WebKit sidebar/settings cases.
- Counts and SHA-256 fingerprints of TypeScript-normalized `expect(...)` calls in 39 original test/helper files.

The runners check the assertion fingerprints before execution. Each test file runs in a separate Node process. Its registered and completed case names must match the recorded inventory, and its process must succeed. Unknown test files, missing cases, failures, cancellation and missing receipts fail validation. Local file/project selectors are explicit; CI uses the default command with both engines.

Four additional browser conformance cases bring the default browser total to **128: 120 Chromium and eight WebKit**. They exercise positive and negative assertions, native locator retries, strict matching, text/regex handling, polling and cancellation. Unit-harness conformance runs before the application cases: seven positive cases and seven deliberately failing or cancelled controls must produce the expected outcomes. A deliberately contaminated distribution must also be rejected.

Original tests now import explicit local adapters. The compiler uses TypeScript syntax trees to preserve mock-before-import ordering. Two ESM mock fixtures declare previously omitted exports and throw if those unused exports are called. One startup test waits for its existing asynchronously displayed button before clicking it. Original assertion bodies are preserved.

When adding a test, deliberately update the inventory with the reviewed case names. Preserve existing entries and fingerprints. A change to an existing assertion needs explicit review of that test change; do not regenerate the baseline merely to make a failing check pass. A future migration of pending #174 or editor-access work must add its tests to this inventory and verify the combined result before merging that work.

## Browser compatibility boundary

The browser assertion adapter binds to Playwright core **1.63.0**'s private Locator `_expect` interface. This retains the engine's own strict locator, retry, visibility, whitespace and regex behavior instead of approximating browser checks with custom DOM reads. The adapter checks the exact SDK version, required method and result shape. An assertion mismatch, timeout or cancellation fails the test.

This private interface is a maintenance risk. Before upgrading Playwright core, review its protocol, update the binding if needed and run conformance plus every original case on both engines. Do not remove the version guard to accept an unreviewed update. Both browser engines remain required in CI.

## Dependency checks and release gates

The existing full `npm audit` gate remains in place. A separate installed-distribution scan rejects the removed root engines and known matcher signatures, including bundled copies that npm's dependency audit cannot see. This is a bounded check for known code signatures, not a replacement for security review or a complete source audit.

Only the browser-install CLI name changes in the workflow: `playwright` becomes `playwright-core`. The normal browser command still runs both engines. Windows/Mint native validation, both trust jobs, artifact integrity, `acceptance`, protected merge and exact-main validation remain required. Human signing approval, owner UAT on the authenticated candidate and separately authorized stable promotion remain separate gates.

## Local evidence and limits

The migrated unit inventory and harness controls passed locally. Production build/type checking and the installed-distribution scan passed. npm audit reported no vulnerabilities. CI-policy checks passed.

The final complete Chromium inventory passed: 120 cases, including all 118 original cases and the two added conformance cases. This workspace's network policy blocks the official WebKit browser downloads with HTTP 403. WebKit cases are preserved and required in GitHub CI; their local execution is not claimed as passing. Native and trust evidence for this migration must come from its own full pipeline, followed by full exact-main validation after a protected merge. Previous successful runs remain useful historical evidence, but do not replace those gates.
