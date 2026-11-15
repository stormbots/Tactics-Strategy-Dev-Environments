# Node.js and npm verification: first Windows increment for #161

## Problem and result

The Windows validator independently ran bare `node --version` and bare `npm --version`. It could reject a required Node 24 installation when another version was the default, or check npm through another Node.

It now discovers a supported Node 24 executable, resolves and reverifies its actual identity, checks its associated npm package and supported Node range, then invokes that npm CLI with the selected Node. A complete pair produces one required Node.js pass and supplies both actual versions to the existing tool metadata. Missing search results, unusable candidates and unfinished checks remain different non-passing results.

Other installations, PATH, runtime-manager selection, project settings and global defaults are preserved. This is read-only observation work. Linux pairing, complete real side-by-side fixtures, maintenance eligibility/review, preservation gaps in provisioning and the accepted connected UI remain outstanding. This increment does not complete #161 or create a Node-only repair engine.

## Supported discovery

`NodeRuntime.ps1` reads bounded known Windows sources:

- Cached Node 24 directories under configured/default nvm-windows, Volta and fnm stores.
- Node.js install-path and bounded uninstall registry records, including supported per-user/machine views.
- Conventional Program Files and nvm symlink locations.
- The resolved `node.exe` application as a fallback.

No manager command is run and no drive is scanned. The known Volta launcher path is excluded because launching it could acquire a missing runtime; only cached version-store executables are considered there. Shell `.cmd`/PowerShell shims are not executed for discovery. Executable shims that return an actual interpreter are followed only through fresh identity verification. Missing/unreadable/truncated sources remain incomplete unless another complete pair passes.

Version-store lists and final candidates are capped. Each fixed process has at most a 2.5-second wait within a 15-second probe budget. Only the helper's own diagnostic process can be stopped on timeout. Nothing targets an existing installer or removes a native gate.

## Pair verification

The fixed `NodeRuntimeProbe.cjs` uses Node's actual version and resolved executable path. Its npm mode derives `node_modules/npm/bin/npm-cli.js` beside that executable, reads npm's package metadata and uses npm's own semver dependency to check its declared Node engine range. npm must be the named package with a valid version and compatible engine range. Merely finding an npm file is not a pass.

The wrapper then invokes that exact CLI through the verified Node and requires successful exit plus a version matching the checked package. It never resolves bare npm or executes diagnostic text as a command. Supported npm prerelease versions remain evidence, not a newly imposed npm family restriction.

For each child process, Node injection/cache/coverage environment variables are removed and npm notification/script/audit settings are disabled. The working directory is temporary. Parent environment values are unchanged. No project package script, installation, manager switch or network lookup is requested by the fixed probes.

## Evidence and maintenance boundary

The validator emits `SKYVIEW_EVENT|runtime|Node.js|{...}` with schema 1, required family, status/reason, verified Node version/path, npm version/CLI path when established, and `maintenanceEligibility: notEvaluated`.

The frontend decoder rejects incomplete passes, another installation's npm path, malformed records and injected maintenance permission. It is an evidence foundation for later cards, not a native execution API. Existing generic rows still display the new check messages; the accepted card/continuation work remains a later increment.

Validation success does not prove that Chocolatey can maintain a selected version-store installation. Managed update metadata now withholds a candidate when the selected Node version differs from Chocolatey's tracked version, rather than treating executable/package version differences as one update comparison. That difference is informational and does not create a readiness warning or an update-retry task. It does not prove there are two installations; package drift is also possible. A matching version still supplies advisory package metadata, not proof of path ownership or execution authority. Actual eligibility/conflict review remains required before claiming the accepted maintenance workflow complete.

`Node24.ps1`, its migration/ownership rules, updater execution, coordination and all native admission checks are unchanged. Their existing preservation limitations must be resolved in the accepted follow-up work before promising a safe full Install/Repair remedy for every coexistence arrangement.

## Deployment and verification

The managed maintenance copy includes both new helpers under its existing protected file rules. The native application bundle already includes the backend resource directory. Required installed Windows recovery verification now checks that both helpers exist; original journal/privilege/summary assertions stay intact.

Local evidence:

- 286 frontend tests, production build/type checks and formatting passed.
- The real JavaScript probe passed 11 compatibility/metadata cases using npm's actual semver dependency. Controlled identities are not actual Windows side-by-side installations.
- PowerShell contracts passed 86 local assertions for pairing, newer/older defaults, fallback, executable shims, missing versus incomplete discovery, invalid output, npm failure/timeout/mismatch and unchanged defaults. Actual process quoting, Unicode output, exit/deadline behavior and child-environment isolation were exercised separately.
- The platform-independent metadata fixtures passed the new cross-installation update guard. The full metadata suite includes Windows native disk/COM assertions and cannot pass on this Linux host; those assertions are unchanged and remain required in Windows CI.
- Source PowerShell parsing and the existing 35 backend contracts and 35 CI-scope tests passed. No application safety or CI classification exception was added.

Required Windows CI additionally exercises real directory discovery for nvm/Volta/fnm fixture stores, the prepared real Node 24/npm pair, production-validator observation consistency and packaged helper presence. Windows PowerShell 5.1 and installed/native assertions have not run locally. Full native/trust/acceptance CI remains mandatory for this platform change. A runner pass does not replace exact-candidate owner UAT or a complete supported coexistence fixture.

Baseline is green main `6ae6a2e7750b175bf83f2ee66c76c94ffe94d47e`. #160 is currently closed; remaining packaged startup/owner evidence must be reconciled in the release ledger rather than inferred from issue closure. No release version, signing approval, owner acceptance or stable promotion is created by this increment.
