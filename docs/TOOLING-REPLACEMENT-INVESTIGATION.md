# Tooling replacement investigation

This is a research checkpoint for [#161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161) and the dependency blocker on [#174](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/174). No replacement is adopted. The high-severity audit gate and every native, integrity, trust, signing and owner acceptance gate remain required.

## The blocker and exposure

[GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf) affects picomatch through 4.0.7. The registry still lists 4.0.7 as latest, and the advisory lists no patched release at this checkpoint. Current Vite and Vitest releases still depend on that range. A blind retry or updating those tools alone does not resolve it.

The affected matcher compiles file patterns into regular expressions. Certain crafted patterns can cause excessive processing. SDE's checked-in test patterns and normal build configuration are controlled by the project. No application UI path that submits an external pattern to this matcher was identified in this review. This is a bounded source review, not proof of zero exposure.

The matcher is in the development-tool chain. The frontend production build inspected here contains no picomatch name or its `analyzeRepeatedExtglob` signature. Tauri's source configuration packages `dist` and the Windows/Linux backend trees, rather than installer `node_modules`. These observations do not authenticate a final installer or replace exact-candidate package inspection. The advisory does not identify a flaw in SDE's Python verification, maintenance or recovery code.

## Rsbuild/Rstest: rejected as a remediation

The [official Vitest migration guide](https://rstest.rs/guide/migration/vitest) describes many compatible APIs. A clean candidate resolution replaced Vite/Vitest/plugin-react with:

- `@rsbuild/core` 2.3.3
- `@rsbuild/plugin-react` 2.1.1
- `@rstest/core` 0.12.6

The rest of SDE's declared dependencies were retained. Both Rsbuild and Rstest declare Node support compatible with the project's Node 24.19 toolchain. The candidate lockfile reported **zero npm audit findings**, but that result was misleading for this specific investigation.

The published Rstest package bundles picomatch 4.0.7. Its `dist/h~0.js` contains the module identifier `../../node_modules/.pnpm/picomatch@4.0.7/node_modules/picomatch/index.js`. Other distributed chunks call that matcher. Its package metadata also lists picomatch `^4.0.7` among build-time development dependencies, and its license file includes picomatch. Bundling moves the code outside npm's normal transitive-package audit graph; it does not repair it.

The inspected `dist/h~0.js` SHA-256 is `51484ddae945678d59de1d0ba5afadc581ccac5836c91b9c7594c1d6b804b099`. Package metadata is available at the [registry's version endpoint](https://registry.npmjs.org/@rstest/core/0.12.6). The experiment installed candidate packages with lifecycle scripts disabled and inspected their distributed files. It did not migrate or run SDE's suite against Rstest. Experimental manifest/lockfile changes were discarded; they are not proposed source changes.

**Do not adopt this candidate to make audit green.** Reconsider only after the bundled code has a verified remediation and the actual installed distribution is inspected again.

## esbuild and Node's test runner: possible larger migration

A second, manifest-only experiment removed Vite, Vitest and their React plugin, added esbuild 0.28.2, and retained SDE's other dependencies. It resolved with **zero audit findings** and no picomatch package in its lockfile. Node's test runner is built into Node rather than installed as another npm test framework.

This is a dependency-tree observation, not a working replacement. No migrated build, dev server, test suite or native installer was produced with this candidate. It still needs distributed-code review and a prototype before any safety or compatibility claim.

The migration would need to preserve:

1. All existing assertions, including module mocks, timers, request races, cancellation, native admission boundaries and accessibility checks.
2. React/TSX transformation, jsdom setup, cleanup and test isolation. Do not replace complex production-App checks with simpler component snapshots.
3. Correct static HTML, CSS, image and JavaScript output under Tauri's existing content-security policy. Preserve the 1420 development URL and browser-test server behavior.
4. Windows/Mint frontend packaging, installation and update evidence.

This is not a direct import rename. Vitest hoists module mocks; the existing suite uses these mocks and an asynchronous `importActual` factory. Node's [24.19 test-runner documentation](https://nodejs.org/download/release/v24.19.0/docs/api/test.html) labels module-mock facilities as early development. The installed Node 24.19 `--help` exposes `--experimental-test-module-mocks`. Loader and mock behavior need explicit parity tests before choosing this path. Keep [esbuild's official API](https://esbuild.github.io/api/) as the build reference for any later spike.

## Decision and next work

Keep the existing toolchain blocked at the audit gate while waiting for a complete upstream fix. Continue independent release work on separate branches with local verification and durable checkpoints. Do not launch repeated known-failing CI runs.

If a replacement becomes necessary, start with a small esbuild/Node prototype that preserves one demanding production-App race and mocking test, plus a packaged frontend smoke check. Proceed only if that prototype establishes real parity; then port the complete suite and require all normal gates. Do not hide bundled dependencies, suppress the advisory, lower the audit threshold, install an incomplete fork, or downgrade merely because npm suggests it.

An upstream release is useful only after verifying its actual fixed code, published package and advisory status. A clean audit alone is insufficient, as the Rstest experiment demonstrates. No security exception or release promotion is authorized by this report.
